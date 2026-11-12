# Section 6: evaluate the blind–repeat–route protocol and alternative strategies on the 400 tier-3 resumes
# Usage: python method_eval.py data   (blind-resume files may sit in data/ or data/blind/)
import glob, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D = sys.argv[1] if len(sys.argv) > 1 else "."
CUT = 60


def load(pattern):
    parts = []
    files = sorted(glob.glob(os.path.join(D, pattern)) + glob.glob(os.path.join(D, "blind", pattern)))
    if pattern.startswith("results_[!tp]"):
        files = [f for f in files if "results_mask_" not in f]   # main experiment only
    for f in files:
        d = pd.read_csv(f, encoding="utf-8-sig", dtype={"tier": str, "raw": str})
        d = d[~d.raw.fillna("").str.startswith("ERROR")]
        parts.append(d.drop_duplicates(["model", "run", "pid"], keep="last"))
    d = pd.concat(parts)
    d["score"] = pd.to_numeric(d.score, errors="coerce")
    return d[(d.score >= 1) & (d.score <= 100)]


main = load("results_[!tp]*.csv")
t3 = load("results_t3_*.csv")
orig = pd.concat([main[main.tier == "3"], t3])
orig = orig[orig.run <= 2]                       # use two runs, as in the blind experiment
blind = load("results_mask_*.csv")
print("original tier-3 rows", len(orig), "blind rows", len(blind))

orig["cond"] = orig.age.astype(str) + "_" + np.where(orig.exp_years > 5, "rise", np.where(orig.age == 28, "base", "fix"))
orig["bid"] = orig.job + "|" + orig.tier + "|" + orig.gender + "|" + orig.marital
key = ["job", "tier", "gender", "exp_years"]

# candidate-level table: one row per (model, original resume)
cand = orig.groupby(["model", "pid", "bid", "cond"] + key + ["marital", "age"]).agg(
    s1=("score", lambda x: x.iloc[0] if len(x) > 0 else np.nan), s2=("score", "mean")).reset_index()
r1 = orig[orig.run == 1].set_index(["model", "pid"]).score
cand["s1"] = [r1.get((m, p), np.nan) for m, p in zip(cand.model, cand.pid)]
# blind scores mapped to each original resume (same text without birth date / marital status)
b1 = blind[blind.run == 1].set_index(["model"] + key).score
b2 = blind.groupby(["model"] + key).score.mean()
cand["b1"] = [b1.get((m, j, t, g, e), np.nan) for m, j, t, g, e in zip(cand.model, cand.job, cand.tier, cand.gender, cand.exp_years)]
cand["b2"] = [b2.get((m, j, t, g, e), np.nan) for m, j, t, g, e in zip(cand.model, cand.job, cand.tier, cand.gender, cand.exp_years)]
# counterfactual averaging: average the run-1 scores of all versions that differ only in age (if feasible) and marital status
grp = ["model", "job", "tier", "gender", "exp_years"]
cand["cf"] = cand.groupby(grp).s1.transform("mean")
cand.loc[cand.exp_years > 5, "cf"] = cand[cand.exp_years > 5].groupby(grp + ["age"]).s1.transform("mean")
print("missing", cand[["s1", "s2", "b1", "b2", "cf"]].isna().sum().to_dict())

STRATS = [("S0 Original, 1 run", "s1", 1), ("S1 Original, mean of 2 runs", "s2", 2),
          ("S2 Counterfactual averaging", "cf", None), ("S3 Blind, 1 run", "b1", 1), ("S4 Blind, mean of 2 runs", "b2", 2)]
rng = np.random.default_rng(2026)
bids = cand.bid.unique()


def ratio(d, col, a, b, by="cond"):
    w = d.groupby(["bid", "model", by])[col].mean().unstack()
    return w[a].mean() / w[b].mean()


def boot(d, col, a, b, by="cond", B=2000):
    w = d.groupby(["bid", "model", by])[col].mean().unstack()
    g = [w.loc[x] for x in bids]
    est = w[a].mean() / w[b].mean()
    bs = []
    for _ in range(B):
        s = pd.concat([g[i] for i in rng.integers(0, len(g), len(g))])
        bs.append(s[a].mean() / s[b].mean())
    return est, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


rows = []
for name, col, R in STRATS:
    d = cand.copy()
    d["p"] = (d[col] >= CUT) * 1.0
    a5 = boot(d, "p", "40_fix", "28_base")
    a17 = boot(d, "p", "40_rise", "28_base")
    gr = ratio(d.assign(k=d.job + d.tier + d.marital + d.cond), "p", "女", "男", by="gender")
    w = d.groupby(["job", "tier", "gender", "cond", "model", "marital"]).p.mean().unstack()
    mr = w["已婚已育"].mean() / w["未婚"].mean()
    # disagreement across models per original resume
    pm = d.groupby(["pid", "model"])[col].mean().unstack()
    n = (pm >= CUT).sum(axis=1)
    dis = ((n > 0) & (n < pm.shape[1])).mean()
    cost = {1: 1, 2: 2, None: "2–6"}[R]
    rows.append([name, round(d.p.mean(), 3), "%.2f [%.2f, %.2f]" % a5, "%.2f [%.2f, %.2f]" % a17, round(gr, 2), round(mr, 2), round(dis, 3), cost])
res = pd.DataFrame(rows, columns=["strategy", "pass", "AIR 40,5y", "AIR 40,17y", "F/M", "married/single", "disagree", "calls"])
print(res.to_string())

# run-to-run flips (two runs) original vs blind
fo = orig.assign(p=orig.score >= CUT).groupby(["model", "pid"]).p.nunique().gt(1).mean()
fb = blind.assign(p=blind.score >= CUT).groupby(["model", "pid"]).p.nunique().gt(1).mean()
print("flip rate 2 runs: original %.3f blind %.3f" % (fo, fb))
# validity: blind vs original 28-year-old baseline scores (same text with age 28)
base = cand[cand.cond == "28_base"].groupby(["model", "job", "tier", "gender"])[["s2", "b2"]].mean()
print("blind vs age-28 original: mean diff %.2f, corr %.3f" % ((base.b2 - base.s2).mean(), base.corr().iloc[0, 1]))
print("mean score original %.1f blind %.1f" % (cand.s2.mean(), cand.b2.mean()))
# experience effect without age: blind 17 vs 5 years, and 12 vs 5
bl = blind.copy()
fit = smf.ols("score ~ C(job)*C(tier) + C(gender) + C(model) + C(exp_years)", data=bl).fit(cov_type="cluster", cov_kwds={"groups": bl.pid})
print("blind experience effects:", {k: (round(v, 2), round(fit.pvalues[k], 4)) for k, v in fit.params.items() if "exp_years" in k})
# original: same contrasts, for comparison (age 28/5, 35/12, 40/17)
o = orig[orig.cond.isin(["28_base", "35_rise", "40_rise"])]
fit2 = smf.ols("score ~ C(job)*C(tier) + C(gender) + C(marital) + C(model) + C(exp_years)", data=o).fit(cov_type="cluster", cov_kwds={"groups": o.pid})
print("original (age rises with experience):", {k: (round(v, 2), round(fit2.pvalues[k], 4)) for k, v in fit2.params.items() if "exp_years" in k})
# per-model blind experience effect and per-model AIR 40,17
for m, d in cand.groupby("model"):
    d = d.copy(); d["po"] = (d.s1 >= CUT) * 1.0; d["pb"] = (d.b1 >= CUT) * 1.0
    print(m, "AIR40_17 orig %.2f blind %.2f | AIR40_5 orig %.2f" % (ratio(d, "po", "40_rise", "28_base"), ratio(d, "pb", "40_rise", "28_base"), ratio(d, "po", "40_fix", "28_base")))

# routing: send |score - C| < delta to human review (blind, mean of 2 runs)
sd = blind.groupby(["model", "pid"]).score.std().mean()
print("blind within-resume run SD (2 runs) %.2f" % sd)
for delta in [0, 2, 4, 6, 8]:
    d = cand.copy()
    d["route"] = (d.b2 - CUT).abs() < delta
    d["auto_pass"] = ((d.b2 >= CUT) & ~d.route) * 1.0
    # how many routed cases would have flipped between the two runs
    bb = blind.pivot_table(index=["model"] + key, columns="run", values="score")
    bb["flip"] = (bb[1] >= CUT) != (bb[2] >= CUT)
    bb["mean"] = bb[[1, 2]].mean(axis=1)
    bb["route"] = (bb["mean"] - CUT).abs() < delta
    caught = bb[bb.flip].route.mean() if bb.flip.sum() else np.nan
    o2 = cand.copy(); o2["route"] = (o2.s2 - CUT).abs() < delta
    print("delta %d: routed blind %.3f (original %.3f); share of run-to-run flips caught %.2f; auto-pass %.3f" % (delta, d.route.mean(), o2.route.mean(), caught, d.auto_pass.mean()))
# reference reliability: same original text (age 28) scored in two separate runs
o28 = orig[orig.age == 28].pivot_table(index=["model", "job", "tier", "gender"], columns="run", values="score")
print("original age-28, run 1 vs run 2 corr %.3f" % o28.corr().iloc[0, 1])
bb2 = blind.pivot_table(index=["model"] + key, columns="run", values="score")
print("blind run 1 vs run 2 corr %.3f" % bb2.corr().iloc[0, 1])
# full protocol (blind + mean of 2 runs + routing): residual instability among automatic decisions,
# and review load over the whole applicant pool (all tiers, main experiment, mean of runs 1-2)
allm = main[main.run <= 2].groupby(["model", "pid", "tier"]).score.mean().reset_index()
bb = blind.pivot_table(index=["model"] + key, columns="run", values="score").dropna()
bb["mean"] = bb[[1, 2]].mean(axis=1)
bb["flip"] = (bb[1] >= CUT) != (bb[2] >= CUT)
d17 = cand.copy()
for delta in [0, 2, 4, 6, 8]:
    auto = bb[(bb["mean"] - CUT).abs() >= delta]
    load_all = ((allm.score - CUT).abs() < delta).mean()
    d17["route"] = (d17.b2 - CUT).abs() < delta
    d17["ap"] = ((d17.b2 >= CUT) & ~d17.route) * 1.0
    d17["ar"] = ((d17.b2 < CUT) & ~d17.route) * 1.0
    print("delta %d: flips among automatic decisions %.3f; review load all tiers %.3f; auto-pass AIR40_17 %.2f; auto-reject ratio40_17 %.2f" % (
        delta, auto.flip.mean(), load_all, ratio(d17, "ap", "40_rise", "28_base"), ratio(d17, "ar", "40_rise", "28_base")))
# like-for-like validity check: correlation between single scores of the same text
# (a) two runs of the original age-28 resume; (b) original age-28 run r vs blind run r
o = orig[orig.age == 28].pivot_table(index=["model", "pid"] + key, columns="run", values="score").dropna().reset_index()
bl2 = blind.pivot_table(index=["model"] + key, columns="run", values="score")
o = o.merge(bl2, left_on=["model"] + key, right_index=True, suffixes=("_o", "_b")).dropna()
print("single scores: original run1 vs run2 corr %.3f; original vs blind (same run) corr %.3f / %.3f" % (
    o["1_o"].corr(o["2_o"]), o["1_o"].corr(o["1_b"]), o["2_o"].corr(o["2_b"])))
