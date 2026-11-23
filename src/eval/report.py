"""Tables and figures from results/raw: error analysis, sensitivity-vs-false-alarm curves, Q1 chart."""
from __future__ import annotations

import glob

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

from ..data.preprocess import build
from . import events as ev
from .common import RAW, TAB, FIG, subject_rows, pooled

ACTS = pd.read_csv(RAW.parents[1] / "configs" / "activities.csv").set_index("ActivityID")


def load_run(name: str):
    win = pd.read_csv(RAW / f"win_{name}.csv.gz")
    subj = pd.read_csv(RAW / f"subj_{name}.csv")
    return win, subj


def per_activity(win: pd.DataFrame, subj: pd.DataFrame, meta: pd.DataFrame, model: str,
                 rule: str = "sens95") -> pd.DataFrame:
    """Per-record outcome at each fold's own threshold -> per ActivityID counts."""
    out = []
    for f, w in win[win.model == model].groupby("fold"):
        thr = subj[(subj.model == model) & (subj.fold == f) & (subj.rule == rule)].thr.iloc[0]
        pr = ev.per_record(w, meta, np.array([thr]))
        out.append(pd.DataFrame(dict(rec=pr["rec"], det=pr["det"][:, 0], fa=pr["fa"][:, 0],
                                     is_fall=pr["is_fall"])))
    r = pd.concat(out)
    r = r.join(meta[["SubjectID", "ActivityID", "TrialNo", "label", "recovery"]], on="rec")
    g = r.groupby("ActivityID")
    a = pd.DataFrame(dict(label=g.label.first(), n=g.size(), n_det=g.det.sum(), n_fa=g.fa.sum(),
                          recs_with_fa=g.fa.apply(lambda x: (x > 0).sum())))
    a["missed"] = np.where(a.label == "FALL", a.n - a.n_det, 0)
    a["description"] = ACTS.loc[a.index, "description"].str.replace("\n", " ").str[:70]
    return a, r


def curve(win: pd.DataFrame, meta: pd.DataFrame, model: str, n: int = 300):
    """Pooled sensitivity vs FA/h, sweeping one global threshold over all LOSO test predictions."""
    w = win[win.model == model]
    grid = ev.threshold_grid(w.prob.values, n)
    pr = ev.per_record(w[["rec", "t_end", "prob"]], meta, grid)
    return ev.summarise(pr)


def wilcoxon_fa(a: pd.DataFrame, b: pd.DataFrame) -> tuple[float, float]:
    """Paired by subject: FA/h of a vs b. Returns (median difference, p)."""
    m = a.merge(b, on="SubjectID", suffixes=("_a", "_b"))
    da = m.n_fa_a / m.hours_a - m.n_fa_b / m.hours_b
    if (da == 0).all():
        return 0.0, 1.0
    return float(np.median(da)), float(wilcoxon(m.n_fa_a / m.hours_a, m.n_fa_b / m.hours_b).pvalue)


def q1_chart(summ: pd.DataFrame):
    s = summ[(summ.model == "M1lgbm") & summ.rule.isin(["sens95", "sens98", "sens99"])]
    order = ["A", "A+G", "A+B", "A+G+B"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    w = 0.25
    for j, rule in enumerate(["sens95", "sens98", "sens99"]):
        g = s[s.rule == rule].set_index("sensors").loc[order]
        x = np.arange(len(order)) + (j - 1) * w
        err = np.vstack([g.fa_per_h - g.fah_lo, g.fah_hi - g.fa_per_h])
        ax.bar(x, g.fa_per_h, w, yerr=err, capsize=3, label=f"recall target {rule[4:]} %")
        for xi, (fa, se) in enumerate(zip(g.fa_per_h, g.sens)):
            ax.text(x[xi], fa + 0.3, f"{se * 100:.1f}%", ha="center", fontsize=7, rotation=90)
    ax.set_xticks(np.arange(len(order)), ["A (accel)", "A+G (+gyro)", "A+B (+pressure)", "A+G+B"])
    ax.set_ylabel("false alarms per hour of ADL (95 % CI)")
    ax.set_title("M1 LightGBM, 60 Hz, 4 s window, LOSO (label above bar = achieved recall)", fontsize=9)
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "q1_sensors.png", dpi=120)


def example_plot(win: pd.DataFrame, subj: pd.DataFrame, r: pd.DataFrame, model: str, rule: str, fname: str):
    """2 missed falls (most-missed activities) + 2 false-alarm records, with |a|, pressure and score."""
    d = build(60)
    X, meta = d["X"], d["meta"]
    missed = r[r.is_fall & ~r.det]
    top = missed.ActivityID.value_counts().index[:2]
    picks = [missed[missed.ActivityID == a].iloc[0] for a in top]
    fa = r[(~r.is_fall) & (r.fa > 0)].sort_values("fa", ascending=False)
    picks += [fa.iloc[i] for i in range(min(2, len(fa)))]
    fig, axes = plt.subplots(len(picks), 1, figsize=(10, 2.6 * len(picks)), sharex=True)
    for ax, row in zip(np.atleast_1d(axes), picks):
        rec = int(row.rec)
        x = X[rec]; t = np.arange(len(x)) / 60
        ax.plot(t, np.linalg.norm(x[:, :3], axis=1), lw=.7, label="|a| [g]")
        ax2 = ax.twinx()
        ax2.plot(t, x[:, 6] - np.median(x[:30, 6]), color="k", lw=.8, label="ΔP [Pa]")
        ax2.set_ylabel("ΔP [Pa]")
        w = win[(win.model == model) & (win.rec == rec)]
        thr = subj[(subj.model == model) & (subj.fold == row.SubjectID) & (subj.rule == rule)].thr.iloc[0]
        ax.plot(w.t_end, w.prob * 5, "o-", ms=2, color="C3", lw=.8, label="score x5 (at window end)")
        ax.axhline(thr * 5, color="C3", ls="--", lw=.6)
        if row.is_fall:
            ax.axvspan(meta.t_impact[rec] - 1, meta.t_impact[rec] + 5, color="C2", alpha=.12)
        kind = "MISSED FALL" if row.is_fall else f"FALSE ALARM x{int(row.fa)}"
        desc = ACTS.loc[row.ActivityID, "description"].replace("\n", " ")[:70]
        ax.set_title(f"{kind}: S{row.SubjectID:02d} A{row.ActivityID} T{row.TrialNo:02d} - {desc}", fontsize=8)
        ax.legend(loc="upper left", fontsize=6); ax2.legend(loc="upper right", fontsize=6)
    np.atleast_1d(axes)[-1].set_xlabel("t [s]")
    fig.tight_layout(); fig.savefig(FIG / fname, dpi=110)


def main():
    meta = build(60)["meta"]
    runs = {}
    for f in sorted(glob.glob(str(RAW / "subj_*.csv"))):
        name = f.split("subj_")[1][:-4]
        if name.startswith("quick"):
            continue
        runs[name] = load_run(name)
    # error analysis at each recall target for every LOSO run at 60 Hz / 4 s
    for name, (win, subj) in runs.items():
        if not name.endswith("60_4") and "60_4_s" not in name:
            continue
        for model in win.model.unique():
            for rule in ("sens95", "sens98", "sens99"):
                if rule not in set(subj[subj.model == model].rule):
                    continue
                a, r = per_activity(win, subj, meta, model, rule)
                a.to_csv(TAB / f"errors_{name}_{model}_{rule}.csv")
                rr = r[r.is_fall]
                pd.DataFrame(dict(recall=rr.groupby("recovery").det.mean(),
                                  n=rr.groupby("recovery").size())).to_csv(
                    TAB / f"recall_by_recovery_{name}_{model}_{rule}.csv")
                if name == "trees_AB_60_4" and model == "M1lgbm" and rule == "sens98":
                    example_plot(win, subj, r, model, rule, "examples_M1lgbm_AB_sens98.png")
    # sensitivity vs false alarms (one global threshold over pooled LOSO predictions)
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, (win, subj) in runs.items():
        if not (name.startswith("trees_") or name.startswith("nn_")):
            continue
        for model in win.model.unique():
            if model in ("M0", "M1tree"):
                continue
            sens, fah = curve(win, meta, model)
            ax.plot(fah, sens, label=f"{model} {subj.sensors.iloc[0]}", ls="--" if model == "M2" else "-")
    ax.set_xscale("symlog", linthresh=1); ax.set_xlim(0, 60); ax.set_ylim(0.85, 1.0)
    for y in (0.95, 0.98, 0.99):
        ax.axhline(y, color="k", lw=.5, ls=":")
    ax.set_xlabel("false alarms per hour of ADL"); ax.set_ylabel("fall recall (events)")
    ax.set_title("LOSO, 60 Hz, 4 s; one global threshold swept over pooled test scores", fontsize=9)
    ax.legend(fontsize=7); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "curve_recall_vs_fah.png", dpi=120)
    q1_chart(pd.read_csv(TAB / "summary_trees.csv"))


if __name__ == "__main__":
    main()
