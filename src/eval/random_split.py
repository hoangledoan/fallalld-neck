"""H5: how much a random window-level 80/20 split inflates results compared with LOSO.

Illustration only (not used for any conclusion). Same features (M1, accel + pressure, 60 Hz, 4 s),
same LightGBM, same windows: positives = anchored fall windows (5 jittered copies per fall),
negatives = sliding windows of ADL / near-fall records; fixed threshold 0.5.
- random: windows shuffled into 80/20 -> jittered copies of one fall and overlapping windows of
  one record can land on both sides (the leak typical of random splits)
- LOSO: all windows of the test subject are held out.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ..models.trees import feature_set, _fit
from ..features.feats import select
from .common import window_metrics, outer_folds, SEED, TAB


def main(sensors: str = "A+B", odr: float = 60, L: float = 4):
    fs = feature_set(odr, L)
    meta = fs["meta"]
    cols = select(fs["names"], fs["grp"], sensors)
    neg = meta.label.values[fs["sl"].rec.values] != "FALL"
    X = np.vstack([fs["F_an"][:, cols], fs["F_sl"][neg][:, cols]])
    y = np.r_[np.ones(len(fs["F_an"])), np.zeros(neg.sum())]
    subj = np.r_[meta.SubjectID.values[fs["an"].rec.values], meta.SubjectID.values[fs["sl"].rec.values[neg]]]
    rows = []
    # random 80/20
    tr, te = train_test_split(np.arange(len(y)), test_size=0.2, stratify=y, random_state=SEED)
    m = _fit("lgbm", X[tr], y[tr], SEED)
    p = m.predict_proba(X[te])[:, 1]
    acc = ((p >= .5) == y[te]).mean()
    rows.append(dict(split="random 80/20 (windows)", accuracy=acc, **window_metrics(y[te], p, (p >= .5).astype(int))))
    # LOSO
    P = np.zeros(len(y))
    for s, train_s in outer_folds(meta):
        trm = np.isin(subj, train_s); tem = subj == s
        assert not (set(subj[trm]) & set(subj[tem]))
        P[tem] = _fit("lgbm", X[trm], y[trm], SEED).predict_proba(X[tem])[:, 1]
    rows.append(dict(split="LOSO (subjects)", accuracy=((P >= .5) == y).mean(),
                     **window_metrics(y, P, (P >= .5).astype(int))))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "h5_random_vs_loso.csv", index=False)
    print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
