# Robustness: cluster bootstrap and pooled regression with the 20 tier-3 base texts as clusters; tier-only variance shares
# Usage: python cluster_sensitivity.py data
# Sensitivity: cluster bootstrap by base TEXT (job x tier text: 20 clusters) instead of base resume (80)
import glob, os, sys, numpy as np, pandas as pd, statsmodels.formula.api as smf
D = sys.argv[1]
def load(p):
    fs = sorted(glob.glob(os.path.join(D, p)) + glob.glob(os.path.join(D, "blind", p)))
    if p.startswith("results_[!tp]"): fs = [f for f in fs if "mask" not in f]
    d = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype={"tier": str, "raw": str}) for f in fs])
    d = d[~d.raw.fillna("").str.startswith("ERROR")].drop_duplicates(["model", "run", "pid"], keep="last")
    return d
main = load("results_[!tp]*.csv"); t3 = load("results_t3_*.csv")
for d in (main, t3): d["score"] = pd.to_numeric(d.score, errors="coerce")
main = main[(main.score >= 1) & (main.score <= 100)]; t3 = t3[(t3.score >= 1) & (t3.score <= 100)]
# variance share of tier alone vs job, job x tier
for m, d in main.groupby("model"):
    tot = ((d.score - d.score.mean()) ** 2).sum()
    r_t = smf.ols("score ~ C(tier)", d).fit().ssr; r_j = smf.ols("score ~ C(job)", d).fit().ssr; r_jt = smf.ols("score ~ C(job)*C(tier)", d).fit().ssr
    print(m, "tier alone %.1f  job alone %.2f  job*tier %.1f" % (100*(tot-r_t)/tot, 100*(tot-r_j)/tot, 100*(tot-r_jt)/tot))
P = pd.concat([main[main.tier == "3"], t3])
P["cond"] = P.age.astype(str) + "_" + np.where(P.exp_years > 5, "rise", np.where(P.age == 28, "base", "fix"))
P["text"] = P.job + "|" + P.tier
P["bid"] = P.text + "|" + P.gender + "|" + P.marital
rng = np.random.default_rng(7)
def boot(d, col, c, unit, B=3000):
    w = d.groupby([unit, "bid", "model", "cond"])[col].mean().unstack()
    est = w[c].mean() / w["28_base"].mean()
    units = w.index.get_level_values(0).unique().values; g = [w.loc[u] for u in units]
    bs = []
    for _ in range(B):
        s = pd.concat([g[i] for i in rng.integers(0, len(g), len(g))]); bs.append(s[c].mean() / s["28_base"].mean())
    return "%.2f [%.2f, %.2f]" % (est, np.percentile(bs, 2.5), np.percentile(bs, 97.5))
print("n texts", P.text.nunique(), "n bases", P.bid.nunique())
for cut in (50, 60, 70):
    P["p"] = (P.score >= cut) * 1.0
    for c in ["40_fix", "40_rise"]:
        print("cut", cut, c, "base-resume:", boot(P, "p", c, "bid"), " base-text:", boot(P, "p", c, "text"))
# pooled regression with text-level clustering
f = smf.ols("score ~ C(text) + C(gender) + C(marital) + C(model) + C(cond, Treatment('28_base'))", P).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(P.text)[0]})
print({k[-12:]: (round(v, 2), round(f.pvalues[k], 4)) for k, v in f.params.items() if "cond" in k})
# Section 6 with text-level clusters
B_ = load("results_mask_*.csv"); B_["score"] = pd.to_numeric(B_.score, errors="coerce")
key = ["job", "tier", "gender", "exp_years"]
o = P[P.run <= 2].copy()
b2 = B_.groupby(["model"] + key).score.mean()
o["b2"] = [b2.get((m, j, t, g, e), np.nan) for m, j, t, g, e in zip(o.model, o.job, o.tier, o.gender, o.exp_years)]
c2 = o.groupby(["model", "pid", "bid", "text", "cond"] + key).agg(s1=("score", "first"), b2=("b2", "first")).reset_index()
r1 = o[o.run == 1].set_index(["model", "pid"]).score
c2["s1"] = [r1.get((m, p), np.nan) for m, p in zip(c2.model, c2.pid)]
for col in ["s1", "b2"]:
    c2["p"] = (c2[col] >= 60) * 1.0
    print("S6", col, "40_rise base-resume", boot(c2, "p", "40_rise", "bid"), "| base-text", boot(c2, "p", "40_rise", "text"))
# Section 6.3: experience effects with and without age cues, clustered by resume and by base text
Bm = load("results_mask_*.csv"); Bm["score"] = pd.to_numeric(Bm.score, errors="coerce"); Bm = Bm[(Bm.score >= 1) & (Bm.score <= 100)]
Bm["text"] = Bm.job + "|" + Bm.tier
O = P[P.cond.isin(["28_base", "35_rise", "40_rise"])]
for nm, x, form in [("blind", Bm, "score ~ C(job)*C(tier) + C(gender) + C(model) + C(exp_years)"),
                    ("original", O, "score ~ C(job)*C(tier) + C(gender) + C(marital) + C(model) + C(exp_years)")]:
    for lab, g in [("resume", x.pid), ("base text", pd.factorize(x.text)[0])]:
        f = smf.ols(form, x).fit(cov_type="cluster", cov_kwds={"groups": g})
        print("S6.3", nm, "clustered by", lab, {k: (round(v, 2), round(f.pvalues[k], 4)) for k, v in f.params.items() if "exp_years" in k})
