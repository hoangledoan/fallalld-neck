"""M0 (threshold rule) and M1 (features + LightGBM / decision tree), leave-one-subject-out."""
from __future__ import annotations

import os
import pickle
import time

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.tree import DecisionTreeClassifier

from ..data.load import ROOT
from ..data.preprocess import build
from ..data.windows import sliding_index, anchored_index, gather
from ..features.feats import features, select
from ..eval import events as ev
from ..eval.common import (outer_folds, inner_groupkfold, subject_rows, pooled, bootstrap_ci,
                           window_metrics, COST_RATIOS, SENS_TARGETS, SEED, RAW, TAB)

OFFSETS = (-0.5, -0.25, 0.0, 0.25, 0.5)   # +-0.5 s jitter of the impact position (train positives)


def feature_set(odr: float, L: float, rebuild: bool = False) -> dict:
    path = ROOT / "cache" / f"feats_odr{int(odr)}_L{L:g}.pkl"
    if path.exists() and not rebuild:
        with open(path, "rb") as f:
            return pickle.load(f)
    d = build(odr)
    n = np.array([len(x) for x in d["X"]])
    W = int(round(L * odr))
    sl = sliding_index(d["meta"], n, odr, L)
    an = anchored_index(d["meta"], n, odr, L, OFFSETS)
    out = dict(meta=d["meta"], odr=odr, L=L, sl=sl, an=an)
    for key, idx in (("F_sl", sl), ("F_an", an)):
        chunks = []
        for i in range(0, len(idx), 8000):
            w = gather(d["X"], idx.rec.values[i:i + 8000], idx.start.values[i:i + 8000], W)
            F, names, grp = features(w, odr)
            chunks.append(F)
        out[key] = np.vstack(chunks)
    out["names"], out["grp"] = names, grp
    with open(path, "wb") as f:
        pickle.dump(out, f, protocol=4)
    return out


# ---------------------------------------------------------------- M0
def m0_score(F: np.ndarray, names: list, t_ang: float, t_p: float | None) -> np.ndarray:
    a_max = F[:, names.index("a_max")]
    ok = F[:, names.index("ph_posture_deg")] >= t_ang
    if t_p is not None:
        dp = F[:, names.index("p_dP")]
        ok &= np.nan_to_num(dp, nan=-1e9) >= t_p
    return np.where(ok, a_max, 0.0)


def m0_fit(fs, rows_sl, sensors):
    """Grid over gates on training subjects (in-sample: M0 has only 2-3 parameters)."""
    names = fs["names"]
    best = None
    t_ps = [None] + ([0.0, 2.0, 4.0, 6.0] if "B" in sensors else [])
    for t_ang in (0.0, 15.0, 30.0, 45.0):
        for t_p in t_ps:
            sc = m0_score(fs["F_sl"][rows_sl], names, t_ang, t_p)
            win = fs["sl"].iloc[rows_sl][["rec", "t_end"]].assign(prob=sc)
            grid = ev.threshold_grid(sc[sc > 0] if (sc > 0).any() else sc, 300)
            pr = ev.per_record(win, fs["meta"], grid)
            thr = ev.pick_threshold(pr, grid, 0.95)
            i = np.searchsorted(grid, thr)
            sens, fah = ev.summarise(pr)
            key = (fah[i], -sens[i])
            if best is None or key < best[0]:
                thr_cost = {f"cost{c}": ev.pick_cost_threshold(pr, grid, c) for c in COST_RATIOS}
                thr_s = {f"sens{int(q * 100)}": ev.pick_threshold(pr, grid, q) for q in SENS_TARGETS}
                best = (key, dict(t_ang=t_ang, t_p=t_p, **thr_s, **thr_cost))
    return best[1]


# ---------------------------------------------------------------- M1
LGBM_DEFAULT = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=20,
                    class_weight=True)


def _fit(kind, X, y, seed, params: dict | None = None):
    if kind == "lgbm":
        p = {**LGBM_DEFAULT, **(params or {})}
        spw = (y == 0).sum() / max((y == 1).sum(), 1) if p["class_weight"] else 1.0
        m = lgb.LGBMClassifier(n_estimators=p["n_estimators"], learning_rate=p["learning_rate"],
                               num_leaves=p["num_leaves"], min_child_samples=p["min_child_samples"],
                               subsample=0.8, subsample_freq=1, colsample_bytree=0.8, scale_pos_weight=spw,
                               random_state=seed, n_jobs=int(os.environ.get("LGBM_THREADS", 2)), verbose=-1)  # 4 threads is ~40x slower on this shared 4-core box
    else:
        m = DecisionTreeClassifier(max_depth=6, min_samples_leaf=20, class_weight="balanced",
                                   random_state=seed)
    return m.fit(X, y)


NEG_MARGIN_S = 0.5   # fall-record windows used as negatives must miss the impact by > 0.5 s


def _train_rows(fs, subjects, neg_from_falls: bool = True):
    """Positives: anchored fall windows. Negatives: sliding windows of ADL / near-fall records and,
    from revision 2 on, sliding windows of fall records that do not contain the impact."""
    meta = fs["meta"]
    rec = fs["sl"].rec.values
    sub_sl = meta.SubjectID.values[rec]
    sub_an = meta.SubjectID.values[fs["an"].rec.values]
    is_fall = meta.label.values[rec] == "FALL"
    neg = np.isin(sub_sl, subjects) & ~is_fall
    if neg_from_falls:
        t_end = fs["sl"].t_end.values
        ti = meta.t_impact.values[rec]
        no_impact = (t_end < ti - NEG_MARGIN_S) | (t_end - fs["L"] > ti + NEG_MARGIN_S)
        neg |= np.isin(sub_sl, subjects) & is_fall & no_impact
    pos = np.isin(sub_an, subjects)
    return pos, neg


def run(sensors: str, odr: float, L: float, models=("M0", "M1lgbm", "M1tree"), seed: int = SEED,
        tag: str = "", quick: bool = False, neg_from_falls: bool = True, fv: dict | None = None,
        params: dict | None = None, variant: str = "", keep: dict | None = None) -> pd.DataFrame:
    """fv (optional feature view) overrides features: keys F_sl, F_an, cols, and optionally
    F_sl_test / F_an_test (e.g. rotated test data) and F_sl_aug / F_an_aug (extra training copies).
    keep (optional dict): filled with {(model, test subject): {"model", "thr", "cols"}} for re-use."""
    fs = dict(feature_set(odr, L))
    meta = fs["meta"]
    cols = select(fs["names"], fs["grp"], sensors)
    if fv is not None:
        fs.update({k: v for k, v in fv.items() if k in ("F_sl", "F_an")})
        cols = fv.get("cols", cols)
    F_sl_test = fv.get("F_sl_test", fs["F_sl"]) if fv else fs["F_sl"]
    F_an_test = fv.get("F_an_test", fs["F_an"]) if fv else fs["F_an"]
    aug = [(fv["F_an_aug"], fv["F_sl_aug"])] if fv and "F_sl_aug" in fv else []
    sub_sl = meta.SubjectID.values[fs["sl"].rec.values]
    sub_an = meta.SubjectID.values[fs["an"].rec.values]
    is_fall_sl = meta.label.values[fs["sl"].rec.values] == "FALL"
    an0 = fs["an"].offset.values == 0.0
    rows, raw = [], []
    folds = list(outer_folds(meta))
    if quick:
        folds = folds[:2]
    for model in models:
        t0 = time.time()
        for test_s, train_s in folds:
            te_sl = sub_sl == test_s
            assert not (set(sub_sl[te_sl]) & set(train_s))
            if model == "M0":
                tr_rows = np.where(np.isin(sub_sl, train_s))[0]
                par = m0_fit(fs, tr_rows, sensors)
                score = lambda F: m0_score(F, fs["names"], par["t_ang"], par["t_p"])
                thr = {k: v for k, v in par.items() if k.startswith(("sens", "cost"))}
            else:
                kind = "lgbm" if model == "M1lgbm" else "tree"
                # inner GroupKFold -> out-of-fold predictions on training subjects -> thresholds
                oof = []
                for itr, iva in inner_groupkfold(train_s):
                    pos, neg = _train_rows(fs, itr, neg_from_falls)
                    X, y = _xy(fs, aug, pos, neg, cols)
                    m = _fit(kind, X, y, seed, params)
                    va = np.isin(sub_sl, iva)
                    oof.append(fs["sl"][va][["rec", "t_end"]].assign(
                        prob=m.predict_proba(fs["F_sl"][va][:, cols])[:, 1]))
                oof = pd.concat(oof)
                grid = ev.threshold_grid(oof.prob.values)
                pr_in = ev.per_record(oof, meta, grid)
                thr = {f"sens{int(q * 100)}": ev.pick_threshold(pr_in, grid, q) for q in SENS_TARGETS}
                for c in COST_RATIOS:
                    thr[f"cost{c}"] = ev.pick_cost_threshold(pr_in, grid, c)
                pos, neg = _train_rows(fs, train_s, neg_from_falls)
                X, y = _xy(fs, aug, pos, neg, cols)
                m = _fit(kind, X, y, seed, params)
                if keep is not None:
                    keep[(model, test_s)] = dict(model=m, thr=dict(thr), cols=list(cols))
                score = lambda F, m=m: m.predict_proba(F[:, cols])[:, 1]
            # --- test subject
            p_sl = score(F_sl_test[te_sl])
            win = fs["sl"][te_sl][["rec", "t_end"]].assign(prob=p_sl)
            te_an = (sub_an == test_s) & an0
            p_an = score(F_an_test[te_an]) if te_an.any() else np.array([])   # S04, S10: no falls
            raw.append(win.assign(fold=test_s, model=model))
            # window-level labels: anchored positives (offset 0) vs negative-record sliding windows
            neg_w = ~is_fall_sl[te_sl]
            yw = np.r_[np.ones(te_an.sum()), np.zeros(neg_w.sum())]
            pw = np.r_[p_an, p_sl[neg_w]]
            for rule, t in thr.items():
                pr = ev.per_record(win, meta, np.array([t]))
                sr = subject_rows(pr, meta, 0)
                wm = window_metrics(yw, pw, (pw >= t).astype(int)) if yw.sum() > 0 else {}
                for _, r in sr.iterrows():
                    rows.append(dict(model=model, sensors=sensors, odr=odr, L=L, seed=seed, tag=tag,
                                     variant=variant, rule=rule, fold=test_s, thr=t, **r.to_dict(), **wm))
        print(f"  {model} {sensors} {odr}Hz {L}s: {time.time() - t0:.0f}s", flush=True)
    res = pd.DataFrame(rows)
    name = f"{tag or 'm01'}_{sensors}_{int(odr)}_{L:g}{'_' + variant if variant else ''}".replace("+", "")
    pd.concat(raw).to_csv(RAW / f"win_{name}.csv.gz", index=False)
    res.to_csv(RAW / f"subj_{name}.csv", index=False)
    return res


def _xy(fs, aug, pos, neg, cols):
    """Training matrix; augmented copies (same rows, transformed signals) are appended if given."""
    Xs = [fs["F_an"][pos][:, cols], fs["F_sl"][neg][:, cols]]
    ys = [np.ones(pos.sum()), np.zeros(neg.sum())]
    for F_an_a, F_sl_a in aug:
        Xs += [F_an_a[pos][:, cols], F_sl_a[neg][:, cols]]
        ys += [np.ones(pos.sum()), np.zeros(neg.sum())]
    return np.vstack(Xs), np.concatenate(ys)


def summary(res: pd.DataFrame) -> pd.DataFrame:
    out = []
    keys = [k for k in ["model", "sensors", "odr", "L", "seed", "tag", "variant", "rule"] if k in res.columns]
    for k, g in res.groupby(keys, dropna=False):
        sens, fah = pooled(g)
        ci = bootstrap_ci(g)
        wcols = [c for c in g.columns if c.startswith("w_")]
        out.append(dict(zip(keys, k), sens=sens, fa_per_h=fah, n_falls=int(g.n_falls.sum()),
                        n_fa=int(g.n_fa.sum()), hours=g.hours.sum(), **ci,
                        **{c: g[c].mean() for c in wcols}))
    return pd.DataFrame(out)
