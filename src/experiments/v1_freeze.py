"""Freeze model v1: M1 LightGBM, A+B, 20 invariant features, 60 Hz, 4 s window, 0.5 s step.

Fixed hyper-parameters (not re-tuned): 150 trees x 7 leaves, lr 0.1, min_child_samples 20,
no class weight (subsample / colsample 0.8 as in every earlier M1 run). Revision-2 protocol.

1. LOSO (14 subjects) for A+B (v1) and A (fallback without barometer), same settings;
   fold models + thresholds cached in cache/v1_folds_{AB,A}.pkl for the robustness tests.
2. Final models on all 14 subjects; thresholds (98 % / 99 % recall) on out-of-fold predictions of
   GroupKFold(4) over the 14 subjects. Saved to models/v1/ (A+B) and models/v1/fallback_A/ (A).

    python -m src.experiments.v1_freeze
"""
from __future__ import annotations

import json
import pickle
import platform
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
import scipy
import sklearn

from ..data.load import ROOT, ACC_G_PER_LSB, GYR_DPS_PER_LSB, FS_IMU, FS_BAR
from ..eval import events as ev
from ..eval.common import inner_groupkfold, SEED, RAW, TAB
from ..features.feats import select
from ..models import trees
from .r2_tables import paired, _subj

V1 = dict(n_estimators=150, num_leaves=7, learning_rate=0.1, min_child_samples=20, class_weight=False)
ODR, L, STEP = 60, 4, 0.5
TARGETS = (0.98, 0.99)
MODEL_DIR = ROOT / "models" / "v1"
CACHE = ROOT / "cache"


def loso(sensors: str) -> pd.DataFrame:
    keep = {}
    res = trees.run(sensors, ODR, L, models=("M1lgbm",), tag="v1", params=V1, keep=keep)
    folds = {s: v for (_, s), v in keep.items()}
    with open(CACHE / f"v1_folds_{sensors.replace('+', '')}.pkl", "wb") as f:
        pickle.dump(folds, f, protocol=4)
    return res


def final(sensors: str, out: "Path") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    fs = trees.feature_set(ODR, L)
    meta = fs["meta"]
    cols = select(fs["names"], fs["grp"], sensors)
    subs = np.sort(meta.SubjectID.unique())
    sub_sl = meta.SubjectID.values[fs["sl"].rec.values]
    # out-of-fold predictions over all 14 subjects -> thresholds
    oof = []
    for itr, iva in inner_groupkfold(subs):
        pos, neg = trees._train_rows(fs, itr, True)
        X, y = trees._xy(fs, [], pos, neg, cols)
        m = trees._fit("lgbm", X, y, SEED, V1)
        va = np.isin(sub_sl, iva)
        oof.append(fs["sl"][va][["rec", "t_end"]].assign(prob=m.predict_proba(fs["F_sl"][va][:, cols])[:, 1]))
    oof = pd.concat(oof)
    grid = ev.threshold_grid(oof.prob.values)
    pr = ev.per_record(oof, meta, grid)
    sens, fah = ev.summarise(pr)
    thr = {}
    for q in TARGETS:
        t = ev.pick_threshold(pr, grid, q)
        i = int(np.searchsorted(grid, t))
        thr[f"recall{int(q * 100)}"] = dict(threshold=float(t), oof_recall=float(sens[i]), oof_fa_per_h=float(fah[i]),
                                            oof_falls=int(pr["is_fall"].sum()), oof_hours=float(pr["hours"].sum()))
    # final model on every subject
    pos, neg = trees._train_rows(fs, subs, True)
    X, y = trees._xy(fs, [], pos, neg, cols)
    m = trees._fit("lgbm", X, y, SEED, V1)
    m.booster_.save_model(str(out / "model.txt"))
    # check: the saved text model reproduces the in-memory model
    b = lgb.Booster(model_file=str(out / "model.txt"))
    Xs = fs["F_sl"][:, cols]
    diff = float(np.abs(b.predict(Xs) - m.predict_proba(Xs)[:, 1]).max())
    assert diff < 1e-9, diff
    feats = [dict(index=j, name=fs["names"][c], group=fs["grp"][c], source_column_in_feats_features=int(c))
             for j, c in enumerate(cols)]
    json.dump(dict(sensors=sensors, n_features=len(cols), features=feats,
                   note="column order of the model input = order of this list; computed by "
                        "src/features/feats.py:features() on a (N, 240, 7) window [ax ay az gx gy gz p]"),
              open(out / "features.json", "w"), indent=2)
    json.dump(dict(
        raw_units=dict(acc_g_per_lsb=ACC_G_PER_LSB, gyr_dps_per_lsb=GYR_DPS_PER_LSB, pressure="hPa x 100 -> Pa",
                       fs_imu_hz=FS_IMU, fs_baro_hz=FS_BAR),
        imu=dict(resample="scipy.signal.resample_poly (Kaiser anti-aliasing FIR) 238 Hz -> 60 Hz", odr_hz=ODR),
        pressure=dict(steps=["trailing median of 5 samples (0.5 s) at 10 Hz",
                             "2nd-order Butterworth low-pass 1 Hz (causal lfilter, initial state = first value)",
                             "linear interpolation onto the 60 Hz IMU time grid"]),
        window=dict(length_s=L, samples=int(L * ODR), step_s=STEP, decision_time="window end"),
        alerts=dict(merge_s=ev.MERGE_S, note="alerts less than 10 s apart = one event (used in evaluation)"),
        code=dict(preprocess="src/data/preprocess.py", features="src/features/feats.py"),
    ), open(out / "preprocessing.json", "w"), indent=2)
    json.dump(dict(rule="alert when model probability >= threshold",
                   chosen_on="out-of-fold predictions, GroupKFold(4) by subject over all 14 subjects", **thr),
              open(out / "thresholds.json", "w"), indent=2)
    json.dump(dict(model="LightGBM LGBMClassifier", params=dict(**V1, subsample=0.8, subsample_freq=1,
                   colsample_bytree=0.8, random_state=SEED), n_train_pos=int(y.sum()), n_train_neg=int((y == 0).sum()),
                   n_subjects=int(len(subs)), max_abs_diff_saved_vs_memory=diff,
                   versions=dict(python=sys.version.split()[0], platform=platform.platform(), lightgbm=lgb.__version__,
                                 numpy=np.__version__, scipy=scipy.__version__, pandas=pd.__version__,
                                 scikit_learn=sklearn.__version__)),
              open(out / "model_info.json", "w"), indent=2)
    return thr


def errors():
    """Missed falls and false alarms by ActivityID for v1 A+B at the 98 % / 99 % targets."""
    from ..data.preprocess import build
    from ..eval.report import per_activity
    meta = build(ODR)["meta"]
    win = pd.read_csv(RAW / "win_v1_AB_60_4.csv.gz"); subj = pd.read_csv(RAW / "subj_v1_AB_60_4.csv")
    out = []
    for rule in ("sens98", "sens99"):
        a, r = per_activity(win, subj, meta, "M1lgbm", rule)
        a = a[(a.missed > 0) | (a.n_fa > 0)].reset_index()
        out.append(a.assign(rule=rule))
        print(rule, "FA by subject:", r.groupby("SubjectID").fa.sum().to_dict())
    out = pd.concat(out)
    out.to_csv(TAB / "v1_errors_AB.csv", index=False)
    print(out.to_string(index=False))


def main():
    ev.COUNT_FALL_FA = True
    res = pd.concat([loso("A+B"), loso("A")])
    s = trees.summary(res)
    s.to_csv(TAB / "v1_summary.csv", index=False)
    rows = []
    for rule in ("sens95", "sens98", "sens99"):
        rows.append(paired(_subj("v1_AB_60_4", rule), _subj("r2_AB_60_4", rule), "v1 A+B (150x7)", "r2 A+B (300x15)", rule))
        rows.append(paired(_subj("v1_A_60_4", rule), _subj("r2_A_60_4", rule), "v1 A (150x7)", "r2 A (300x15)", rule))
        rows.append(paired(_subj("v1_AB_60_4", rule), _subj("v1_A_60_4", rule), "v1 A+B", "v1 A", rule))
    p = pd.DataFrame(rows)
    p.to_csv(TAB / "v1_paired.csv", index=False)
    print(s[["sensors", "rule", "sens", "sens_lo", "sens_hi", "fa_per_h", "fah_lo", "fah_hi", "n_fa"]].round(3).to_string(index=False))
    print(p.round(4).to_string(index=False))
    thr = {"A+B": final("A+B", MODEL_DIR), "A": final("A", MODEL_DIR / "fallback_A")}
    pd.DataFrame([dict(sensors=k, target=t, **v) for k, d in thr.items() for t, v in d.items()]).to_csv(
        TAB / "v1_final_thresholds.csv", index=False)
    print(json.dumps(thr, indent=1))
    errors()


if __name__ == "__main__":
    main()
