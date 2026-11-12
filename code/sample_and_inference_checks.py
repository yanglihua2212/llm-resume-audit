# Table B1 sample accounting; t-based cluster p-values (Sections 6.3, 6.4); bootstrap zero-denominator check
# Usage: python sample_and_inference_checks.py data
# Sample accounting, t-based cluster p-values, bootstrap zero-denominator counts
import glob, os, sys, numpy as np, pandas as pd, statsmodels.formula.api as smf
D = sys.argv[1]
def raw(p, sub=""):
    fs = sorted(glob.glob(os.path.join(D, sub, p)))
    if p.startswith("results_[!tp]"): fs = [f for f in fs if "mask" not in f]
    return pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype={"tier": str, "raw": str}) for f in fs])
print("== sample accounting ==")
for name, p, sub, planned, isbin in [("Main", "results_[!tp]*.csv", "", 6000, False), ("Supplement 1", "results_t3_*.csv", "", 4800, False),
                                     ("Supplement 2 binary", "results_p_bin_*.csv", "", 4000, True), ("Supplement 2 fairness", "results_p_fair_*.csv", "", 4000, False),
                                     ("Supplement 3 blind", "results_mask_*.csv", "blind", 1200, False), ("Supplement 4 external", "results_ext_*.csv", "external", 2240, False)]:
    d = raw(p, sub); err = d.raw.fillna("").str.startswith("ERROR")
    ok = d[~err].drop_duplicates(["model", "run", "pid"], keep="last")
    if isbin:
        r = ok.raw.astype(str).str.strip(); inval = int((~(r.str.startswith("是") | r.str.startswith("否") | r.str.startswith("不") | r.str.contains("不雇佣"))).sum())
    else:
        s = pd.to_numeric(ok.score, errors="coerce"); inval = int(((s < 1) | (s > 100) | s.isna()).sum())
    print("%-22s planned %5d logged %5d http_errors %4d valid_responses %5d invalid %d analysed %5d missing %d" % (name, planned, len(d), err.sum(), len(ok), inval, len(ok) - inval, planned - len(ok)))

def load(p, sub=""):
    d = raw(p, sub); d = d[~d.raw.fillna("").str.startswith("ERROR")].drop_duplicates(["model", "run", "pid"], keep="last")
    d["score"] = pd.to_numeric(d.score, errors="coerce"); return d[(d.score >= 1) & (d.score <= 100)].copy()
def fitp(form, x, groups, coefs):
    out = {}
    for lab, ut in [("z", False), ("t(G-1)", True)]:
        f = smf.ols(form, x).fit(cov_type="cluster", cov_kwds={"groups": groups}, use_t=ut)
        out[lab] = {k.split("[T.")[1][:-1]: (round(f.params[k], 2), round(f.pvalues[k], 4)) for k in f.params.index if any(c in k for c in coefs)}
    return out
main = load("results_[!tp]*.csv"); t3 = load("results_t3_*.csv")
P = pd.concat([main[main.tier == "3"], t3]); P["text"] = P.job + "|" + P.tier
P["cond"] = P.age.astype(str) + "_" + np.where(P.exp_years > 5, "rise", np.where(P.age == 28, "base", "fix"))
G = pd.factorize(P.text)[0]
print("\n== pooled tier-3 age effects, clustered by 20 base texts ==")
print(fitp("score ~ C(job)*C(tier) + C(model) + C(gender) + C(marital) + C(cond, Treatment('28_base'))", P, G, ["40_"]))
# matched comparison: same texts, runs 1-2, conditions with blind counterparts
O = P[(P.run <= 2) & P.cond.isin(["28_base", "35_rise", "40_rise"])]
B = load("results_mask_*.csv", "blind"); B["text"] = B.job + "|" + B.tier
print("\n== matched (runs 1-2, same texts): 17 vs 5 years ==")
print("original:", fitp("score ~ C(job)*C(tier) + C(gender) + C(marital) + C(model) + C(exp_years)", O, pd.factorize(O.text)[0], ["exp_years"]))
print("original, clustered by resume:", fitp("score ~ C(job)*C(tier) + C(gender) + C(marital) + C(model) + C(exp_years)", O, O.pid, ["exp_years"])["z"])
print("blind:   ", fitp("score ~ C(job)*C(tier) + C(gender) + C(model) + C(exp_years)", B, pd.factorize(B.text)[0], ["exp_years"]))
E = load("results_ext_*.csv", "external"); E["text"] = E.job + "|" + E.tier; E["t"] = E.tier.str[0].astype(int)
eo = E[(E.pid < 4000) & (E.t == 3)].copy(); eo["cond"] = eo.age.astype(str) + "_" + eo.exp_years.astype(str)
eb = E[(E.pid > 4000) & (E.t == 3)]
print("\n== external, clustered by 8 base texts ==")
print("original:", fitp("score ~ C(text) + C(gender) + C(model) + C(cond, Treatment('28_5'))", eo, pd.factorize(eo.text)[0], ["40_"]))
print("blind:   ", fitp("score ~ C(text) + C(gender) + C(model) + C(exp_years)", eb, pd.factorize(eb.text)[0], ["exp_years"]))
# bootstrap zero denominators in external validation (cutoff 60, S0)
rng = np.random.default_rng(2026)
r1 = eo[eo.run == 1].assign(p=lambda x: (x.score >= 60) * 1.0, bid=lambda x: x.text + "|" + x.gender)
w = r1.groupby(["bid", "model", "cond"]).p.mean().unstack(); units = w.index.get_level_values(0).unique(); g = [w.loc[u] for u in units]
zero = 0
for _ in range(3000):
    s = pd.concat([g[i] for i in rng.integers(0, len(g), len(g))]); zero += s["28_5"].mean() == 0
print("\nexternal S0 cutoff 60: resamples with zero reference pass rate %d of 3000" % zero)
