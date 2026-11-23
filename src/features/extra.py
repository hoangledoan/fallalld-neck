"""Revision 2 feature sets, row-aligned with trees.feature_set (same sliding / anchored windows).

- axis_features: raw per-axis acceleration statistics (NOT orientation invariant) for H2
- slow_features: impact-free features for slow falls / falls from bed, on a window of length Ls
  that ends at the same decision time (Ls >= L; start padded with the first sample if t_end < Ls)
- rotate_records: one random 3D rotation per record (pendant flipped), for robustness tests
"""
from __future__ import annotations

import pickle

import numpy as np

from ..data.load import ROOT
from ..data.preprocess import build
from ..data.windows import sliding_index, anchored_index
from .feats import features as base_features, _angle, _rolling_std

CACHE = ROOT / "cache"
OFFSETS = (-0.5, -0.25, 0.0, 0.25, 0.5)   # must match trees.OFFSETS


def rotate_records(X: list, seed: int) -> list:
    rng = np.random.default_rng(seed)
    out = []
    for x in X:
        q = rng.normal(size=4); q /= np.linalg.norm(q)
        w, a, b, c = q
        R = np.array([[1 - 2 * (b * b + c * c), 2 * (a * b - c * w), 2 * (a * c + b * w)],
                      [2 * (a * b + c * w), 1 - 2 * (a * a + c * c), 2 * (b * c - a * w)],
                      [2 * (a * c - b * w), 2 * (b * c + a * w), 1 - 2 * (a * a + b * b)]], np.float32)
        y = x.copy()
        y[:, 0:3] = x[:, 0:3] @ R.T
        y[:, 3:6] = x[:, 3:6] @ R.T
        out.append(y)
    return out


def axis_features(win: np.ndarray, odr: float):
    acc = win[..., 0:3]
    F, names = [], []
    for i, ax in enumerate("xyz"):
        a = acc[..., i]
        for nm, v in (("mean", a.mean(1)), ("std", a.std(1)), ("min", a.min(1)), ("max", a.max(1)),
                      ("ptp", np.ptp(a, 1)), ("energy", (a * a).mean(1))):
            F.append(v); names.append(f"ax{ax}_{nm}")
    return np.column_stack(F).astype(np.float32), names


def slow_features(win: np.ndarray, odr: float):
    """Impact-free features (orientation invariant): stillness at the end, tilt end vs start,
    fastest descent dP/dt, motion energy first vs second half, share of time near 1 g after."""
    N, W, _ = win.shape
    acc, p = win[..., 0:3], win[..., 6].astype(np.float64)
    amag = np.linalg.norm(acc, axis=-1)
    s = lambda sec: int(round(sec * odr))
    rs = _rolling_std(amag, s(0.5))
    moving = ~(rs < 0.03)                       # NaN at the start counts as moving
    # length of the continuous still period at the end of the window
    rev = moving[:, ::-1]
    first_move = np.where(rev.any(1), rev.argmax(1), W)
    still_tail_s = first_move / odr
    tilt = _angle(acc[:, :s(1.0)].mean(1), acc[:, -s(1.0):].mean(1))
    k = s(1.0)
    dpdt = (p[:, k:] - p[:, :-k]).max(1)        # Pa per second, positive = moving down
    h = W // 2
    e_pre = ((amag[:, :h] - 1) ** 2).mean(1)
    e_post = ((amag[:, h:] - 1) ** 2).mean(1)
    near1g = (np.abs(amag[:, h:] - 1) < 0.05).mean(1)
    names = ["s_still_tail_s", "s_tilt_end_deg", "s_dpdt_max", "s_energy_pre", "s_energy_post", "s_near1g_post"]
    return np.column_stack([still_tail_s, tilt, dpdt, e_pre, e_post, near1g]).astype(np.float32), names


def _gather_end_aligned(X, rec, end_idx, Wl):
    out = np.empty((len(rec), Wl, X[0].shape[1]), np.float32)
    for j, (r, e) in enumerate(zip(rec, end_idx)):
        st = e - Wl
        if st >= 0:
            out[j] = X[r][st:e]
        else:   # pad the start with the first sample (only when t_end < Ls)
            out[j, :-st] = X[r][0]
            out[j, -st:] = X[r][:e]
    return out


def build_features(kind: str, odr: float = 60, L: float = 4, Ls: float | None = None,
                   rotate_seed: int | None = None, rebuild: bool = False) -> dict:
    """kind: 'base' (feats.features), 'axis', 'slow'. Rows match trees.feature_set(odr, L)."""
    tag = f"{kind}_odr{int(odr)}_L{L:g}" + (f"_Ls{Ls:g}" if Ls else "") + (f"_rot{rotate_seed}" if rotate_seed is not None else "")
    path = CACHE / f"feats_x_{tag}.pkl"
    if path.exists() and not rebuild:
        with open(path, "rb") as f:
            return pickle.load(f)
    d = build(odr)
    X = d["X"] if rotate_seed is None else rotate_records(d["X"], rotate_seed)
    n = np.array([len(x) for x in d["X"]])
    W = int(round(L * odr))
    Wl = int(round((Ls or L) * odr))
    func = {"base": base_features, "axis": axis_features, "slow": slow_features}[kind]
    out = {}
    for key, idx in (("F_sl", sliding_index(d["meta"], n, odr, L)),
                     ("F_an", anchored_index(d["meta"], n, odr, L, OFFSETS))):
        chunks = []
        for i in range(0, len(idx), 8000):
            rec = idx.rec.values[i:i + 8000]
            end = idx.start.values[i:i + 8000] + W
            w = _gather_end_aligned(X, rec, end, Wl)
            r = func(w, odr)
            chunks.append(r[0]); names = r[1]
        out[key] = np.vstack(chunks)
    out["names"] = names
    with open(path, "wb") as f:
        pickle.dump(out, f, protocol=4)
    return out
