# Section 6.4: external validation on new occupations and a new resume template (Supplement 4)
# Usage: python ext_eval.py data   (files results_ext_<model>.csv may sit in data/ or data/external/)
import glob, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D = sys.argv[1] if len(sys.argv) > 1 else "."
CUT = 60
DELTA = 6
files = sorted(glob.glob(os.path.join(D, "results_ext_*.csv")) + glob.glob(os.path.join(D, "external", "results_ext_*.csv")))
d = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype={"tier": str, "raw": str}) for f in files])
d = d[~d.raw.fillna("").str.startswith("ERROR")].drop_duplicates(["model", "run", "pid"], keep="last")
d["score"] = pd.to_numeric(d.score, errors="coerce")
print("valid calls", len(d), "excluded scores", ((d.score < 1) | (d.score > 100) | d.score.isna()).sum())
d = d[(d.score >= 1) & (d.score <= 100)].copy()
d["t"] = d.tier.str[0].astype(int)
d["text"] = d.job + "|" + d.tier
orig = d[d.pid < 4000].copy()
blind = d[d.pid > 4000].copy()
orig["cond"] = orig.age.astype(str) + "_" + orig.exp_years.astype(str)
key = ["model", "job", "tier", "gender", "exp_years"]

# ---- A. validity: tier means and variance explained by tier, original (28/5) vs blind
o28 = orig[orig.cond == "28_5"]
print("\nA. mean score by tier (original age 28 / blind 5 yrs):")
print(pd.DataFrame({"orig28": o28.groupby("t").score.mean().round(1), "blind5": blind[blind.exp_years == 5].groupby("t").score.mean().round(1)}))
for nm, x in [("original", orig), ("blind", blind)]:
    tot = ((x.score - x.score.mean()) ** 2).sum()
    for m, xm in x.groupby("model"):
        pass
    r = smf.ols("score ~ C(t)", x).fit().ssr
    print(nm, "share of variance explained by tier: %.1f%%" % (100 * (tot - r) / tot))
tm_o = o28.groupby(["model", "text"]).score.mean(); tm_b = blind[blind.exp_years == 5].groupby(["model", "text"]).score.mean()
print("text-level mean scores, original vs blind: corr %.3f" % pd.concat([tm_o, tm_b], axis=1).corr().iloc[0, 1])
# pass rates by tier
print("pass rate by tier, blind:", blind.assign(p=blind.score >= CUT).groupby("t").p.mean().round(3).to_dict())

# ---- B. age effects in the new setting (original resumes, tier 3)
o3 = orig[orig.t == 3].copy()
f = smf.ols("score ~ C(text) + C(gender) + C(model) + C(cond, Treatment('28_5'))", o3).fit(cov_type="cluster", cov_kwds={"groups": o3.pid})
print("\nB. tier-3 score effects vs 28/5:", {k[-6:-1]: (round(v, 2), round(f.pvalues[k], 4)) for k, v in f.params.items() if "cond" in k})
fa = smf.ols("score ~ C(text) + C(gender) + C(model) + C(cond, Treatment('28_5'))", orig).fit(cov_type="cluster", cov_kwds={"groups": orig.pid})
print("   all tiers:", {k[-6:-1]: (round(v, 2), round(fa.pvalues[k], 4)) for k, v in fa.params.items() if "cond" in k})
bl3 = blind[blind.t == 3]
fb = smf.ols("score ~ C(text) + C(gender) + C(model) + C(exp_years)", bl3).fit(cov_type="cluster", cov_kwds={"groups": bl3.pid})
print("   blind tier 3, 17 vs 5 yrs:", {k: (round(v, 2), round(fb.pvalues[k], 4)) for k, v in fb.params.items() if "exp_years" in k})

rng = np.random.default_rng(2026)


def boot_ratio(w, a, b, B=3000):
    est = w[a].mean() / w[b].mean()
    units = w.index.get_level_values(0).unique().values
    g = [w.loc[u] for u in units]
    bs = []
    for _ in range(B):
        s = pd.concat([g[i] for i in rng.integers(0, len(g), len(g))])
        if s[b].mean() > 0:
            bs.append(s[a].mean() / s[b].mean())
    # resamples whose reference pass rate is zero are discarded; their number is reported
    return "%.2f [%.2f, %.2f] (discarded %d of %d)" % (est, np.percentile(bs, 2.5), np.percentile(bs, 97.5), B - len(bs), B)


# candidate table for tier 3: S0 = original run 1; S4 = blind mean of runs 1-2
o3["bid"] = o3.text + "|" + o3.gender
r1 = o3[o3.run == 1]
b12 = blind[blind.run <= 2].groupby(key).score.mean()
r1 = r1.assign(b2=[b12.get(k, np.nan) for k in zip(r1.model, r1.job, r1.tier, r1.gender, r1.exp_years)])
for cut in [CUT, 50]:
    print("\nC. tier-3 pass-rate ratios vs 28/5 (cutoff %d; bootstrap over 16 base resumes):" % cut)
    for nm, col in [("S0 original, 1 run", "score"), ("S4 blind, mean of 2 runs", "b2")]:
        x = r1.assign(p=(r1[col] >= cut) * 1.0)
        w = x.groupby(["bid", "model", "cond"]).p.mean().unstack()
        print("  ", nm, "pass %.3f" % x.p.mean(), "| 40,5y", boot_ratio(w, "40_5", "28_5"), "| 40,17y", boot_ratio(w, "40_17", "28_5"))
    s1 = o3.groupby(["bid", "model", "cond"]).score.mean().ge(cut).astype(float).unstack()
    print("   S1 original, mean of 2 runs pass %.3f | 40,5y" % s1.stack().mean(), boot_ratio(s1, "40_5", "28_5"), "| 40,17y", boot_ratio(s1, "40_17", "28_5"))

# ---- D. test-retest of the full protocol: decision from runs 1-2 vs decision from runs 3-4 (blind)
pv = blind.pivot_table(index=key + ["t"], columns="run", values="score").dropna().reset_index()
pv["mA"] = pv[[1, 2]].mean(axis=1); pv["mB"] = pv[[3, 4]].mean(axis=1)


def decide(m, delta):
    return np.where((m - CUT).abs() < delta, "review", np.where(m >= CUT, "invite", "reject"))


print("\nD. test-retest (blind resumes; decision A from runs 1-2, decision B from runs 3-4)")
for scope, x in [("tier 3", pv[pv.t == 3]), ("all tiers", pv)]:
    single = ((x[1] >= CUT) != (x[3] >= CUT)).mean()        # single run vs an independent single run
    for delta in [0, 4, DELTA]:
        A = decide(x.mA, delta); B = decide(x.mB, delta)
        both_auto = (A != "review") & (B != "review")
        opp = ((A == "invite") & (B == "reject")) | ((A == "reject") & (B == "invite"))
        print("  %-9s delta %d: routed %.3f; opposite automatic decisions %.3f of all pairs (%.3f of pairs automatic in both); any change %.3f" % (
            scope, delta, (A == "review").mean(), opp.mean(), opp[both_auto].mean() if both_auto.any() else np.nan, (A != B).mean()))
    print("  %-9s single run vs independent single run: pass/fail differs %.3f" % (scope, single))
# original resumes: single-run test-retest for comparison
po = orig.pivot_table(index=["model", "pid", "t"], columns="run", values="score").dropna().reset_index()
print("  original resumes, run 1 vs run 2 pass/fail differs: tier 3 %.3f, all tiers %.3f" % (
    ((po[po.t == 3][1] >= CUT) != (po[po.t == 3][2] >= CUT)).mean(), ((po[1] >= CUT) != (po[2] >= CUT)).mean()))
# review load over all applicants (blind, runs 1-2), all tiers equally weighted
rt = pd.Series(decide(pv.mA, DELTA) == "review").groupby(pv.t.values).mean()
print("  share routed by tier (delta 6):", rt.round(3).to_dict(), "| equal-weight average over tiers %.3f" % rt.mean())
print("\nper model tier-3 ratio 40,17y (S0 -> S4):")
for m, x in r1.groupby("model"):
    a = x.assign(p=(x.score >= CUT) * 1.0).groupby("cond").p.mean(); b = x.assign(p=(x.b2 >= CUT) * 1.0).groupby("cond").p.mean()
    print("  ", m, "%.2f -> %.2f" % (a["40_17"] / a["28_5"], b["40_17"] / b["28_5"]))

# ---- E. transition counts between the two replications of the full protocol (tier 3, delta 6)
x3 = pv[pv.t == 3]
A = pd.Series(decide(x3.mA, DELTA), name="replication 1"); B = pd.Series(decide(x3.mB, DELTA), name="replication 2")
print("\nE. tier-3 transitions (resume-model pairs, n=%d):" % len(x3))
print(pd.crosstab(A, B, margins=True))
both = (A != "review") & (B != "review")
print("automatic in both: %d; reversed among them: %d" % (both.sum(), (both & (A != B)).sum()))

# ---- F. sensitivity: bootstrap over the 8 tier-3 base texts instead of 16 base resumes
r1["txt"] = r1.text
for cut in [50, 60]:
    for nm, col in [("S0 original, 1 run", "score"), ("S4 blind, mean of 2 runs", "b2")]:
        xx = r1.assign(p=(r1[col] >= cut) * 1.0)
        w = xx.groupby(["txt", "bid", "model", "cond"]).p.mean().unstack()
        print("F. cut %d %s | by base text: 40,5y %s | 40,17y %s" % (cut, nm, boot_ratio(w, "40_5", "28_5"), boot_ratio(w, "40_17", "28_5")))
f2 = smf.ols("score ~ C(text) + C(gender) + C(model) + C(cond, Treatment('28_5'))", o3).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(o3.text)[0]})
print("F. tier-3 score effects clustered by base text:", {k[-6:-1]: (round(v, 2), round(f2.pvalues[k], 4)) for k, v in f2.params.items() if "cond" in k})
fb2 = smf.ols("score ~ C(text) + C(gender) + C(model) + C(exp_years)", bl3).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(bl3.text)[0]})
print("F. blind 17 vs 5 clustered by base text:", {k: (round(v, 2), round(fb2.pvalues[k], 4)) for k, v in fb2.params.items() if "exp_years" in k})
print("G. review load in this sample (tier 3 = half of texts): %.3f" % (decide(pv.mA, DELTA) == "review").mean())
# ---- H. review rates in each replication and on average (delta 6)
for scope, x in [("tier 3", pv[pv.t == 3]), ("all tiers", pv)]:
    a = (decide(x.mA, DELTA) == "review").mean(); b = (decide(x.mB, DELTA) == "review").mean()
    print("H. %s routed: replication 1 %.3f, replication 2 %.3f, average %.3f" % (scope, a, b, (a + b) / 2))
rB = pd.Series(decide(pv.mB, DELTA) == "review").groupby(pv.t.values).mean()
print("H. equal-weight over tiers: replication 1 %.3f, replication 2 %.3f" % (rt.mean(), rB.mean()))
