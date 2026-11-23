#!/bin/bash
# Revision-2 job queue: wait for task 2, then tuning (2 procs) + tasks 4 and 6 (1 proc), 1 LightGBM thread each.
cd /storage/user/lho/lho/test/fall_detection/fallalld_neck
PY=~/miniconda3/envs/fallalld/bin/python
while pgrep -f "src.experiments.t2_fall_fa" >/dev/null; do sleep 10; done
echo "task2 finished $(date)"
$PY -u -m src.experiments.t5_strata r2_AB_60_4 M1lgbm r2_strata_fixed.csv > results/log_r2_t5.txt 2>&1
export LGBM_THREADS=1
$PY -u -m src.experiments.t3_tune --folds 1,2,3,4,5,7,8 > results/log_r2_tune_a.txt 2>&1 &
$PY -u -m src.experiments.t3_tune --folds 9,10,11,12,13,14,15 > results/log_r2_tune_b.txt 2>&1 &
( $PY -u -m src.experiments.t4_h2 > results/log_r2_t4.txt 2>&1; $PY -u -m src.experiments.t6_slow > results/log_r2_t6.txt 2>&1 ) &
wait
echo "queue done $(date)"
