"""Revision 2, task 2: false alarms inside fall records + fall-record negatives in training.

before   = results of revision 1 (summary_trees.csv): old counting, ADL-only negatives
recount  = old training (ADL-only negatives), new counting (thresholds re-chosen under the new rule)
retrain  = new training (+ fall-record windows without the impact as negatives), new counting
"""
from __future__ import annotations

import pandas as pd

from ..eval import events as ev
from ..eval.common import TAB
from ..models import trees

SENSORS = ("A", "A+B", "A+G+B")


def main():
    ev.COUNT_FALL_FA = True
    res = []
    for sensors in SENSORS:
        res.append(trees.run(sensors, 60, 4, models=("M1lgbm",), tag="r2recount", neg_from_falls=False))
        res.append(trees.run(sensors, 60, 4, models=("M1lgbm",), tag="r2", neg_from_falls=True))
    s = trees.summary(pd.concat(res))
    old = pd.read_csv(TAB / "summary_trees.csv")
    old = old[(old.model == "M1lgbm") & old.sensors.isin(SENSORS)].assign(tag="before")
    out = pd.concat([old, s], ignore_index=True)
    out.to_csv(TAB / "r2_task2_fall_fa.csv", index=False)
    print(out[out.rule.isin(["sens95", "sens98", "sens99"])][
        ["tag", "sensors", "rule", "sens", "fa_per_h", "n_fa", "hours"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
