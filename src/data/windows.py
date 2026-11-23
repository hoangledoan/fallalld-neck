"""Window indexing and gathering.

A window is (rec, start) on the record's sample grid; its decision time is t_end = (start + W) / odr.
- sliding windows: every record, step 0.5 s (used for negatives in training and for all evaluation)
- anchored windows: fall records only, impact placed at L/3 from the window start, plus offsets
  (used as positives in training; offset 0 for window-level test metrics)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ANCHOR_FRAC = 1.0 / 3.0   # impact position inside a positive window


def sliding_index(meta: pd.DataFrame, n_samples: np.ndarray, odr: float, L: float, step: float = 0.5):
    W = int(round(L * odr))
    s = int(round(step * odr))
    rec, start = [], []
    for i, n in enumerate(n_samples):
        st = np.arange(0, n - W + 1, s)
        rec.append(np.full(len(st), i))
        start.append(st)
    rec, start = np.concatenate(rec), np.concatenate(start)
    return pd.DataFrame(dict(rec=rec, start=start, t_end=(start + W) / odr))


def anchored_index(meta: pd.DataFrame, n_samples: np.ndarray, odr: float, L: float, offsets) -> pd.DataFrame:
    W = int(round(L * odr))
    rows = []
    for i in np.where(meta.label.values == "FALL")[0]:
        for off in offsets:
            st = int(round((meta.t_impact.values[i] - ANCHOR_FRAC * L + off) * odr))
            st = int(np.clip(st, 0, n_samples[i] - W))
            rows.append((i, st, (st + W) / odr, off))
    return pd.DataFrame(rows, columns=["rec", "start", "t_end", "offset"])


def gather(X: list, rec: np.ndarray, start: np.ndarray, W: int) -> np.ndarray:
    out = np.empty((len(rec), W, X[0].shape[1]), dtype=np.float32)
    for j, (r, s) in enumerate(zip(rec, start)):
        out[j] = X[r][s:s + W]
    return out


SENSORS = {"A": ("A",), "A+B": ("A", "B"), "A+G": ("A", "G"), "A+G+B": ("A", "G", "B")}


def nn_channels(win: np.ndarray, sensors: str) -> np.ndarray:
    """Model input channels with fixed physical scaling (no data-fitted normalisation).
    A: ax, ay, az [/4 g], |a| [/4 g];  G: gx, gy, gz [/500 dps], |w| [/500 dps];
    B: relative pressure p - median(first 0.5 s of window) [/20 Pa]."""
    parts = SENSORS[sensors]
    acc, gyr, p = win[..., 0:3], win[..., 3:6], win[..., 6]
    C = 4 + 4 * ("G" in parts) + ("B" in parts)
    out = np.empty(win.shape[:2] + (C,), np.float32)
    out[..., 0:3] = acc / 4.0
    out[..., 3] = np.sqrt((acc * acc).sum(-1)) / 4.0
    c = 4
    if "G" in parts:
        out[..., 4:7] = gyr / 500.0
        out[..., 7] = np.sqrt((gyr * gyr).sum(-1)) / 500.0
        c = 8
    if "B" in parts:
        n0 = max(1, win.shape[1] // 8)
        out[..., c] = (p - np.median(p[:, :n0], axis=1, keepdims=True)) / 20.0
    return out
