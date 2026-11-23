"""Revision 2, task 6: slow falls and falls from bed (ActivityID 135, 127, 130).

Part A - impact-free features added to M1 LightGBM A+B (60 Hz, 4 s decision window); the slow
features are computed on a window of Ls = 4, 6 or 8 s ending at the same decision time.

Part B - stand-alone "long lie" detector, combined with M1 (A+B, revision-2 run, 98 % recall
threshold of each fold) by OR. Decision every 0.5 s at time t, for T in {5, 8, 10} s:
  still   : the current still run (rolling std of |a| over 0.5 s < 0.03 g) has lasted >= T s;
            s0 = start of that still run
  lying   : angle between mean acceleration of the still run and of the reference [s0-4 s, s0-1 s]
            (posture before the event; the last second before s0 is skipped) >= 45 deg
  lower   : median pressure of the still run - median pressure of the reference > 0 Pa
Fixed a-priori constants (not tuned on any data). Records are 20 s long and impacts are at ~10 s,
so at most ~9 s of lying is observable; real systems use 30-60 s, which cannot be evaluated here.
Scoring: a long-lie alert counts as a detection if it is at or after impact - 1 s (lying comes after
the impact). Extra false alarms = additional merged events (10 s) that the long-lie alerts create on
top of M1's alerts, in ADL / near-fall records and in fall records before impact - 1 s.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.preprocess import build
from ..data.windows import sliding_index
from ..eval import events as ev
from ..eval.common import RAW, TAB
from ..features.extra import build_features
from ..features.feats import select, _angle, _rolling_std
from ..models import trees

SLOW_IDS = (135, 127, 130)
T_LIST = (5, 8, 10)
STILL_G, LYING_DEG, REF_S, GAP_S = 0.03, 45.0, 3.0, 1.0


def part_a():
    ev.COUNT_FALL_FA = True
    fs = trees.feature_set(60, 4)
    icols = select(fs["names"], fs["grp"], "A+B")
    res = []
    for Ls in (4, 6, 8):
        sf = build_features("slow", Ls=Ls)
        fv = {k: np.hstack([fs[k][:, icols], sf[k]]) for k in ("F_sl", "F_an")}
        fv["cols"] = list(range(fv["F_sl"].shape[1]))
        res.append(trees.run("A+B", 60, 4, models=("M1lgbm",), tag="r2slow", fv=fv, variant=f"slowLs{Ls}"))
    return pd.concat(res)


def long_lie_flags(T: float) -> pd.DataFrame:
    d = build(60)
    X, meta, odr = d["X"], d["meta"], d["odr"]
    n = np.array([len(x) for x in X])
    sl = sliding_index(meta, n, odr, 4)
    flags = np.zeros(len(sl), bool)
    k = int(round(T * odr)); kr = int(round(REF_S * odr)); kg = int(round(GAP_S * odr))
    for r in range(len(X)):
        x = X[r]; amag = np.linalg.norm(x[:, :3], axis=1)
        rs = _rolling_std(amag[None, :], int(round(0.5 * odr)))[0]
        still = rs < STILL_G
        # start index of the still run that contains sample i (-1 if not still)
        run_start = np.full(len(still), -1)
        s0 = -1
        for i, st in enumerate(still):
            s0 = (i if s0 < 0 else s0) if st else -1
            run_start[i] = s0
        rows = np.where(sl.rec.values == r)[0]
        for j in rows:
            e = int(round(sl.t_end.values[j] * odr))       # decision at sample e (exclusive end)
            s0 = run_start[e - 1]
            if s0 < 0 or e - s0 < k or s0 - kg - kr < 0:
                continue
            g_now = x[s0:e, :3].mean(0); g_ref = x[s0 - kg - kr:s0 - kg, :3].mean(0)
            if _angle(g_now[None], g_ref[None])[0] < LYING_DEG:
                continue
            dp = np.median(x[s0:e, 6]) - np.median(x[s0 - kg - kr:s0 - kg, 6])
            flags[j] = dp > 0
    return sl.assign(ll=flags)


def _events(t, a):
    """number of merged events for a boolean alert vector a on times t"""
    return int(ev._events_per_record(t, a[None, :])[0]) if a.any() else 0


def part_b(m1_run: str = "r2_AB_60_4", rule: str = "sens98") -> pd.DataFrame:
    meta = build(60)["meta"]
    win = pd.read_csv(RAW / f"win_{m1_run}.csv.gz"); subj = pd.read_csv(RAW / f"subj_{m1_run}.csv")
    win = win[win.model == "M1lgbm"]
    thr = subj[(subj.model == "M1lgbm") & (subj.rule == rule)].set_index("fold").thr
    win = win.assign(m1=win.prob.values >= thr.loc[win.fold.values].values)
    rows, per_rec = [], []
    for T in T_LIST:
        ll = long_lie_flags(T)[["rec", "t_end", "ll"]]
        w = win.merge(ll, on=["rec", "t_end"], how="left").sort_values(["rec", "t_end"])
        assert w.ll.notna().all()
        extra_fa = 0; hours = 0.0; caught = []; ll_alone_det = 0; n_m1_missed = 0
        for r, g in w.groupby("rec"):
            t = g.t_end.values; m1 = g.m1.values; lla = g.ll.values.astype(bool)
            if meta.label.values[r] == "FALL":
                ti = meta.t_impact.values[r]
                m1_det = (m1 & (t >= ti - ev.PRE_S) & (t <= ti + ev.POST_S)).any()
                ll_det = (lla & (t >= ti - ev.PRE_S)).any()
                ll_alone_det += ll_det
                if not m1_det:
                    n_m1_missed += 1
                    if ll_det:
                        caught.append(int(meta.ActivityID.values[r]))
                pre = t < ti - ev.PRE_S                     # long-lie alerts here are false alarms
                extra_fa += _events(t[pre], (m1 | lla)[pre]) - _events(t[pre], m1[pre])
                per_rec.append(dict(T=T, rec=r, ActivityID=int(meta.ActivityID.values[r]), m1_det=m1_det, ll_det=ll_det))
            else:
                extra_fa += _events(t, m1 | lla) - _events(t, m1)
        hours = subj[(subj.model == "M1lgbm") & (subj.rule == rule)].hours.sum()
        n_fa_m1 = subj[(subj.model == "M1lgbm") & (subj.rule == rule)].n_fa.sum()
        nf = (meta.label == "FALL").sum()
        rows.append(dict(T_s=T, m1_rule=rule, n_falls=int(nf), m1_missed=n_m1_missed, caught_by_longlie=len(caught),
                         caught_ids=",".join(map(str, sorted(caught))),
                         recall_m1=1 - n_m1_missed / nf, recall_or=1 - (n_m1_missed - len(caught)) / nf,
                         longlie_alone_recall=ll_alone_det / nf,
                         fa_m1=int(n_fa_m1), extra_fa=int(extra_fa), hours=hours,
                         fa_per_h_m1=n_fa_m1 / hours, fa_per_h_or=(n_fa_m1 + extra_fa) / hours))
    pr = pd.DataFrame(per_rec)
    slow = pr[pr.ActivityID.isin(SLOW_IDS)].groupby(["T", "ActivityID"]).agg(
        n=("rec", "size"), m1_det=("m1_det", "sum"), ll_det=("ll_det", "sum"),
        or_det=("ll_det", lambda s: int((s | pr.loc[s.index, "m1_det"]).sum()))).reset_index()
    slow.to_csv(TAB / "r2_longlie_slow_ids.csv", index=False)
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "r2_longlie_or.csv", index=False)
    return out, slow


def main():
    res = part_a()
    s = trees.summary(res)
    s.to_csv(TAB / "r2_slow_summary.csv", index=False)
    print(s[s.rule.isin(["sens98", "sens99"])][["variant", "rule", "sens", "fa_per_h", "n_fa"]].round(3).to_string(index=False))
    out, slow = part_b()
    print(out.round(3).to_string(index=False)); print(slow.to_string(index=False))


if __name__ == "__main__":
    main()
