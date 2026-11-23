"""Shared experiment utilities: folds, per-subject results, bootstrap CIs, window metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from ..data.load import ROOT
from . import events as ev

TAB = ROOT / "results" / "tables"
RAW = ROOT / "results" / "raw"
FIG = ROOT / "results" / "figures"
for d in (TAB, RAW, FIG):
    d.mkdir(parents=True, exist_ok=True)

SEED = 20261123
COST_RATIOS = (10, 50, 100)
SENS_TARGETS = (0.95, 0.98, 0.99)   # recall first: report FA/h at each target


def outer_folds(meta: pd.DataFrame):
    subs = np.sort(meta.SubjectID.unique())
    for s in subs:
        train = np.array([x for x in subs if x != s])
        assert s not in set(train), "subject leakage"
        yield int(s), train


def inner_groupkfold(train_subjects: np.ndarray, k: int = 4):
    """Deterministic GroupKFold over training subjects -> list of (inner_train, inner_val)."""
    gkf = GroupKFold(n_splits=k)
    subs = np.asarray(train_subjects)
    for tr, va in gkf.split(subs, groups=subs):
        assert not set(subs[tr]) & set(subs[va])
        yield subs[tr], subs[va]


def inner_val_subjects(meta: pd.DataFrame, train_subjects: np.ndarray, test_subject: int, n_val: int = 3):
    """Fixed per outer fold (same for every model/seed): n_val training subjects that have falls."""
    has_fall = set(meta[meta.label == "FALL"].SubjectID.unique())
    cand = np.array([s for s in train_subjects if s in has_fall])
    rng = np.random.default_rng(SEED + test_subject)
    return np.sort(rng.choice(cand, size=n_val, replace=False))


def subject_rows(pr: dict, meta: pd.DataFrame, thr_idx: int) -> pd.DataFrame:
    """Per-subject counts at one threshold index of a per_record result."""
    sub = meta.SubjectID.values[pr["rec"]]
    df = pd.DataFrame(dict(SubjectID=sub, is_fall=pr["is_fall"], det=pr["det"][:, thr_idx],
                           fa=pr["fa"][:, thr_idx], hours=pr["hours"]))
    g = df.groupby("SubjectID")
    return pd.DataFrame(dict(n_falls=g.is_fall.sum(), n_det=g.det.sum(), n_fa=g.fa.sum(),
                             hours=g.hours.sum())).reset_index()


def pooled(df: pd.DataFrame) -> tuple[float, float]:
    sens = df.n_det.sum() / max(df.n_falls.sum(), 1)
    return sens, df.n_fa.sum() / df.hours.sum()


def bootstrap_ci(df: pd.DataFrame, n: int = 2000, seed: int = SEED) -> dict:
    """95 % CI by resampling subjects with replacement (pooled sensitivity and FA/h)."""
    rng = np.random.default_rng(seed)
    arr = df[["n_falls", "n_det", "n_fa", "hours"]].to_numpy(float)
    idx = rng.integers(0, len(arr), size=(n, len(arr)))
    s = arr[idx].sum(1)
    sens = s[:, 1] / np.maximum(s[:, 0], 1)
    fah = s[:, 2] / s[:, 3]
    s_ci, f_ci = np.percentile(sens, [2.5, 97.5]), np.percentile(fah, [2.5, 97.5])
    return dict(sens_lo=s_ci[0], sens_hi=s_ci[1], fah_lo=f_ci[0], fah_hi=f_ci[1])


def window_metrics(y: np.ndarray, prob: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(((pred == 1) & (y == 1)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    sens = tp / max(tp + fn, 1); spec = tn / max(tn + fp, 1); prec = tp / max(tp + fp, 1)
    return dict(w_sens=sens, w_spec=spec, w_prec=prec,
                w_f1=2 * prec * sens / max(prec + sens, 1e-9),
                w_prauc=average_precision_score(y, prob), w_rocauc=roc_auc_score(y, prob))


def choose_thresholds(pr_inner: dict, probs_inner: np.ndarray) -> dict:
    """Thresholds chosen on inner (training-subject) predictions only."""
    grid = ev.threshold_grid(probs_inner)
    pr = ev.per_record(pr_inner["win"], pr_inner["meta"], grid)
    out = {"sens95": ev.pick_threshold(pr, grid, 0.95)}
    for c in COST_RATIOS:
        out[f"cost{c}"] = ev.pick_cost_threshold(pr, grid, c)
    return out
