"""Revision 2, task 1: clipping check on RAW int16 values per axis, neck device (D1).

Conversion factors in use (src/data/load.py): acc 0.244 mg/LSB (+-8 g), gyro 70 mdps/LSB (+-2000 dps).
Source: LSM9DS1 datasheet DocID025715 Rev 2, Table 3 (linear acceleration / angular rate sensitivity),
and the official FallAllD script Plot_FallAllD_Record.m (IEEE DataPort), which uses the same factors.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..data.load import load_neck, ACC_G_PER_LSB, GYR_DPS_PER_LSB
from ..eval.common import TAB, FIG

I16_MAX, I16_MIN = 32767, -32768


def main():
    recs = load_neck()
    acts = pd.read_csv(TAB.parents[1] / "configs" / "activities.csv").set_index("ActivityID")
    rows, per_rec = [], []
    for sensor, key, lsb, unit in (("acc", "acc_raw", ACC_G_PER_LSB, "g"), ("gyr", "gyr_raw", GYR_DPS_PER_LSB, "dps")):
        allv = np.concatenate([r[key] for r in recs]).astype(np.int32)   # (N, 3)
        for ax, name in enumerate("xyz"):
            v = allv[:, ax]
            q99 = np.quantile(np.abs(v), 0.99)
            rows.append(dict(sensor=sensor, axis=name, n_samples=len(v),
                             n_eq_max=int((v == I16_MAX).sum()), n_eq_min=int((v == I16_MIN).sum()),
                             n_abs_ge_32000=int((np.abs(v) >= 32000).sum()),
                             raw_min=int(v.min()), raw_max=int(v.max()),
                             phys_min=v.min() * lsb, phys_max=v.max() * lsb, unit=unit,
                             lsb=lsb, abs_q99_raw=float(q99), abs_q99_phys=float(q99 * lsb)))
        # histogram of the top 1 % |raw| values (all axes pooled) per sensor
        a = np.abs(allv).ravel()
        top = a[a >= np.quantile(a, 0.99)]
        bins = np.linspace(top.min(), 32768, 60)
        h, e = np.histogram(top, bins)
        pd.DataFrame(dict(bin_lo=e[:-1], bin_hi=e[1:], count=h)).to_csv(TAB / f"r2_clip_hist_top1pct_{sensor}.csv", index=False)
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.hist(top, bins=bins, log=True)
        ax.axvline(32767, color="r", ls="--", lw=.8, label="int16 limit")
        ax.set_xlabel(f"|raw {sensor}| [LSB]  (x {lsb:g} {unit}/LSB)"); ax.set_ylabel("samples (log)")
        ax.set_title(f"Neck device, top 1 % of |raw {sensor}| values, all axes", fontsize=9); ax.legend()
        fig.tight_layout(); fig.savefig(FIG / f"r2_clip_hist_{sensor}.png", dpi=110)
    for r in recs:
        acc = r["acc_raw"].astype(np.int32); gyr = r["gyr_raw"].astype(np.int32)
        per_rec.append(dict(SubjectID=r["SubjectID"], ActivityID=r["ActivityID"], TrialNo=r["TrialNo"],
                            label=acts.loc[r["ActivityID"], "label"],
                            acc_at_limit=bool(((acc == I16_MAX) | (acc == I16_MIN)).any()),
                            gyr_at_limit=bool(((gyr == I16_MAX) | (gyr == I16_MIN)).any()),
                            rest_raw_norm=float(np.median(np.linalg.norm(acc, axis=1)))))
    pr = pd.DataFrame(per_rec)
    by = pr.groupby("label").agg(n=("TrialNo", "size"), acc_clipped_recs=("acc_at_limit", "sum"),
                                 acc_clipped_pct=("acc_at_limit", "mean"), gyr_clipped_recs=("gyr_at_limit", "sum"),
                                 gyr_clipped_pct=("gyr_at_limit", "mean"), median_norm_raw=("rest_raw_norm", "median"))
    by["acc_clipped_pct"] *= 100; by["gyr_clipped_pct"] *= 100
    # 1 g at 0.244 mg/LSB = 4098 LSB; at +-16 g (0.732 mg/LSB) it would be 1366 LSB
    by["implied_g_at_0.244mg"] = by.median_norm_raw * ACC_G_PER_LSB
    pd.DataFrame(rows).to_csv(TAB / "r2_clip_axes.csv", index=False)
    by.to_csv(TAB / "r2_clip_by_label.csv")
    print(pd.DataFrame(rows).to_string(index=False)); print(by.round(3).to_string())


if __name__ == "__main__":
    main()
