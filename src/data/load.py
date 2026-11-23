"""Read FallAllD raw .dat files (read-only) and build a cached neck-only dataset.

File name pattern (verified against FallAllD_to_PYTHON_Structure.py):
    S{subject:02d}_D{device}_A{activity:03d}_T{trial:02d}_{A|G|M|B}.dat
    device: 1 = Neck, 2 = Wrist, 3 = Waist
    A/G/M: int16 raw counts, 3 columns (x, y, z)
    B:     2 columns: pressure [hPa], temperature [degC]
"""
from __future__ import annotations

import os
import pickle
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_ZIP = ROOT.parent / "FallAllD__zip.zip"
RAW_DIR = ROOT / "cache" / "FallAllD"          # extracted copy, never modified
CACHE_FILE = ROOT / "cache" / "neck_raw.pkl"

DEVICE_CODE = {1: "Neck", 2: "Wrist", 3: "Waist"}
NAME_RE = re.compile(r"S(\d{2})_D(\d)_A(\d{3})_T(\d{2})_A\.dat$")

# LSM9DS1 sensitivities (datasheet DocID025715, table 3)
ACC_G_PER_LSB = 0.244e-3      # +-8 g
GYR_DPS_PER_LSB = 70e-3       # +-2000 dps
MAG_GAUSS_PER_LSB = 0.14e-3   # +-4 gauss (only used for audit)
FS_IMU = 238.0
FS_MAG = 80.0
FS_BAR = 10.0


def ensure_extracted(devices=("D1",)) -> None:
    """Extract the requested devices from the read-only zip into cache/."""
    if RAW_DIR.exists() and any(RAW_DIR.glob("S*_D1_*_A.dat")):
        return
    import zipfile
    with zipfile.ZipFile(RAW_ZIP) as z:
        for n in z.namelist():
            if any(f"_{d}_" in n for d in devices):
                z.extract(n, RAW_DIR.parent)


def _read(path: Path, dtype) -> np.ndarray:
    return pd.read_csv(path, header=None).to_numpy(dtype=dtype)


def _load_one(a_path: str) -> dict:
    p = Path(a_path)
    m = NAME_RE.search(p.name)
    subj, dev, act, trial = (int(g) for g in m.groups())
    base = str(p)[:-5]
    acc = _read(Path(base + "A.dat"), np.int16)
    gyr = _read(Path(base + "G.dat"), np.int16)
    mag = _read(Path(base + "M.dat"), np.int16)
    bar = _read(Path(base + "B.dat"), np.float64)
    return dict(SubjectID=subj, Device=DEVICE_CODE[dev], ActivityID=act, TrialNo=trial,
                file=p.name, acc_raw=acc, gyr_raw=gyr, mag_raw=mag, bar_raw=bar)


def load_neck(rebuild: bool = False, workers: int = 4) -> list[dict]:
    """Return list of neck recordings with raw counts. Cached in cache/neck_raw.pkl."""
    if CACHE_FILE.exists() and not rebuild:
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    ensure_extracted()
    files = sorted(str(p) for p in RAW_DIR.glob("S*_D1_*_A.dat"))
    with ProcessPoolExecutor(workers) as ex:
        recs = list(ex.map(_load_one, files, chunksize=32))
    recs = [r for r in recs if r["Device"] == "Neck"]
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(recs, f, protocol=4)
    return recs


def to_physical(rec: dict) -> dict:
    """Convert raw counts to physical units: acc [g], gyr [dps], pressure [Pa]."""
    return dict(
        acc=rec["acc_raw"].astype(np.float32) * ACC_G_PER_LSB,
        gyr=rec["gyr_raw"].astype(np.float32) * GYR_DPS_PER_LSB,
        pres=rec["bar_raw"][:, 0] * 100.0,   # hPa -> Pa
        temp=rec["bar_raw"][:, 1],
    )


if __name__ == "__main__":
    recs = load_neck(rebuild=True)
    print(len(recs), "neck recordings cached to", CACHE_FILE)
