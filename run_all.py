"""Run the whole pipeline: audit -> preprocessing -> M0/M1 -> M2/M3 -> tables and figures.

    python run_all.py            # full run (settings in configs/experiment.yaml)
    python run_all.py --quick    # 2 LOSO folds, 3 epochs: smoke test of every stage
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", default="audit,trees,nn,report")
    ap.add_argument("--config", default=str(ROOT / "configs" / "experiment.yaml"))
    ap.add_argument("--tag", default="", help="name prefix for result files")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    stages = a.stages.split(",")
    tag = "quick" if a.quick else a.tag
    t0 = time.time()

    from src.data.load import load_neck
    load_neck()
    if "audit" in stages:
        from src.data import audit
        audit.main()

    from src.models import trees
    from src.eval.common import TAB
    if "trees" in stages:
        res = []
        for odr in cfg["trees"]["odr"]:
            for L in cfg["trees"]["window_s"]:
                for sensors in cfg["trees"]["sensors"]:
                    res.append(trees.run(sensors, odr, L, models=tuple(cfg["trees"]["models"]),
                                         tag=tag or "trees", quick=a.quick))
        res = pd.concat(res)
        trees.summary(res).to_csv(TAB / f"summary_{tag or 'trees'}.csv", index=False)

    if "nn" in stages:
        from src.models import cnn
        res = []
        for odr in cfg["nn"]["odr"]:
            for L in cfg["nn"]["window_s"]:
                data = cnn.Data(odr, L)
                for sensors in cfg["nn"]["sensors"]:
                    for kind in cfg["nn"]["models"]:
                        for seed in cfg["nn"]["seeds"][: 1 if a.quick else None]:
                            res.append(cnn.run(kind, sensors, odr, L, seed=seed, tag=tag or "nn",
                                               quick=a.quick, data=data))
        res = pd.concat(res)
        trees.summary(res).to_csv(TAB / f"summary_{tag or 'nn'}.csv", index=False)

    if "report" in stages and not a.quick:
        from src.eval import report
        report.main()
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
