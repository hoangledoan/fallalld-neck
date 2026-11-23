"""Revision 2: paired per-subject tests between runs (Wilcoxon on FA/h and on recall)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from ..eval.common import RAW, TAB


def _subj(run: str, rule: str, model: str = "M1lgbm", variant: str | None = None):
    r = pd.read_csv(RAW / f"subj_{run}.csv")
    r = r[(r.model == model) & (r.rule == rule)]
    if variant is not None:
        r = r[r.variant == variant]
    return r


def paired(a: pd.DataFrame, b: pd.DataFrame, name_a: str, name_b: str, rule: str) -> dict:
    m = a.merge(b, on="SubjectID", suffixes=("_a", "_b"))
    assert len(m) == 14
    fa, fb = m.n_fa_a / m.hours_a, m.n_fa_b / m.hours_b
    p_fa = wilcoxon(fa, fb).pvalue if (fa != fb).any() else 1.0
    f = m[m.n_falls_a > 0]
    ra, rb = f.n_det_a / f.n_falls_a, f.n_det_b / f.n_falls_b
    p_r = wilcoxon(ra, rb).pvalue if (ra != rb).any() else 1.0
    return dict(rule=rule, a=name_a, b=name_b,
                recall_a=f.n_det_a.sum() / f.n_falls_a.sum(), recall_b=f.n_det_b.sum() / f.n_falls_b.sum(),
                fa_per_h_a=m.n_fa_a.sum() / m.hours_a.sum(), fa_per_h_b=m.n_fa_b.sum() / m.hours_b.sum(),
                n_fa_a=int(m.n_fa_a.sum()), n_fa_b=int(m.n_fa_b.sum()),
                subj_fa_lower_a=int((fa < fb).sum()), subj_fa_lower_b=int((fa > fb).sum()),
                p_fa=p_fa, p_recall=p_r)


def task2():
    rows = []
    for cfg in ("A", "AB", "AGB"):
        for rule in ("sens95", "sens98", "sens99"):
            rows.append(paired(_subj(f"r2_{cfg}_60_4", rule), _subj(f"r2recount_{cfg}_60_4", rule),
                               f"{cfg} retrain (+fall negatives)", f"{cfg} old training", rule))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "r2_task2_paired.csv", index=False)
    return df



def task4():
    rows = []
    for rule in ("sens98", "sens99"):
        g = lambda v: _subj("r2h2_AB_60_4_" + v, rule)
        for a, b in (("inv_orig", "axis_orig"), ("inv_orig", "axis_rotaug_orig"), ("inv_orig", "inv_axis_orig"),
                     ("axis_orig", "axis_rot"), ("axis_rotaug_orig", "axis_rotaug_rot"),
                     ("inv_axis_orig", "inv_axis_rot"), ("inv_orig", "inv_rot")):
            rows.append(paired(g(a), g(b), a, b, rule))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "r2_h2_paired.csv", index=False)
    return df


def task6():
    from ..data.preprocess import build
    from ..eval.report import per_activity
    meta = build(60)["meta"]
    rows, prow = [], []
    runs = {"base (r2)": "r2_AB_60_4", **{f"slow Ls={L}": f"r2slow_AB_60_4_slowLs{L}" for L in (4, 6, 8)}}
    for rule in ("sens98", "sens99"):
        for name, run in runs.items():
            win = pd.read_csv(RAW / f"win_{run}.csv.gz"); subj = pd.read_csv(RAW / f"subj_{run}.csv")
            a, _ = per_activity(win, subj, meta, "M1lgbm", rule)
            for aid in (135, 127, 130):
                rows.append(dict(rule=rule, run=name, ActivityID=aid, n=int(a.loc[aid, "n"]),
                                 detected=int(a.loc[aid, "n_det"]), missed=int(a.loc[aid, "missed"])))
            if name != "base (r2)":
                prow.append(paired(_subj(run, rule), _subj("r2_AB_60_4", rule), name, "base (r2)", rule))
    pd.DataFrame(rows).to_csv(TAB / "r2_slow_by_id.csv", index=False)
    pd.DataFrame(prow).to_csv(TAB / "r2_slow_paired.csv", index=False)
    return pd.DataFrame(rows), pd.DataFrame(prow)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    for f in (task2, task4):
        print(f().round(4).to_string(index=False))
    for d in task6():
        print(d.round(4).to_string(index=False))
