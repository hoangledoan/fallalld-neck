"""Data audit for FallAllD neck recordings -> results/tables/audit_*.csv + figures."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .load import ROOT, load_neck, to_physical, FS_IMU, FS_BAR, FS_MAG

TAB = ROOT / "results" / "tables"
FIG = ROOT / "results" / "figures"
ACT_CSV = ROOT / "configs" / "activities.csv"


def label_of(act_id: int, acts: pd.DataFrame | None) -> str:
    if acts is not None and act_id in acts.index:
        return acts.loc[act_id, "label"]
    return "FALL" if act_id >= 101 else "ADL"


def _delta_p(pres: np.ndarray, t_peak: float) -> float:
    """dP = median P in [t+1, t+3] s minus median P in [t-3, t-1] s (positive = moved down)."""
    t = np.arange(len(pres)) / FS_BAR
    pre = pres[(t >= t_peak - 3) & (t <= t_peak - 1)]
    post = pres[(t >= t_peak + 1) & (t <= t_peak + 3)]
    if len(pre) < 5 or len(post) < 5:
        return float("nan")
    return float(np.median(post) - np.median(pre))


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    acts = pd.read_csv(ACT_CSV).set_index("ActivityID") if ACT_CSV.exists() else None
    recs = load_neck()
    rows = []
    for r in recs:
        ph = to_physical(r)
        amag = np.linalg.norm(ph["acc"], axis=1)
        wmag = np.linalg.norm(ph["gyr"], axis=1)
        n = len(amag)
        # rest |a|: median over the quietest 1 s (lowest |w| variance)
        k = int(FS_IMU)
        seg_std = np.array([wmag[i:i + k].std() for i in range(0, n - k, k // 2)])
        i0 = int(np.argmin(seg_std)) * (k // 2)
        rows.append(dict(
            SubjectID=r["SubjectID"], ActivityID=r["ActivityID"], TrialNo=r["TrialNo"],
            label=label_of(r["ActivityID"], acts),
            n_acc=len(r["acc_raw"]), n_gyr=len(r["gyr_raw"]), n_mag=len(r["mag_raw"]),
            n_bar=len(r["bar_raw"]),
            acc_cols=r["acc_raw"].shape[1], bar_cols=r["bar_raw"].shape[1],
            dur_acc_s=len(r["acc_raw"]) / FS_IMU, dur_bar_s=len(r["bar_raw"]) / FS_BAR,
            dur_mag_s=len(r["mag_raw"]) / FS_MAG,
            nan_any=bool(np.isnan(r["bar_raw"]).any()),
            rest_amag_g=float(np.median(amag[i0:i0 + k])),
            peak_amag_g=float(amag.max()),
            peak_wmag_dps=float(wmag.max()),
            max_abs_axis_g=float(np.abs(ph["acc"]).max()),
            clip_axis=bool((np.abs(ph["acc"]) >= 7.9).any()),
            max_abs_raw_acc=int(np.abs(r["acc_raw"].astype(int)).max()),
            max_abs_axis_dps=float(np.abs(ph["gyr"]).max()),
            clip_gyr=bool((np.abs(ph["gyr"]) >= 1990).any()),
            p_med_hpa=float(np.median(ph["pres"]) / 100),
            p_min_hpa=float(ph["pres"].min() / 100), p_max_hpa=float(ph["pres"].max() / 100),
            p_range_pa=float(np.ptp(ph["pres"])),
            temp_med=float(np.median(ph["temp"])),
            # repeated identical consecutive rows: hint of dropped/held samples
            acc_dup_frac=float((np.diff(r["acc_raw"], axis=0) == 0).all(axis=1).mean()),
            peak_t_s=float(np.argmax(amag) / FS_IMU),
            dP_pa=_delta_p(ph["pres"], np.argmax(amag) / FS_IMU),
        ))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "audit_recordings.csv", index=False)

    # counts per subject x label, per activity
    df.pivot_table(index="SubjectID", columns="label", values="TrialNo", aggfunc="count",
                   fill_value=0).to_csv(TAB / "audit_counts_subject_label.csv")
    df.pivot_table(index="ActivityID", columns="SubjectID", values="TrialNo", aggfunc="count",
                   fill_value=0).to_csv(TAB / "audit_counts_activity_subject.csv")
    summ = df.groupby("label").agg(
        n=("TrialNo", "size"), subjects=("SubjectID", "nunique"),
        dur_mean=("dur_acc_s", "mean"), dur_min=("dur_acc_s", "min"), dur_max=("dur_acc_s", "max"),
        rest_g_med=("rest_amag_g", "median"), peak_g_med=("peak_amag_g", "median"),
        clip_frac=("clip_axis", "mean"), clip_gyr_frac=("clip_gyr", "mean"),
        p_med=("p_med_hpa", "median"), p_min=("p_min_hpa", "min"), p_max=("p_max_hpa", "max"),
        p_range_pa_med=("p_range_pa", "median"))
    summ.to_csv(TAB / "audit_summary_label.csv")
    act = df.groupby("ActivityID").agg(
        label=("label", "first"), n=("TrialNo", "size"), subjects=("SubjectID", "nunique"),
        peak_g_med=("peak_amag_g", "median"), clip_frac=("clip_axis", "mean"),
        p_range_pa_med=("p_range_pa", "median"))
    if acts is not None:
        act = act.join(acts[["description"]])
    act.to_csv(TAB / "audit_activity.csv")
    # meaning of "with recovery": posture at end vs start of the recording
    if acts is not None:
        rr = []
        for r in recs:
            if label_of(r["ActivityID"], acts) != "FALL":
                continue
            acc = to_physical(r)["acc"]
            k = int(2 * FS_IMU)
            g0, g1 = acc[:k].mean(0), acc[-k:].mean(0)
            ang = np.degrees(np.arccos(np.clip(g0 @ g1 / np.linalg.norm(g0) / np.linalg.norm(g1), -1, 1)))
            rr.append(dict(ActivityID=r["ActivityID"], recovery=acts.loc[r["ActivityID"], "recovery"],
                           posture_change_deg=ang,
                           last2s_amag_std=float(np.linalg.norm(acc[-k:], axis=1).std())))
        rr = pd.DataFrame(rr)
        rec_s = rr.groupby("recovery").agg(n=("ActivityID", "size"),
                                           posture_change_deg_med=("posture_change_deg", "median"),
                                           frac_posture_lt30=("posture_change_deg", lambda x: (x < 30).mean()),
                                           last2s_amag_std_med=("last2s_amag_std", "median"))
        rec_s.to_csv(TAB / "audit_recovery.csv")
        print(rec_s)
    dp = df.groupby("label").dP_pa.describe(percentiles=[.1, .25, .5, .75, .9])
    if acts is not None:
        df["pre_fall_status"] = df.ActivityID.map(acts["pre_fall_status"])
        dp_f = df[df.label == "FALL"].groupby("pre_fall_status").dP_pa.describe(percentiles=[.1, .5, .9])
        dp = pd.concat([dp, dp_f])
    dp.to_csv(TAB / "audit_delta_p.csv")
    print(dp.round(1))
    lens = df[["n_acc", "n_gyr", "n_mag", "n_bar"]].value_counts().reset_index()
    lens.to_csv(TAB / "audit_lengths.csv", index=False)
    print(summ.T)
    print(lens.head(10))

    # --- figures: 3 falls (different activities) + 3 ADLs with highest peak |a|
    falls = df[df.label == "FALL"].sort_values("peak_amag_g")
    pick_f = [falls.iloc[len(falls) // 4], falls.iloc[len(falls) // 2], falls.iloc[3 * len(falls) // 4]]
    adl = df[df.label != "FALL"]
    # confusable ADLs (data-driven): 2 activities with highest median peak |a|,
    # 1 activity with highest median pressure range (barometer confounder)
    top_adl_acts = list(adl.groupby("ActivityID").peak_amag_g.median().sort_values().index[-2:])
    top_adl_acts.append(adl.groupby("ActivityID").p_range_pa.median().sort_values().index[-1])
    pick_a = [adl[adl.ActivityID == a].sort_values("peak_amag_g").iloc[len(adl[adl.ActivityID == a]) // 2]
              for a in top_adl_acts]
    idx = {(r["SubjectID"], r["ActivityID"], r["TrialNo"]): r for r in recs}
    fig, axes = plt.subplots(6, 1, figsize=(10, 15), sharex=True)
    for ax, row in zip(axes, pick_f + pick_a):
        r = idx[(row.SubjectID, row.ActivityID, row.TrialNo)]
        ph = to_physical(r)
        t = np.arange(len(ph["acc"])) / FS_IMU
        tb = np.arange(len(ph["pres"])) / FS_BAR
        ax.plot(t, np.linalg.norm(ph["acc"], axis=1), lw=.7, label="|a| [g]")
        ax.plot(t, np.linalg.norm(ph["gyr"], axis=1) / 1000, lw=.7, label="|ω| [1000 dps]")
        ax.set_ylim(0, 9)
        ax2 = ax.twinx()
        prel = ph["pres"] - np.median(ph["pres"][:20])
        ax2.plot(tb, prel, color="0.6", lw=.6, label="ΔP raw [Pa]")
        from scipy.ndimage import median_filter
        ax2.plot(tb, median_filter(prel, 11, mode="nearest"), color="k", lw=1.2, label="ΔP median 1.1 s [Pa]")
        ax2.set_ylabel("ΔP [Pa]")
        desc = ""
        if acts is not None and row.ActivityID in acts.index:
            desc = acts.loc[row.ActivityID, "description"][:60]
        ax.set_title(f"S{row.SubjectID:02d} A{row.ActivityID:03d} T{row.TrialNo:02d} [{row.label}] {desc}",
                     fontsize=9)
        ax.legend(loc="upper left", fontsize=7)
        ax2.legend(loc="upper right", fontsize=7)
    axes[-1].set_xlabel("t [s]")
    fig.tight_layout()
    fig.savefig(FIG / "audit_examples.png", dpi=110)

    # histogram of peak |a| by label
    fig, ax = plt.subplots(figsize=(7, 4))
    for lab, g in df.groupby("label"):
        ax.hist(g.peak_amag_g, bins=60, range=(0, 14), alpha=.5, label=lab)
    ax.axvline(8, color="r", ls="--", lw=.8)
    ax.set_xlabel("peak |a| [g]"); ax.set_ylabel("recordings"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "audit_peak_hist.png", dpi=110)


if __name__ == "__main__":
    main()
