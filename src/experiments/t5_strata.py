"""Revision 2, task 5: recall of M1 LightGBM A+B by impact strength (peak |a|), by pressure step (dP),
and per subject. Peak |a| and dP come from the data audit (native 238 Hz / 10 Hz, independent of the model)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.preprocess import build
from ..eval import events as ev
from ..eval.common import RAW, TAB
from ..eval.report import per_activity

A_BINS = [0, 2, 3, 4, 6, np.inf]; A_LAB = ["<2 g", "2–3 g", "3–4 g", "4–6 g", ">6 g"]
P_BINS = [-np.inf, 3, 6, 10, np.inf]; P_LAB = ["<3 Pa", "3–6 Pa", "6–10 Pa", ">10 Pa"]


def strata(run: str, model: str, out: str):
    ev.COUNT_FALL_FA = True
    meta = build(60)["meta"]
    audit = pd.read_csv(TAB / "audit_recordings.csv")[["SubjectID", "ActivityID", "TrialNo", "peak_amag_g", "dP_pa"]]
    win = pd.read_csv(RAW / f"win_{run}.csv.gz"); subj = pd.read_csv(RAW / f"subj_{run}.csv")
    rows = []
    for rule in ("sens95", "sens98", "sens99"):
        _, r = per_activity(win, subj, meta, model, rule)
        f = r[r.is_fall].merge(audit, on=["SubjectID", "ActivityID", "TrialNo"], how="left")
        f["a_bin"] = pd.cut(f.peak_amag_g, A_BINS, labels=A_LAB, right=False)
        f["p_bin"] = pd.cut(f.dP_pa, P_BINS, labels=P_LAB, right=False).cat.add_categories("n/a").fillna("n/a")
        for col, kind in (("a_bin", "peak |a|"), ("p_bin", "dP"), ("SubjectID", "subject")):
            g = f.groupby(col, observed=True)
            for k, gg in g:
                rows.append(dict(rule=rule, stratum=kind, bin=str(k), n_falls=len(gg), n_det=int(gg.det.sum()),
                                 recall=gg.det.mean()))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / out, index=False)
    return df


if __name__ == "__main__":
    import sys
    run, model, out = sys.argv[1:4]
    d = strata(run, model, out)
    print(d[d.rule == "sens98"].round(3).to_string(index=False))
