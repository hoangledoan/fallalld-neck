"""Revision 2, task 4 (H2): orientation-invariant vs raw-axis features, and robustness to a random
rotation of the test data (one random 3D rotation per test record = pendant flipped).

Variants (M1 LightGBM, A+B, 60 Hz, 4 s, revision-2 protocol):
  inv          current orientation-invariant features (20)
  axis         raw per-axis acceleration statistics (18) + the 4 pressure features
  axis_rotaug  axis, plus one randomly rotated copy of every training window (rotation only in training)
  inv_axis     both sets (38)
Each variant is tested on the original test data and on rotated test data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..eval import events as ev
from ..eval.common import TAB
from ..features.extra import build_features
from ..features.feats import select
from ..models import trees
from .build_feats import TEST_ROT_SEED, TRAIN_ROT_SEED


def main():
    ev.COUNT_FALL_FA = True
    fs = trees.feature_set(60, 4)
    pcols = [i for i, g in enumerate(fs["grp"]) if g == "B"]
    icols = select(fs["names"], fs["grp"], "A+B")
    base_rot = build_features("base", rotate_seed=TEST_ROT_SEED)
    ax, ax_rot, ax_aug = (build_features("axis"), build_features("axis", rotate_seed=TEST_ROT_SEED),
                          build_features("axis", rotate_seed=TRAIN_ROT_SEED))
    P = {k: fs[k][:, pcols] for k in ("F_sl", "F_an")}
    I = {k: fs[k][:, icols] for k in ("F_sl", "F_an")}
    Irot = {k: base_rot[k][:, icols] for k in ("F_sl", "F_an")}
    views = {
        "inv": (I, Irot, None),
        "axis": ({k: np.hstack([ax[k], P[k]]) for k in P}, {k: np.hstack([ax_rot[k], P[k]]) for k in P}, None),
        "axis_rotaug": ({k: np.hstack([ax[k], P[k]]) for k in P}, {k: np.hstack([ax_rot[k], P[k]]) for k in P},
                        {k: np.hstack([ax_aug[k], P[k]]) for k in P}),
        "inv_axis": ({k: np.hstack([I[k], ax[k]]) for k in P}, {k: np.hstack([Irot[k], ax_rot[k]]) for k in P}, None),
    }
    res = []
    for name, (tr, rot, aug) in views.items():
        for test in ("orig", "rot"):
            te = tr if test == "orig" else rot
            fv = dict(F_sl=tr["F_sl"], F_an=tr["F_an"], cols=list(range(tr["F_sl"].shape[1])),
                      F_sl_test=te["F_sl"], F_an_test=te["F_an"])
            if aug is not None:
                fv.update(F_sl_aug=aug["F_sl"], F_an_aug=aug["F_an"])
            r = trees.run("A+B", 60, 4, models=("M1lgbm",), tag="r2h2", fv=fv, variant=f"{name}_{test}")
            res.append(r.assign(features=name, test=test, n_features=tr["F_sl"].shape[1]))
    res = pd.concat(res)
    s = trees.summary(res)
    s.to_csv(TAB / "r2_h2_summary.csv", index=False)
    print(s[s.rule.isin(["sens98", "sens99"])][["variant", "rule", "sens", "fa_per_h", "fah_lo", "fah_hi", "n_fa", "w_prauc"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
