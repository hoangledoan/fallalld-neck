# FallAllD neck – fall detection baseline

Fall detection on the **neck-worn** logger of FallAllD (14 subjects, 2 292 recordings of 20 s).
Leave-one-subject-out (LOSO) evaluation, event-level metrics (recall and false alarms per hour of ADL).
Report (Vietnamese): `REPORT.md`. Data checks: `DATA_AUDIT.md`. Literature: `LITERATURE.md`. Decisions: `LOG.md`.

## Install

```bash
conda create -n fallalld python=3.11 -y
~/miniconda3/envs/fallalld/bin/pip install -r requirements.txt
```

Raw data: `../FallAllD__zip.zip` (read-only). Neck files (D1) are extracted to `cache/FallAllD/` on first run.

## Run

```bash
PY=~/miniconda3/envs/fallalld/bin/python
$PY run_all.py --quick                       # smoke test: 2 LOSO folds, 3 CNN epochs (~2 min)
$PY run_all.py --stages audit,trees,report   # data audit + M0/M1 + tables/figures (~10 min)
$PY run_all.py --stages trees --config configs/q2_rate_window.yaml --tag q2   # Q2 sweep
$PY -m src.eval.random_split                 # H5: random split vs LOSO
CUDA_VISIBLE_DEVICES="" $PY run_all.py --stages nn   # CNN (M2), ~30 min per sensor set on CPU
```

On a shared 4-core machine use LightGBM with 2 threads (set in `src/models/trees.py`); 4 threads was ~40x slower.
CNN folds are saved in `results/raw/folds/`; an interrupted run resumes from the last finished fold.

## Revision 2 experiments (model only)

```bash
PY=~/miniconda3/envs/fallalld/bin/python
$PY -m src.experiments.t1_clipping                       # raw int16 clipping check
$PY -m src.experiments.t2_fall_fa                        # fall-record false alarms + fall-record negatives
$PY -m src.experiments.build_feats                       # axis / rotated / slow feature caches
LGBM_THREADS=1 $PY -m src.experiments.t3_tune --folds 1,2,3,4,5,7,8 &   # nested CV, split over 2 processes
LGBM_THREADS=1 $PY -m src.experiments.t3_tune --folds 9,10,11,12,13,14,15
$PY -m src.experiments.t3_tune --merge
$PY -m src.experiments.t4_h2                             # H2: invariant vs raw-axis features, rotated test
$PY -m src.experiments.t5_strata r2_AB_60_4 M1lgbm r2_strata_fixed.csv
$PY -m src.experiments.t6_slow                           # impact-free features + long-lie detector (OR)
$PY -m src.experiments.r2_tables                         # paired tests
```

Since revision 2, `src/eval/events.py` counts false alarms inside fall records (`COUNT_FALL_FA = True`)
and training uses fall-record windows without the impact as negatives (`neg_from_falls=True`).

## Layout

```
src/data/      load.py (raw -> cache), audit.py, preprocess.py (resample, pressure filter), windows.py
src/features/  feats.py (orientation-invariant statistics + fall-phase features)
src/models/    trees.py (M0 rule, M1 LightGBM / decision tree), cnn.py (M2 CNN, M3 variants defined)
src/eval/      events.py (streaming event scoring), common.py (folds, CI), report.py, nn_rescore.py, random_split.py
configs/       activities.csv (ActivityID -> label), experiment.yaml, q2_rate_window.yaml
results/       raw/ (per-window scores, per-subject counts), tables/, figures/
models/        saved CNN models per fold
```

## Evaluation rules

- LOSO over 14 subjects; `assert` checks no subject is in both train and test (outer and inner splits).
- Thresholds chosen on training subjects only: LightGBM on out-of-fold predictions of an inner 4-fold GroupKFold,
  CNN on 3 inner validation subjects.
- Event scoring: sliding 4 s windows every 0.5 s; alerts < 10 s apart merge into one event; a fall counts as detected
  if an alert occurs within [-1 s, +5 s] of the impact; every event in an ADL/near-fall record is a false alarm.

## Chốt v1

```bash
PY=~/miniconda3/envs/fallalld/bin/python
LGBM_THREADS=2 $PY -m src.experiments.v1_freeze          # LOSO v1 + model A, model cuối -> models/v1/
LGBM_THREADS=2 $PY -m src.experiments.v1_noise           # nhiễu áp suất, 25 Hz, barometer hằng số/NaN
LGBM_THREADS=2 $PY -m src.experiments.v1_noise --extra   # các mức thêm (*) để tìm điểm A+B mất lợi thế so với A
```
Model, đặc trưng, ngưỡng và model card: `models/v1/`. Kết quả: `REPORT.md` mục 12.
