"""v1 robustness to barometer noise (test data only; training and thresholds unchanged), and the
fallback when the barometer fails.

Perturbations are applied to the RAW barometer signal (10 Hz, Pa) of every test record (ADL,
near-fall and fall records alike), then the normal pressure chain runs (trailing median 0.5 s,
1 Hz Butterworth, interpolation to 60 Hz) and the 4 pressure features are recomputed. The 16
acceleration features are untouched. Each LOSO fold uses its own v1 model and its own thresholds
(98 % / 99 % recall, chosen on the clean out-of-fold predictions of its training subjects).

  white    : Gaussian white noise, sd 0.5 / 1 / 2 / 4 Pa per raw sample
  drift    : linear drift 5 / 10 / 20 Pa per minute, sign random per record
             (drift_pos / drift_neg: same with a fixed sign; deterministic, 1 seed)
  impulse  : door-type disturbance once per 30 s (random phase, so 0 or 1 per 20 s record,
             P = 2/3): amplitude +-3 / 6 / 10 Pa (random sign), duration U(0.5, 2) s,
             shape 50/50 "pulse" (offset for the duration, then back) or "step" (linear ramp over
             the duration, then stays)
  baro25   : raw 10 Hz pressure linearly interpolated to 25 Hz, pressure chain run at 25 Hz
             (median of 13 samples = 0.52 s, 1 Hz Butterworth at fs = 25 Hz); test only, and also
             with the v1 recipe re-trained on 25 Hz features (baro25_retrain)
  const    : barometer stuck: raw pressure = its first sample for the whole record
  nan      : barometer missing: the 4 pressure features are NaN
Stochastic conditions: 5 noise seeds per level. CIs: bootstrap over subjects on the counts summed
over seeds.

    python -m src.experiments.v1_noise
"""
from __future__ import annotations

import pickle
import zlib

import numpy as np
import pandas as pd
from scipy import signal

from ..data.load import ROOT, load_neck, to_physical, FS_BAR
from ..data.preprocess import build
from ..eval import events as ev
from ..eval.common import subject_rows, bootstrap_ci, RAW, TAB, FIG, SEED
from ..features.feats import _masked
from ..models import trees
from .r2_tables import paired
from .v1_freeze import V1

ODR, L = 60, 4
W = L * ODR
RULES = ("sens98", "sens99")
SEEDS = range(5)
LEVELS = {"white": (0.5, 1, 2, 4), "drift": (5, 10, 20), "impulse": (3, 6, 10)}
# beyond the requested levels, only to locate where A+B becomes worse than model A
EXTRA = {"white": (8, 16, 32), "drift": (60, 120), "impulse": (20, 40)}
P_NAMES = ["p_dP", "p_end_minus_start", "p_slope", "p_range"]
CACHE = ROOT / "cache"


# ---------------------------------------------------------------- pressure chain
def pressure_chain(p: np.ndarray, n_out: int, fs_bar: float = FS_BAR) -> np.ndarray:
    """Same as preprocess._pressure, for any barometer rate (median length = odd ~0.5 s)."""
    p = p.astype(np.float64)
    k = int(round(0.5 * fs_bar)) | 1
    med = np.empty_like(p)
    for i in range(min(k - 1, len(p))):
        med[i] = np.median(p[:i + 1])
    if len(p) >= k:
        med[k - 1:] = np.median(np.lib.stride_tricks.sliding_window_view(p, k), axis=1)
    b, a = signal.butter(2, 1.0, fs=fs_bar)
    filt, _ = signal.lfilter(b, a, med, zi=signal.lfilter_zi(b, a) * med[0])
    return np.interp(np.arange(n_out) / ODR, np.arange(len(p)) / fs_bar, filt)


def perturb(p: np.ndarray, kind: str, level: float, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(len(p)) / FS_BAR
    if kind == "white":
        return p + rng.normal(0, level, len(p))
    if kind in ("drift", "drift_pos", "drift_neg"):
        sgn = {"drift": rng.choice([-1, 1]), "drift_pos": 1, "drift_neg": -1}[kind]
        return p + sgn * level * t / 60.0
    if kind == "impulse":
        t0 = rng.uniform(0, 30)
        shape, sgn, d = rng.choice(["pulse", "step"]), rng.choice([-1, 1]), rng.uniform(0.5, 2.0)
        if t0 >= t[-1] + 1 / FS_BAR:
            return p.copy()
        if shape == "pulse":
            return p + sgn * level * ((t >= t0) & (t < t0 + d))
        return p + sgn * level * np.clip((t - t0) / d, 0, 1)
    if kind == "const":
        return np.full_like(p, p[0])
    raise ValueError(kind)


# ---------------------------------------------------------------- pressure features
def p_features(Pw: np.ndarray, k: np.ndarray) -> np.ndarray:
    """The 4 pressure features of feats.features (identical code path), Pw (N, W), k (N,)."""
    p = Pw.astype(np.float32).astype(np.float64)
    t = np.arange(W)[None, :]
    k = k[:, None]
    s = lambda sec: int(round(sec * ODR))
    post = t >= k + s(0.5)
    post = np.where(post.any(1, keepdims=True), post, t >= W - s(0.25))
    pre_p = t < np.maximum(k - s(0.5), 1)
    n0 = max(1, s(0.5))
    tt = (np.arange(W) - (W - 1) / 2) / ODR
    F = [_masked(p, post, np.nanmedian) - _masked(p, pre_p, np.nanmedian),
         p[:, -n0:].mean(1) - p[:, :n0].mean(1),
         ((p - p.mean(1, keepdims=True)) * tt).sum(1) / (tt ** 2).sum(),
         np.ptp(p, 1)]
    return np.column_stack([np.asarray(f, np.float32) for f in F])


class Ctx:
    def __init__(self):
        self.fs = trees.feature_set(ODR, L)
        self.meta = self.fs["meta"]
        self.raw_p = [to_physical(r)["pres"] for r in load_neck()]
        X = build(ODR)["X"]
        assert len({len(x) for x in X}) == 1
        self.n = len(X[0])
        acc = np.stack([x[:, :3] for x in X])
        self.P0 = np.stack([x[:, 6] for x in X])
        self.idx = {}
        for key in ("sl", "an"):
            d = self.fs[key]
            rec, st = d.rec.values, d.start.values
            cols = st[:, None] + np.arange(W)[None, :]
            k = np.empty(len(rec), int)
            for i in range(0, len(rec), 8000):
                a = acc[rec[i:i + 8000, None], cols[i:i + 8000]]
                k[i:i + 8000] = np.linalg.norm(a, axis=-1).argmax(1)
            self.idx[key] = (rec, cols, k)
        self.names = self.fs["names"]
        self.pcol = [self.names.index(n) for n in P_NAMES]
        self.sub_sl = self.meta.SubjectID.values[self.fs["sl"].rec.values]

    def feats(self, P: np.ndarray, key: str = "sl") -> np.ndarray:
        """Full feature matrix (all 27 columns) with the pressure columns from P (records, 1200)."""
        rec, cols, k = self.idx[key]
        F = self.fs["F_" + key].copy()
        F[:, self.pcol] = p_features(P[rec[:, None], cols], k)
        return F

    def P_from(self, kind, level, seed, fs_bar=FS_BAR):
        rng = np.random.default_rng([SEED, seed, zlib.crc32(kind.encode()), int(level * 100)])
        out = np.empty_like(self.P0, dtype=np.float64)
        for r, p in enumerate(self.raw_p):
            q = p if kind == "clean" else perturb(p, kind, level, rng)
            if fs_bar != FS_BAR:
                tb = np.arange(len(q)) / FS_BAR
                q = np.interp(np.arange(int(round(len(q) / FS_BAR * fs_bar))) / fs_bar, tb, q)
            out[r] = pressure_chain(q, self.n, fs_bar)
        return out


def evaluate(ctx: Ctx, folds: dict, F: np.ndarray, info: dict) -> list:
    rows = []
    for s, f in folds.items():
        te = ctx.sub_sl == s
        prob = f["model"].predict_proba(F[te][:, f["cols"]])[:, 1]
        win = ctx.fs["sl"][te][["rec", "t_end"]].assign(prob=prob)
        thr = np.array([f["thr"][r] for r in RULES])
        pr = ev.per_record(win, ctx.meta, thr)
        for j, rule in enumerate(RULES):
            for _, r in subject_rows(pr, ctx.meta, j).iterrows():
                rows.append(dict(**info, rule=rule, fold=s, thr=thr[j], **r.to_dict()))
    return rows


def summarise(df: pd.DataFrame, keys=("cond", "level", "rule")) -> pd.DataFrame:
    out = []
    for k, g in df.groupby(list(keys), sort=False):
        per_sub = g.groupby("SubjectID")[["n_falls", "n_det", "n_fa", "hours"]].sum().reset_index()
        per_seed = g.groupby("seed")[["n_falls", "n_det", "n_fa", "hours"]].sum()
        ci = bootstrap_ci(per_sub)
        out.append(dict(zip(keys, k), n_seeds=g.seed.nunique(),
                        sens=per_sub.n_det.sum() / per_sub.n_falls.sum(),
                        fa_per_h=per_sub.n_fa.sum() / per_sub.hours.sum(), **ci,
                        sens_seed_min=(per_seed.n_det / per_seed.n_falls).min(),
                        sens_seed_max=(per_seed.n_det / per_seed.n_falls).max(),
                        fah_seed_min=(per_seed.n_fa / per_seed.hours).min(),
                        fah_seed_max=(per_seed.n_fa / per_seed.hours).max(),
                        n_fa_mean=per_seed.n_fa.mean(), missed_mean=(per_seed.n_falls - per_seed.n_det).mean()))
    return pd.DataFrame(out)


def native_noise(ctx: Ctx) -> pd.DataFrame:
    """Context: noise already present in the raw barometer (10 Hz), per label."""
    rows = []
    for r, p in enumerate(ctx.raw_p):
        hp = p - signal.medfilt(p, 11)                      # residual around a 1.1 s running median
        sd2 = np.lib.stride_tricks.sliding_window_view(p, 20).std(1)   # raw sd over 2 s
        rows.append(dict(label=ctx.meta.label.values[r], resid_sd=hp.std(), diff_sd=np.diff(p).std() / np.sqrt(2),
                         min_sd_2s=sd2.min(), n_exact_repeat=int((np.diff(p) == 0).sum())))
    d = pd.DataFrame(rows)
    return d.groupby("label").agg(n=("resid_sd", "size"), resid_sd_median=("resid_sd", "median"),
                                  diff_sd_median=("diff_sd", "median"), min_sd_2s_min=("min_sd_2s", "min"),
                                  exact_repeats_total=("n_exact_repeat", "sum")).reset_index()


def main():
    ev.COUNT_FALL_FA = True
    ctx = Ctx()
    folds = pickle.load(open(CACHE / "v1_folds_AB.pkl", "rb"))
    # 0. the chain reproduces the cached features exactly
    Pc = ctx.P_from("clean", 0, 0)
    assert np.abs(Pc.astype(np.float32) - ctx.P0).max() == 0
    F0 = ctx.feats(Pc)
    assert np.array_equal(F0[:, ctx.pcol], ctx.fs["F_sl"][:, ctx.pcol], equal_nan=True)
    rows = evaluate(ctx, folds, F0, dict(cond="clean", level=0.0, seed=0))
    ref = pd.read_csv(RAW / "subj_v1_AB_60_4.csv")
    ref = ref[ref.rule.isin(RULES)].sort_values(["rule", "SubjectID"])
    chk = pd.DataFrame(rows).sort_values(["rule", "SubjectID"])
    assert (chk[["n_det", "n_fa"]].values == ref[["n_det", "n_fa"]].values).all(), "clean replay != v1 LOSO"
    print("clean replay matches v1 LOSO", flush=True)
    # 1. noise sweeps
    for kind, levels in LEVELS.items():
        for lv in levels:
            for sd in SEEDS:
                rows += evaluate(ctx, folds, ctx.feats(ctx.P_from(kind, lv, sd)), dict(cond=kind, level=float(lv), seed=sd))
            print(kind, lv, flush=True)
    for kind in ("drift_pos", "drift_neg"):
        for lv in LEVELS["drift"]:
            rows += evaluate(ctx, folds, ctx.feats(ctx.P_from(kind, lv, 0)), dict(cond=kind, level=float(lv), seed=0))
    # 2. barometer at 25 Hz (interpolated), test only
    F25 = ctx.feats(ctx.P_from("clean", 0, 0, fs_bar=25.0))
    rows += evaluate(ctx, folds, F25, dict(cond="baro25", level=25.0, seed=0))
    # 3. failures: stuck and missing
    rows += evaluate(ctx, folds, ctx.feats(ctx.P_from("const", 0, 0)), dict(cond="const", level=0.0, seed=0))
    Fn = F0.copy(); Fn[:, ctx.pcol] = np.nan
    rows += evaluate(ctx, folds, Fn, dict(cond="nan", level=0.0, seed=0))
    df = pd.DataFrame(rows)
    # 4. 25 Hz with the v1 recipe re-trained on 25 Hz features (train and test at 25 Hz)
    P25 = ctx.P_from("clean", 0, 0, fs_bar=25.0)
    fv = dict(F_sl=ctx.feats(P25, "sl"), F_an=ctx.feats(P25, "an"))
    fv["cols"] = folds[next(iter(folds))]["cols"]
    rt = trees.run("A+B", ODR, L, models=("M1lgbm",), tag="v1baro25", params=V1, fv=fv)
    rt = rt[rt.rule.isin(RULES)].assign(cond="baro25_retrain", level=25.0, seed=0)
    df = pd.concat([df, rt[df.columns.intersection(rt.columns)]], ignore_index=True)
    # 5. model A (no barometer), from the v1 LOSO run
    a = pd.read_csv(RAW / "subj_v1_A_60_4.csv")
    a = a[a.rule.isin(RULES)].assign(cond="model_A", level=0.0, seed=0)
    df = pd.concat([df, a[df.columns.intersection(a.columns)]], ignore_index=True)
    df.to_csv(RAW / "subj_v1_noise.csv", index=False)
    finish(df, ctx)


def run_extra():
    ev.COUNT_FALL_FA = True
    ctx = Ctx()
    folds = pickle.load(open(CACHE / "v1_folds_AB.pkl", "rb"))
    df = pd.read_csv(RAW / "subj_v1_noise.csv")
    rows = []
    for kind, levels in EXTRA.items():
        for lv in levels:
            for sd in SEEDS:
                rows += evaluate(ctx, folds, ctx.feats(ctx.P_from(kind, lv, sd)), dict(cond=kind, level=float(lv), seed=sd))
            print("extra", kind, lv, flush=True)
    ex = pd.DataFrame(rows).assign(extra=True)
    df = pd.concat([df.assign(extra=False) if "extra" not in df else df[~df.extra.astype(bool)], ex], ignore_index=True)
    df.to_csv(RAW / "subj_v1_noise.csv", index=False)
    finish(df, ctx)


def finish(df: pd.DataFrame, ctx: Ctx):
    if "extra" not in df:
        df = df.assign(extra=False)
    df = df.sort_values(["cond", "level"], kind="stable")
    summ = summarise(df)
    # compare each condition with model A (paired by subject; counts summed over seeds)
    A = df[df.cond == "model_A"]
    comp = []
    for (c, lv, rule), g in df.groupby(["cond", "level", "rule"], sort=False):
        if c == "model_A":
            continue
        ga = g.groupby("SubjectID")[["n_falls", "n_det", "n_fa", "hours"]].sum().reset_index()
        aa = A[A.rule == rule][["SubjectID", "n_falls", "n_det", "n_fa", "hours"]]
        p = paired(ga, aa, f"{c} {lv}", "model A", rule)
        comp.append(dict(cond=c, level=lv, rule=rule, extra=bool(g.extra.iloc[0]), p_fa_vs_A=p["p_fa"], p_recall_vs_A=p["p_recall"],
                         subj_fa_lower_than_A=p["subj_fa_lower_a"], subj_fa_higher_than_A=p["subj_fa_lower_b"]))
    summ = summ.merge(pd.DataFrame(comp), on=["cond", "level", "rule"], how="left")
    a_ref = summ[summ.cond == "model_A"].set_index("rule")
    # worse than A: more false alarms per hour than A, or recall lower than A with paired p < 0.05
    summ["fah_above_A"] = [r.fa_per_h > a_ref.loc[r.rule, "fa_per_h"] if r.cond != "model_A" else np.nan
                           for r in summ.itertuples()]
    summ["recall_below_A"] = [r.sens < a_ref.loc[r.rule, "sens"] if r.cond != "model_A" else np.nan
                              for r in summ.itertuples()]
    summ["worse_than_A"] = [(r.fah_above_A or (r.recall_below_A and r.p_recall_vs_A < 0.05))
                            if r.cond != "model_A" else np.nan for r in summ.itertuples()]
    summ.to_csv(TAB / "v1_noise_summary.csv", index=False)
    native_noise(ctx).to_csv(TAB / "v1_baro_native_noise.csv", index=False)
    pd.set_option("display.width", 250)
    print(summ[["cond", "level", "rule", "sens", "fa_per_h", "fah_lo", "fah_hi", "fah_seed_min", "fah_seed_max",
                "p_fa_vs_A", "worse_than_A"]].round(3).to_string(index=False))
    figure(summ)


def figure(summ: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"sens98": "#2a78d6", "sens99": "#eb6834"}
    lab = {"sens98": "98 % recall target", "sens99": "99 % recall target"}
    xl = {"white": "white noise sd [Pa]", "drift": "drift [Pa / min], random sign", "impulse": "door-type step / pulse [Pa]"}
    fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, kind in zip(axs, ("white", "drift", "impulse")):
        for rule in RULES:
            clean = summ[(summ.cond == "clean") & (summ.rule == rule)].iloc[0]
            g = summ[(summ.cond == kind) & (summ.rule == rule)].sort_values("level")
            x = np.r_[0, g.level.values]; y = np.r_[clean.fa_per_h, g.fa_per_h.values]
            lo = np.r_[clean.fah_lo, g.fah_lo.values]; hi = np.r_[clean.fah_hi, g.fah_hi.values]
            ax.fill_between(x, lo, hi, color=col[rule], alpha=.12, lw=0)
            ax.plot(x, y, marker="o", ms=5, lw=2, color=col[rule], label=f"v1 A+B, {lab[rule]}")
            ex = g[g.extra.fillna(False).astype(bool)]
            ax.plot(ex.level, ex.fa_per_h, "o", ms=7, mfc="white", mec=col[rule], mew=1.5,
                    label="extra level (beyond request)" if rule == "sens99" else None)
            a = summ[(summ.cond == "model_A") & (summ.rule == rule)].iloc[0]
            ax.axhline(a.fa_per_h, color=col[rule], ls="--", lw=1.2, label=f"model A, {lab[rule]}")
        ax.set_xscale("symlog", linthresh=1 if kind == "white" else 5); ax.set_xlim(left=0)
        ax.set_xlabel(xl[kind]); ax.grid(alpha=.25); ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("false alarms / hour (LOSO, 95 % CI band)")
    axs[0].legend(fontsize=7, frameon=False)
    fig.suptitle("v1 (A+B) with barometer noise added to test data only; dashed = model A (no barometer)", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "v1_noise_fah.png", dpi=130)


if __name__ == "__main__":
    import sys
    run_extra() if "--extra" in sys.argv else main()
