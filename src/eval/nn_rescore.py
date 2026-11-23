"""Re-score saved per-fold NN models with all threshold rules (no retraining).

Thresholds are still chosen on the fold's inner validation subjects only; the test subject is
only scored. Used when threshold rules were added after a training run.
    python -m src.eval.nn_rescore M2 A+B 60 4 20261123
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import tensorflow as tf

from ..data.windows import gather, nn_channels
from ..models.cnn import Data, MODELS_DIR, _predict
from . import events as ev
from .common import (outer_folds, inner_val_subjects, subject_rows, window_metrics,
                     COST_RATIOS, SENS_TARGETS, RAW)


def rescore(kind: str, sensors: str, odr: float, L: float, seed: int, tag: str = "nn",
            data: Data | None = None) -> pd.DataFrame:
    data = data or Data(odr, L)
    meta = data.meta
    rows, raw = [], []
    for test_s, train_s in outer_folds(meta):
        name = f"{kind}_{sensors}_{int(odr)}_{L:g}_s{seed}_f{test_s}".replace("+", "")
        model = tf.keras.models.load_model(MODELS_DIR / f"{name}.keras")
        val_s = inner_val_subjects(meta, train_s, test_s)
        assert test_s not in set(val_s)
        vm = np.isin(data.sub_sl, val_s)
        win_v = data.sl[vm][["rec", "t_end"]].assign(prob=_predict(model, nn_channels(data.rows(vm), sensors)))
        grid = ev.threshold_grid(win_v.prob.values)
        pr_v = ev.per_record(win_v, meta, grid)
        thr = {f"sens{int(q * 100)}": ev.pick_threshold(pr_v, grid, q) for q in SENS_TARGETS}
        for c in COST_RATIOS:
            thr[f"cost{c}"] = ev.pick_cost_threshold(pr_v, grid, c)
        tm = data.sub_sl == test_s
        p_sl = _predict(model, nn_channels(data.rows(tm), sensors))
        win = data.sl[tm][["rec", "t_end"]].assign(prob=p_sl)
        raw.append(win.assign(fold=test_s, model=kind))
        ta = data.sub_an0 == test_s
        p_an = (_predict(model, nn_channels(gather(data.X, data.an0.rec.values[ta], data.an0.start.values[ta],
                                                   data.W), sensors)) if ta.any() else np.array([]))
        neg_w = ~data.fall_sl[tm]
        yw = np.r_[np.ones(ta.sum()), np.zeros(neg_w.sum())]
        pw = np.r_[p_an, p_sl[neg_w]]
        for rule, t in thr.items():
            sr = subject_rows(ev.per_record(win, meta, np.array([t])), meta, 0)
            wm = window_metrics(yw, pw, (pw >= t).astype(int)) if yw.sum() > 0 else {}
            for _, r in sr.iterrows():
                rows.append(dict(model=kind, sensors=sensors, odr=odr, L=L, seed=seed, tag=tag, rule=rule,
                                 fold=test_s, thr=t, n_params=model.count_params(), **r.to_dict(), **wm))
    res = pd.DataFrame(rows)
    out = f"{tag}_{kind}_{sensors}_{int(odr)}_{L:g}_s{seed}".replace("+", "")
    res.to_csv(RAW / f"subj_{out}.csv", index=False)
    pd.concat(raw).to_csv(RAW / f"win_{out}.csv.gz", index=False)
    return res


if __name__ == "__main__":
    k, s, o, l, sd = sys.argv[1:6]
    rescore(k, s, float(o), float(l), int(sd))
