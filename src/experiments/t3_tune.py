"""Revision 2, task 3: nested-CV hyper-parameter tuning of LightGBM (A+B, 60 Hz, 4 s).

Outer: LOSO (14 subjects). Inner: GroupKFold(4) over the training subjects only.
Grid: n_estimators {50,100,150,300,500} x num_leaves {7,15,31} x learning_rate {0.03,0.1}
      x min_child_samples {20,50} x class weight {yes,no}  (120 settings).
Each (leaves, lr, min_child, class weight) is fitted once with 500 trees; the 50/100/150/300-tree
models are read with predict(num_iteration=k) (identical to training k trees: boosting is sequential).
Selection: lowest inner false alarms/hour at the threshold that reaches 98 % recall on the inner
out-of-fold predictions (ties -> fewer trees x leaves). Revision-2 protocol: fall-record negatives,
fall-record false alarms counted.

    python -m src.experiments.t3_tune --folds 1,2,3     # per-fold results cached in results/raw/tune/
    python -m src.experiments.t3_tune --merge
"""
from __future__ import annotations

import argparse
import itertools
import time

import numpy as np
import pandas as pd

from ..eval import events as ev
from ..eval.common import (outer_folds, inner_groupkfold, subject_rows, window_metrics, COST_RATIOS,
                           SENS_TARGETS, SEED, RAW, TAB, FIG)
from ..features.feats import select
from ..models import trees

N_TREES = (50, 100, 150, 300, 500)
LEAVES = (7, 15, 31)
LRS = (0.03, 0.1)
MCS = (20, 50)
CW = (True, False)
BASE = list(itertools.product(LEAVES, LRS, MCS, CW))
OUT = RAW / "tune"
SENSORS = "A+B"


def _inner_fa_at_98(oof_prob: np.ndarray, oof_idx: pd.DataFrame, meta) -> tuple[float, float, float]:
    win = oof_idx.assign(prob=oof_prob)
    grid = ev.threshold_grid(oof_prob)
    pr = ev.per_record(win, meta, grid)
    thr = ev.pick_threshold(pr, grid, 0.98)
    i = int(np.searchsorted(grid, thr))
    sens, fah = ev.summarise(pr)
    return float(fah[i]), float(sens[i]), thr


def _thresholds(oof_prob, oof_idx, meta):
    win = oof_idx.assign(prob=oof_prob)
    grid = ev.threshold_grid(oof_prob)
    pr = ev.per_record(win, meta, grid)
    thr = {f"sens{int(q * 100)}": ev.pick_threshold(pr, grid, q) for q in SENS_TARGETS}
    for c in COST_RATIOS:
        thr[f"cost{c}"] = ev.pick_cost_threshold(pr, grid, c)
    return thr


def run_fold(test_s: int, train_s: np.ndarray, fs: dict, cols: list) -> None:
    path = OUT / f"fold{test_s:02d}.pkl"
    if path.exists():
        return
    t0 = time.time()
    meta = fs["meta"]
    sub_sl = meta.SubjectID.values[fs["sl"].rec.values]
    # ---- inner: out-of-fold probabilities for every (base setting, n_trees)
    oof = {(b, k): np.full(len(sub_sl), np.nan) for b in BASE for k in N_TREES}
    for itr, iva in inner_groupkfold(train_s):
        pos, neg = trees._train_rows(fs, itr, True)
        X, y = trees._xy(fs, [], pos, neg, cols)
        va = np.isin(sub_sl, iva)
        Xv = fs["F_sl"][va][:, cols]
        for b in BASE:
            leaves, lr, mcs, cw = b
            m = trees._fit("lgbm", X, y, SEED, dict(n_estimators=max(N_TREES), num_leaves=leaves,
                                                     learning_rate=lr, min_child_samples=mcs, class_weight=cw))
            for k in N_TREES:
                oof[(b, k)][va] = m.predict_proba(Xv, num_iteration=k)[:, 1]
    tr_mask = np.isin(sub_sl, train_s)
    oof_idx = fs["sl"][tr_mask][["rec", "t_end"]]
    inner = []
    for (b, k), p in oof.items():
        fah, sens, thr = _inner_fa_at_98(p[tr_mask], oof_idx, meta)
        inner.append(dict(fold=test_s, num_leaves=b[0], learning_rate=b[1], min_child_samples=b[2],
                          class_weight=b[3], n_estimators=k, inner_fa_per_h=fah, inner_sens=sens, inner_thr98=thr))
    inner = pd.DataFrame(inner)
    inner["size"] = inner.n_estimators * inner.num_leaves
    # ---- selections: overall best, and best per (n_trees, leaves) pair for the trade-off curve
    def best(df):
        return df.sort_values(["inner_fa_per_h", "size", "learning_rate"]).iloc[0]
    picks = {"tuned": best(inner)}
    for k in N_TREES:
        for lv in LEAVES:
            picks[f"t{k}_l{lv}"] = best(inner[(inner.n_estimators == k) & (inner.num_leaves == lv)])
    # ---- outer: refit each distinct base setting once (500 trees) on all training subjects
    pos, neg = trees._train_rows(fs, train_s, True)
    X, y = trees._xy(fs, [], pos, neg, cols)
    te = sub_sl == test_s
    an0 = (meta.SubjectID.values[fs["an"].rec.values] == test_s) & (fs["an"].offset.values == 0.0)
    fitted, rows, raw = {}, [], []
    for name, r in picks.items():
        b = (int(r.num_leaves), float(r.learning_rate), int(r.min_child_samples), bool(r.class_weight))
        if b not in fitted:
            fitted[b] = trees._fit("lgbm", X, y, SEED, dict(n_estimators=max(N_TREES), num_leaves=b[0],
                                                            learning_rate=b[1], min_child_samples=b[2], class_weight=b[3]))
        m, k = fitted[b], int(r.n_estimators)
        thr = _thresholds(oof[(b, k)][tr_mask], oof_idx, meta)
        p_sl = m.predict_proba(fs["F_sl"][te][:, cols], num_iteration=k)[:, 1]
        win = fs["sl"][te][["rec", "t_end"]].assign(prob=p_sl)
        p_an = m.predict_proba(fs["F_an"][an0][:, cols], num_iteration=k)[:, 1] if an0.any() else np.array([])
        negw = meta.label.values[fs["sl"].rec.values[te]] != "FALL"
        yw = np.r_[np.ones(an0.sum()), np.zeros(negw.sum())]
        pw = np.r_[p_an, p_sl[negw]]
        if name == "tuned":
            raw.append(win.assign(fold=test_s, model="M1lgbm_tuned"))
        for rule, t in thr.items():
            sr = subject_rows(ev.per_record(win, meta, np.array([t])), meta, 0)
            wm = window_metrics(yw, pw, (pw >= t).astype(int)) if yw.sum() > 0 else {}
            for _, srow in sr.iterrows():
                rows.append(dict(model="M1lgbm", sensors=SENSORS, odr=60, L=4, seed=SEED, tag="r2tune",
                                 variant=name, rule=rule, fold=test_s, thr=t, n_estimators=k, num_leaves=b[0],
                                 learning_rate=b[1], min_child_samples=b[2], class_weight=b[3],
                                 **srow.to_dict(), **wm))
    pd.to_pickle(dict(inner=inner, rows=pd.DataFrame(rows), raw=pd.concat(raw)), path)
    print(f"fold S{test_s:02d}: {time.time() - t0:.0f}s, chosen: {dict(picks['tuned'][['n_estimators', 'num_leaves', 'learning_rate', 'min_child_samples', 'class_weight']])}", flush=True)


def merge():
    parts = [pd.read_pickle(p) for p in sorted(OUT.glob("fold*.pkl"))]
    assert len(parts) == 14, f"only {len(parts)} folds finished"
    inner = pd.concat([p["inner"] for p in parts]); rows = pd.concat([p["rows"] for p in parts])
    raw = pd.concat([p["raw"] for p in parts])
    rows.to_csv(RAW / "subj_r2tune_AB_60_4.csv", index=False)
    raw.to_csv(RAW / "win_r2tune_AB_60_4.csv.gz", index=False)
    inner.to_csv(TAB / "r2_tune_inner_all.csv", index=False)
    chosen = rows[(rows.variant == "tuned") & (rows.rule == "sens98")][
        ["fold", "n_estimators", "num_leaves", "learning_rate", "min_child_samples", "class_weight"]]
    chosen.to_csv(TAB / "r2_tune_chosen_per_fold.csv", index=False)
    summ = trees.summary(rows)
    summ.to_csv(TAB / "r2_tune_summary.csv", index=False)
    # trade-off figure (LOSO test, sens98 target; other parameters nested-selected per pair)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = summ[(summ.rule == "sens98") & summ.variant.str.match(r"^t\d+_l\d+$")]
    s = s.assign(n_estimators=s.variant.str.extract(r"t(\d+)_")[0].astype(int),
                 num_leaves=s.variant.str.extract(r"_l(\d+)")[0].astype(int))
    s.to_csv(TAB / "r2_tune_tradeoff.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for lv, g in s.groupby("num_leaves"):
        g = g.sort_values("n_estimators")
        ax.errorbar(g.n_estimators, g.fa_per_h, yerr=[g.fa_per_h - g.fah_lo, g.fah_hi - g.fa_per_h],
                    marker="o", capsize=3, label=f"{lv} leaves")
    ax.set_xscale("log"); ax.set_xticks(N_TREES, [str(k) for k in N_TREES])
    ax.set_xlabel("number of trees"); ax.set_ylabel("false alarms / hour (LOSO, 98 % recall target)")
    ax.set_title("LightGBM size vs false alarms (A+B, 60 Hz, 4 s); lr / min_child / class weight nested-selected", fontsize=8)
    ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "r2_tune_tradeoff.png", dpi=120)
    print(summ[summ.variant == "tuned"][["rule", "sens", "fa_per_h", "fah_lo", "fah_hi", "n_fa"]].round(3).to_string(index=False))
    print(chosen.to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", default="")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge(); return
    OUT.mkdir(parents=True, exist_ok=True)
    ev.COUNT_FALL_FA = True
    fs = trees.feature_set(60, 4)
    cols = select(fs["names"], fs["grp"], SENSORS)
    want = {int(x) for x in a.folds.split(",")} if a.folds else None
    for test_s, train_s in outer_folds(fs["meta"]):
        if want is None or test_s in want:
            run_fold(test_s, train_s, fs, cols)


if __name__ == "__main__":
    main()
