"""Preprocess FallAllD neck recordings: physical units, resampling, pressure filtering.

Per recording output (at the target sample rate `odr`):
    X[:, 0:3] acc [g]   (anti-aliased and resampled)
    X[:, 3:6] gyr [dps] (same)
    X[:, 6]   pressure [Pa], causal median (0.5 s) + causal 1 Hz low-pass, linearly
              interpolated from 10 Hz onto the IMU time grid
Meta: SubjectID, ActivityID, TrialNo, label, recovery, t_impact (falls; seconds).
"""
from __future__ import annotations

import pickle
from fractions import Fraction

import numpy as np
import pandas as pd
from scipy import signal

from .load import ROOT, load_neck, to_physical, FS_IMU, FS_BAR

ACT_CSV = ROOT / "configs" / "activities.csv"
CACHE = ROOT / "cache"


def _resample(x: np.ndarray, fs_out: float) -> np.ndarray:
    if fs_out == FS_IMU:
        return x.copy()
    fr = Fraction(fs_out / FS_IMU).limit_denominator(1000)
    # resample_poly applies a Kaiser-windowed anti-aliasing FIR before decimation
    return signal.resample_poly(x, fr.numerator, fr.denominator, axis=0)


def _pressure(pres: np.ndarray, n_out: int, fs_out: float) -> np.ndarray:
    """Causal spike-robust filter: trailing median of 5 samples (0.5 s), then 1 Hz Butterworth."""
    p = pres.astype(np.float64)
    med = np.array([np.median(p[max(0, i - 4):i + 1]) for i in range(len(p))])
    b, a = signal.butter(2, 1.0, fs=FS_BAR)
    zi = signal.lfilter_zi(b, a) * med[0]
    filt, _ = signal.lfilter(b, a, med, zi=zi)
    t_b = np.arange(len(p)) / FS_BAR
    t_o = np.arange(n_out) / fs_out
    return np.interp(t_o, t_b, filt)


def impact_time(acc_g_238: np.ndarray, lo: float = 8.0, hi: float = 12.0) -> float:
    """Impact = max |a| (native 238 Hz) inside [lo, hi] s; recordings are centred at ~10 s."""
    amag = np.linalg.norm(acc_g_238, axis=1)
    i0, i1 = int(lo * FS_IMU), int(hi * FS_IMU)
    return (i0 + int(np.argmax(amag[i0:i1]))) / FS_IMU


def build(odr: float = 60, rebuild: bool = False) -> dict:
    path = CACHE / f"prep_odr{int(odr)}.pkl"
    if path.exists() and not rebuild:
        with open(path, "rb") as f:
            return pickle.load(f)
    acts = pd.read_csv(ACT_CSV).set_index("ActivityID")
    recs = load_neck()
    X, meta = [], []
    for r in recs:
        ph = to_physical(r)
        acc = _resample(ph["acc"], odr)
        gyr = _resample(ph["gyr"], odr)
        p = _pressure(ph["pres"], len(acc), odr)
        X.append(np.column_stack([acc, gyr, p]).astype(np.float32))
        lab = acts.loc[r["ActivityID"], "label"]
        meta.append(dict(SubjectID=r["SubjectID"], ActivityID=r["ActivityID"], TrialNo=r["TrialNo"],
                         label=lab, recovery=acts.loc[r["ActivityID"], "recovery"],
                         t_impact=impact_time(ph["acc"]) if lab == "FALL" else np.nan,
                         dur=len(acc) / odr))
    out = dict(X=X, meta=pd.DataFrame(meta), odr=odr)
    with open(path, "wb") as f:
        pickle.dump(out, f, protocol=4)
    return out


if __name__ == "__main__":
    import sys
    for odr in [float(a) for a in sys.argv[1:]] or [60.0]:
        d = build(odr, rebuild=True)
        print(odr, len(d["X"]), d["X"][0].shape, d["meta"].label.value_counts().to_dict())
