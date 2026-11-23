"""Event-level (streaming) evaluation.

- Alerts = sliding windows (step 0.5 s) whose probability >= threshold, at time t_end.
- Alerts closer than 10 s to the previous alert belong to the same event.
- A fall is detected if any alert falls in [t_impact - 1 s, t_impact + 5 s].
- Every event in an ADL / NEAR_FALL record is a false alarm.
- Negative time = n_windows x 0.5 s per record (time where a decision was made).
- Revision 2 (COUNT_FALL_FA = True, default): in a FALL record, every event (chain of alerts) that
  has no alert inside the detection window is also a false alarm, and the decision time outside
  the detection window is added to the denominator. Set COUNT_FALL_FA = False for the old rule.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MERGE_S, PRE_S, POST_S, STEP_S = 10.0, 1.0, 5.0, 0.5
COUNT_FALL_FA = True


def _events_per_record(t: np.ndarray, alert: np.ndarray) -> np.ndarray:
    """alert: (n_thr, n_win) bool, t sorted. Returns number of merged events per threshold."""
    n_thr, n = alert.shape
    idx = np.where(alert, np.arange(n)[None, :], -1)
    prev = np.maximum.accumulate(np.concatenate([np.full((n_thr, 1), -1), idx[:, :-1]], 1), axis=1)
    gap_ok = np.where(prev >= 0, t[None, :] - t[np.clip(prev, 0, None)] >= MERGE_S, True)
    return (alert & gap_ok).sum(1)


def _chains_with_hit(t: np.ndarray, P: np.ndarray, inwin: np.ndarray, th: np.ndarray) -> np.ndarray:
    """Number of alert chains that contain at least one in-window alert. P, inwin: (r, n); th: (k,)."""
    A = P[:, None, :] >= th[None, :, None]                       # (r, k, n)
    n = P.shape[1]
    idx = np.where(A, np.arange(n)[None, None, :], -1)
    prev = np.full_like(idx, -1)
    np.maximum.accumulate(idx[..., :-1], axis=2, out=prev[..., 1:])
    start = A & ((prev < 0) | (t[None, None, :] - t[np.clip(prev, 0, None)] >= MERGE_S))
    cid = np.cumsum(start, axis=2) * A                           # chain id of each alert, 0 = no alert
    c = np.where(inwin[:, None, :], cid, 0)
    pm = np.zeros_like(c)
    np.maximum.accumulate(c[..., :-1], axis=2, out=pm[..., 1:])
    return ((c > 0) & (c > pm)).sum(2)


def per_record(win: pd.DataFrame, meta: pd.DataFrame, thresholds: np.ndarray,
               post_s: float = POST_S, count_fall_fa: bool | None = None) -> dict:
    """win: rows of sliding windows with columns rec, t_end, prob.
    Returns dict of arrays (records x thresholds): detected (falls), fa, hours, plus record info.
    post_s: end of the detection window after the impact (5 s; larger for the long-lie detector)."""
    thresholds = np.atleast_1d(thresholds)
    count_fall_fa = COUNT_FALL_FA if count_fall_fa is None else count_fall_fa
    w = win.sort_values(["rec", "t_end"], kind="stable")
    recs, counts = np.unique(w.rec.values, return_counts=True)
    if len(np.unique(counts)) == 1:   # fast path: every record has the same number of windows
        n = counts[0]
        P = w.prob.values.reshape(len(recs), n)
        T = w.t_end.values.reshape(len(recs), n)
        fall = meta.label.values[recs] == "FALL"
        ti = meta.t_impact.values[recs][:, None]
        inwin = (T >= ti - PRE_S) & (T <= ti + post_s)
        mx = np.where(inwin, P, -np.inf).max(1)
        det = (mx[:, None] >= thresholds[None, :]) & fall[:, None]
        assert (T == T[0]).all()           # same decision-time grid in every record
        t = T[0]
        # window i starts a new event at threshold th  <=>  M_i < th <= p_i,
        # M_i = max prob of earlier windows less than MERGE_S before t_i (-inf if none)
        M = np.full_like(P, -np.inf)
        for dsh in range(1, n):
            if t[dsh] - t[0] >= MERGE_S:
                break
            M[:, dsh:] = np.maximum(M[:, dsh:], P[:, :-dsh])
        thr_sorted = np.all(np.diff(thresholds) >= 0)
        th = thresholds if thr_sorted else np.sort(thresholds)
        lo = np.searchsorted(th, M, side="right")
        hi = np.searchsorted(th, P, side="right")
        D = np.zeros((len(recs), len(th) + 1), np.int32)
        rows = np.repeat(np.arange(len(recs)), n)
        v = (hi > lo).ravel().astype(np.int32)
        np.add.at(D, (rows, lo.ravel()), v)
        np.add.at(D, (rows, hi.ravel()), -v)
        ev_count = np.cumsum(D, 1)[:, :-1]
        if not thr_sorted:
            ev_count = ev_count[:, np.argsort(np.argsort(thresholds))]
        if count_fall_fa:
            if PRE_S + post_s < MERGE_S:
                # all in-window alerts lie < MERGE_S apart -> they form exactly one chain when detected
                hit = det.astype(np.int64)
            else:
                hit = np.zeros_like(ev_count)
                fi = np.where(fall)[0]
                for j in range(0, len(fi), 256):
                    b = fi[j:j + 256]
                    hit[b] = _chains_with_hit(t, P[b], inwin[b], th)[:, np.argsort(np.argsort(thresholds))] \
                        if not thr_sorted else _chains_with_hit(t, P[b], inwin[b], th)
            fa = np.where(fall[:, None], ev_count - hit, ev_count)
            hours = np.where(fall, (~inwin).sum(1), n) * STEP_S / 3600
        else:
            fa = np.where(fall[:, None], 0, ev_count)
            hours = np.where(fall, 0.0, n * STEP_S / 3600)
        return dict(rec=recs, det=det, fa=fa, hours=hours, is_fall=fall)
    det, fa, hours, is_fall = [], [], [], []
    g = win.sort_values(["rec", "t_end"]).groupby("rec")
    for r, d in g:
        t, pr = d.t_end.values, d.prob.values
        if meta.label.values[r] == "FALL":
            ti = meta.t_impact.values[r]
            m = (t >= ti - PRE_S) & (t <= ti + post_s)
            mx = pr[m].max() if m.any() else -np.inf
            det.append(mx >= thresholds)
            if count_fall_fa:
                alert = pr[None, :] >= thresholds[:, None]
                hit = _chains_with_hit(t, pr[None, :], m[None, :], thresholds)[0]
                fa.append(_events_per_record(t, alert) - hit)
                hours.append((~m).sum() * STEP_S / 3600)
            else:
                fa.append(np.zeros(len(thresholds), int)); hours.append(0.0)
            is_fall.append(True)
        else:
            alert = pr[None, :] >= thresholds[:, None]
            fa.append(_events_per_record(t, alert)); det.append(np.zeros(len(thresholds), bool))
            hours.append(len(t) * STEP_S / 3600); is_fall.append(False)
    recs = np.array(list(g.groups.keys()))
    return dict(rec=recs, det=np.array(det), fa=np.array(fa), hours=np.array(hours),
                is_fall=np.array(is_fall))


def summarise(pr: dict) -> tuple[np.ndarray, np.ndarray]:
    """Pooled sensitivity and false alarms per hour for each threshold."""
    f = pr["is_fall"]
    sens = pr["det"][f].mean(0) if f.any() else np.full(pr["det"].shape[1], np.nan)
    fah = pr["fa"].sum(0) / pr["hours"].sum()     # fall records contribute only under COUNT_FALL_FA
    return sens, fah


def pick_threshold(pr: dict, thresholds: np.ndarray, target_sens: float = 0.95) -> float:
    """Highest threshold with pooled sensitivity >= target (fewest false alarms)."""
    sens, _ = summarise(pr)
    ok = np.where(sens >= target_sens)[0]
    return float(thresholds[ok.max()]) if len(ok) else float(thresholds.min())


def pick_cost_threshold(pr: dict, thresholds: np.ndarray, ratio: float) -> float:
    f = pr["is_fall"]
    miss = (~pr["det"][f]).sum(0)
    fa = pr["fa"].sum(0)
    cost = ratio * miss + fa
    # highest threshold among those with minimal cost
    return float(thresholds[len(cost) - 1 - np.argmin(cost[::-1])])


def threshold_grid(probs: np.ndarray, n: int = 400) -> np.ndarray:
    q = np.unique(np.quantile(probs, np.linspace(0, 1, n)))
    return np.unique(np.concatenate([q, [0.0, 1.0 + 1e-9]]))
