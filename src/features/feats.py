"""Orientation-invariant window features (statistical + fall-phase), vectorised over windows.

Phases are anchored on the impact k = argmax |a| inside the window
(after Palmerini 2020 / Becker 2012): pre-impact [k-1 s, k), impact, post-impact [k+0.5 s, end].
Every feature uses |a|, |w|, pressure or angles between acceleration vectors, so a flipped
pendant gives the same features.
"""
from __future__ import annotations

import numpy as np

GROUPS = {"A": [], "G": [], "B": []}


def _masked(x, m, fn, fill=np.nan):
    xm = np.where(m, x, np.nan)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            v = fn(xm, axis=1)
    return np.where(m.any(1), v, fill)


def _angle(u, v):
    cos = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def _rolling_std(x, w):
    c1 = np.cumsum(np.pad(x, ((0, 0), (1, 0))), axis=1)
    c2 = np.cumsum(np.pad(x * x, ((0, 0), (1, 0))), axis=1)
    s1 = c1[:, w:] - c1[:, :-w]
    s2 = c2[:, w:] - c2[:, :-w]
    var = np.maximum(s2 / w - (s1 / w) ** 2, 0)
    out = np.full_like(x, np.nan)
    out[:, w - 1:] = np.sqrt(var)
    return out


def features(win: np.ndarray, odr: float) -> tuple[np.ndarray, list[str], list[str]]:
    """win: (N, W, 7) [ax ay az gx gy gz p]. Returns (F, names, group per feature)."""
    N, W, _ = win.shape
    acc, gyr, p = win[..., 0:3], win[..., 3:6], win[..., 6].astype(np.float64)
    amag = np.linalg.norm(acc, axis=-1)
    wmag = np.linalg.norm(gyr, axis=-1)
    t = np.arange(W)[None, :]
    k = amag.argmax(1)[:, None]
    s = lambda sec: int(round(sec * odr))
    pre = (t >= k - s(1.0)) & (t < k)
    early = t < np.maximum(k - s(0.5), s(0.25))
    post = t >= k + s(0.5)
    post = np.where(post.any(1, keepdims=True), post, t >= W - s(0.25))
    F, names, grp = [], [], []

    def add(name, v, g):
        F.append(np.asarray(v, dtype=np.float32)); names.append(name); grp.append(g)

    # --- acceleration magnitude: statistics
    add("a_mean", amag.mean(1), "A"); add("a_std", amag.std(1), "A")
    add("a_min", amag.min(1), "A"); add("a_max", amag.max(1), "A")
    add("a_ptp", np.ptp(amag, 1), "A"); add("a_energy", ((amag - 1) ** 2).mean(1), "A")
    c = amag - 1.0
    add("a_cross1g", (np.signbit(c[:, 1:]) != np.signbit(c[:, :-1])).sum(1), "A")
    pk = (amag[:, 1:-1] > amag[:, :-2]) & (amag[:, 1:-1] >= amag[:, 2:]) & (amag[:, 1:-1] > 2.0)
    add("a_npeaks2g", pk.sum(1), "A")
    # --- fall phases
    add("ph_pre_min", _masked(amag, pre, np.nanmin, 1.0), "A")
    k0 = np.clip(k[:, 0] - s(0.25), 0, None)
    pre_short = (t >= k0[:, None]) & (t < k)
    add("ph_impact_slope", (amag.max(1) - _masked(amag, pre_short, np.nanmin, 1.0)) / 0.25, "A")
    add("ph_peak_pos", k[:, 0] / W, "A")
    add("ph_post_std", _masked(amag, post, np.nanstd, 0.0), "A")
    add("ph_post_dev", _masked(np.abs(amag - 1), post, np.nanmean, 0.0), "A")
    rs = _rolling_std(amag, s(0.25))
    add("ph_still_frac", _masked((rs < 0.03).astype(float), post & ~np.isnan(rs), np.nanmean, 0.0), "A")
    g_pre = (acc * early[..., None]).sum(1) / np.maximum(early.sum(1), 1)[:, None]
    g_post = (acc * post[..., None]).sum(1) / np.maximum(post.sum(1), 1)[:, None]
    add("ph_posture_deg", _angle(g_pre, g_post), "A")
    last = t >= W - s(1.0)
    g_last = (acc * last[..., None]).sum(1) / last.sum(1)[:, None]
    add("ph_posture_end_deg", _angle(acc[:, :s(0.5)].mean(1), g_last), "A")
    # --- gyroscope
    add("w_mean", wmag.mean(1), "G"); add("w_std", wmag.std(1), "G"); add("w_max", wmag.max(1), "G")
    add("w_energy", (wmag ** 2).mean(1), "G")
    add("ph_w_pre_max", _masked(wmag, pre, np.nanmax, 0.0), "G")
    add("ph_w_post_mean", _masked(wmag, post, np.nanmean, 0.0), "G")
    # integrated rotation angle (deg) over the second around impact
    around = (t >= k - s(1.0)) & (t < k + s(0.5))
    add("ph_w_rot_deg", (wmag * around).sum(1) / odr, "G")
    # --- pressure (relative; +dP = moved down)
    pre_p = t < np.maximum(k - s(0.5), 1)
    add("p_dP", _masked(p, post, np.nanmedian) - _masked(p, pre_p, np.nanmedian), "B")
    n0 = max(1, s(0.5))
    add("p_end_minus_start", p[:, -n0:].mean(1) - p[:, :n0].mean(1), "B")
    tt = (np.arange(W) - (W - 1) / 2) / odr
    add("p_slope", ((p - p.mean(1, keepdims=True)) * tt).sum(1) / (tt ** 2).sum(), "B")
    add("p_range", np.ptp(p, 1), "B")
    return np.column_stack(F), names, grp


def select(names, grp, sensors: str):
    keep = {"A"} | ({"G"} if "G" in sensors else set()) | ({"B"} if "B" in sensors else set())
    return [i for i, g in enumerate(grp) if g in keep]
