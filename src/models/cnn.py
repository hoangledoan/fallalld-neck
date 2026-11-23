"""M2 (small depthwise-separable 1D-CNN) and M3 (CNN + LSTM/GRU), leave-one-subject-out.

Per outer fold: 3 training subjects with falls (fixed per fold, same for every model and seed)
are held out as inner validation for early stopping (window PR-AUC) and threshold choice
(event level). Augmentation on training windows only: random 3D rotation (acc and gyro with the
same rotation), +-0.5 s impact jitter, Gaussian noise, +-10 % amplitude scaling.
"""
from __future__ import annotations

import os
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import average_precision_score

for _g in tf.config.list_physical_devices("GPU"):   # shared GPU: allocate only what is needed
    tf.config.experimental.set_memory_growth(_g, True)

from ..data.load import ROOT
from ..data.preprocess import build
from ..data.windows import sliding_index, anchored_index, gather, nn_channels, ANCHOR_FRAC
from ..eval import events as ev
from ..eval.common import (outer_folds, inner_val_subjects, subject_rows, window_metrics,
                           COST_RATIOS, SENS_TARGETS, SEED, RAW)

MODELS_DIR = ROOT / "models"


def build_model(kind: str, T: int, C: int) -> tf.keras.Model:
    inp = tf.keras.Input((T, C), batch_size=None)
    x = tf.keras.layers.Conv1D(16, 7, strides=2, padding="same", use_bias=False)(inp)
    x = tf.keras.layers.ReLU()(tf.keras.layers.BatchNormalization()(x))
    for f, k in ((32, 7), (32, 5)):
        x = tf.keras.layers.SeparableConv1D(f, k, strides=2, padding="same", use_bias=False)(x)
        x = tf.keras.layers.ReLU()(tf.keras.layers.BatchNormalization()(x))
    t = T // 8
    while t > 40:
        x = tf.keras.layers.MaxPool1D(2)(x)
        t //= 2
    if kind == "M2":
        x = tf.keras.layers.Concatenate()([tf.keras.layers.GlobalAveragePooling1D()(x),
                                           tf.keras.layers.GlobalMaxPooling1D()(x)])
    else:   # M3a: LSTM32, M3b: LSTM64, M3c: GRU32, M3d: GRU64 (unidirectional, last state)
        units = {"M3a": 32, "M3b": 64, "M3c": 32, "M3d": 64}[kind]
        rnn = tf.keras.layers.LSTM if kind in ("M3a", "M3b") else tf.keras.layers.GRU
        x = rnn(units)(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    return tf.keras.Model(inp, out, name=kind)


def _rotations(n, rng):
    q = rng.normal(size=(n, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q.T
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
        np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
        np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], 1).astype(np.float32)


def augment(win: np.ndarray, rng) -> np.ndarray:
    n = len(win)
    Rt = np.transpose(_rotations(n, rng), (0, 2, 1)) * rng.uniform(0.9, 1.1, (n, 1, 1)).astype(np.float32)
    w = np.empty_like(win)
    w[..., 0:3] = np.matmul(win[..., 0:3], Rt)          # rotate + scale acc
    w[..., 3:6] = np.matmul(win[..., 3:6], Rt)          # same rotation for gyro
    w[..., 6] = win[..., 6]
    noise = rng.standard_normal(w.shape, dtype=np.float32)
    noise *= np.array([0.01] * 3 + [1.0] * 3 + [0.5], np.float32)   # g, dps, Pa
    w += noise
    return w


class Data:
    def __init__(self, odr: float, L: float):
        d = build(odr)
        self.X, self.meta, self.odr, self.L = d["X"], d["meta"], odr, L
        self.n = np.array([len(x) for x in self.X])
        self.W = int(round(L * odr))
        self.sl = sliding_index(self.meta, self.n, odr, L)
        self.an0 = anchored_index(self.meta, self.n, odr, L, (0.0,))
        self.sub_sl = self.meta.SubjectID.values[self.sl.rec.values]
        self.fall_sl = self.meta.label.values[self.sl.rec.values] == "FALL"
        self.sub_an0 = self.meta.SubjectID.values[self.an0.rec.values]

    def pos_windows(self, subjects, rng, reps):
        recs = np.where((self.meta.label.values == "FALL") & np.isin(self.meta.SubjectID.values, subjects))[0]
        recs = np.repeat(recs, reps)
        off = rng.uniform(-0.5, 0.5, len(recs))
        st = np.round((self.meta.t_impact.values[recs] - ANCHOR_FRAC * self.L + off) * self.odr).astype(int)
        st = np.clip(st, 0, self.n[recs] - self.W)
        return gather(self.X, recs, st, self.W)

    def rows(self, mask):
        return gather(self.X, self.sl.rec.values[mask], self.sl.start.values[mask], self.W)


def _predict(model, x):
    return model.predict(x, batch_size=1024, verbose=0).ravel()


def train_fold(data: Data, kind: str, sensors: str, train_s, val_s, seed: int,
               max_epochs: int = 40, patience: int = 8, reps: int = 8, neg_frac: float = 1 / 3,
               verbose: bool = False):
    tf.keras.utils.set_random_seed(seed)
    rng = np.random.default_rng(seed)
    tr_s = np.array([s for s in train_s if s not in set(val_s)])
    assert not set(tr_s) & set(val_s)
    neg_raw = data.rows(np.isin(data.sub_sl, tr_s) & ~data.fall_sl)
    # validation set (no augmentation): anchored positives + negative-record sliding windows
    va_pos = np.isin(data.sub_an0, val_s)
    va_negm = np.isin(data.sub_sl, val_s) & ~data.fall_sl
    xv = nn_channels(np.concatenate([gather(data.X, data.an0.rec.values[va_pos], data.an0.start.values[va_pos], data.W),
                                     data.rows(va_negm)]), sensors)
    yv = np.r_[np.ones(va_pos.sum()), np.zeros(va_negm.sum())]
    C = xv.shape[-1]
    model = build_model(kind, data.W, C)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="binary_crossentropy")
    best, best_w, wait, lr_wait, hist = -1, None, 0, 0, []
    for ep in range(max_epochs):
        pos = data.pos_windows(tr_s, rng, reps)
        neg = neg_raw[rng.random(len(neg_raw)) < neg_frac]     # fresh random subset each epoch
        xb = np.concatenate([augment(pos, rng), augment(neg, rng)])
        yb = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
        cw = {0: 1.0, 1: len(neg) / len(pos)}
        h = model.fit(nn_channels(xb, sensors), yb, batch_size=512, epochs=1, shuffle=True,
                      class_weight=cw, verbose=0)
        ap = average_precision_score(yv, _predict(model, xv))
        hist.append(dict(epoch=ep, loss=h.history["loss"][0], val_prauc=ap,
                         lr=float(model.optimizer.learning_rate.numpy())))
        if verbose:
            print(hist[-1], flush=True)
        if ap > best + 1e-4:
            best, best_w, wait, lr_wait = ap, model.get_weights(), 0, 0
        else:
            wait += 1; lr_wait += 1
            if lr_wait >= 3:   # ReduceLROnPlateau on val PR-AUC
                model.optimizer.learning_rate.assign(model.optimizer.learning_rate * 0.5); lr_wait = 0
            if wait >= patience:
                break
    model.set_weights(best_w)
    return model, pd.DataFrame(hist)


def run(kind: str, sensors: str, odr: float, L: float, seed: int = SEED, tag: str = "",
        quick: bool = False, data: Data | None = None) -> pd.DataFrame:
    data = data or Data(odr, L)
    meta = data.meta
    folds = list(outer_folds(meta))
    if quick:
        folds = folds[:2]
    rows, raw, hists = [], [], []
    t0 = time.time()
    fold_dir = RAW / "folds"
    fold_dir.mkdir(exist_ok=True)
    for test_s, train_s in folds:
        fname = fold_dir / f"{tag or 'nn'}_{kind}_{sensors}_{int(odr)}_{L:g}_s{seed}_f{test_s}.pkl".replace("+", "")
        if fname.exists() and not quick:      # resume: fold already finished in an earlier run
            fr = pd.read_pickle(fname)
            rows += fr["rows"]; raw.append(fr["raw"]); hists.append(fr["hist"])
            print(f"  {kind} {sensors} fold S{test_s:02d}: loaded", flush=True)
            continue
        n_rows0 = len(rows)
        val_s = inner_val_subjects(meta, train_s, test_s)
        assert test_s not in set(val_s) and test_s not in set(train_s)
        model, hist = train_fold(data, kind, sensors, train_s, val_s, seed,
                                 max_epochs=3 if quick else 40)
        hists.append(hist.assign(fold=test_s))
        # thresholds from inner validation subjects (event level)
        vm = np.isin(data.sub_sl, val_s)
        win_v = data.sl[vm][["rec", "t_end"]].assign(prob=_predict(model, nn_channels(data.rows(vm), sensors)))
        grid = ev.threshold_grid(win_v.prob.values)
        pr_v = ev.per_record(win_v, meta, grid)
        thr = {f"sens{int(q * 100)}": ev.pick_threshold(pr_v, grid, q) for q in SENS_TARGETS}
        for c in COST_RATIOS:
            thr[f"cost{c}"] = ev.pick_cost_threshold(pr_v, grid, c)
        # test subject
        tm = data.sub_sl == test_s
        p_sl = _predict(model, nn_channels(data.rows(tm), sensors))
        win = data.sl[tm][["rec", "t_end"]].assign(prob=p_sl)
        ta = data.sub_an0 == test_s
        p_an = _predict(model, nn_channels(gather(data.X, data.an0.rec.values[ta], data.an0.start.values[ta], data.W), sensors)) if ta.any() else np.array([])
        raw.append(win.assign(fold=test_s, model=kind))
        neg_w = ~data.fall_sl[tm]
        yw = np.r_[np.ones(ta.sum()), np.zeros(neg_w.sum())]
        pw = np.r_[p_an, p_sl[neg_w]]
        for rule, t in thr.items():
            pr = ev.per_record(win, meta, np.array([t]))
            sr = subject_rows(pr, meta, 0)
            wm = window_metrics(yw, pw, (pw >= t).astype(int)) if yw.sum() > 0 else {}
            for _, r in sr.iterrows():
                rows.append(dict(model=kind, sensors=sensors, odr=odr, L=L, seed=seed, tag=tag, rule=rule,
                                 fold=test_s, thr=t, n_params=model.count_params(), epochs=len(hist),
                                 **r.to_dict(), **wm))
        name = f"{kind}_{sensors}_{int(odr)}_{L:g}_s{seed}_f{test_s}".replace("+", "")
        if not quick:
            MODELS_DIR.mkdir(exist_ok=True)
            model.save(MODELS_DIR / f"{name}.keras")
            pd.to_pickle(dict(rows=rows[n_rows0:], raw=raw[-1], hist=hists[-1]), fname)
        print(f"  {kind} {sensors} fold S{test_s:02d}: epochs={len(hist)} best val PR-AUC={hist.val_prauc.max():.3f} "
              f"[{time.time() - t0:.0f}s]", flush=True)
    res = pd.DataFrame(rows)
    name = f"{tag or 'nn'}_{kind}_{sensors}_{int(odr)}_{L:g}_s{seed}".replace("+", "")
    pd.concat(raw).to_csv(RAW / f"win_{name}.csv.gz", index=False)
    res.to_csv(RAW / f"subj_{name}.csv", index=False)
    pd.concat(hists).to_csv(RAW / f"hist_{name}.csv", index=False)
    return res
