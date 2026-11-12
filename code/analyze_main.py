# Table 3 and Section 5.1: tier means, variance decomposition, score-level effects, model agreement (main experiment)
# Usage: python analyze_main.py data
import sys, glob
import pandas as pd, numpy as np
import statsmodels.formula.api as smf
import statsmodels.api as sm
pd.set_option("display.width", 200)
fs = sorted(glob.glob(sys.argv[1] + "/results_[!tp]*.csv"))
df = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype={"score": "float"}) for f in fs])
df = df[df.score.notna()].copy()
df = df[(df.score>=1)&(df.score<=100)]
df["agecond"] = df.age.astype(str) + "_" + np.where(df.exp_years>5, "coupled", np.where(df.age==28, "base", "fixed"))
print(df.groupby("model").size())
print("\n== mean score by tier ==")
print(df.pivot_table(index="tier", columns="model", values="score", aggfunc="mean").round(1))
print("\n== pass rate (>=60) by tier ==")
df["passd"] = (df.score>=60).astype(int)
print(df.pivot_table(index="tier", columns="model", values="passd", aggfunc="mean").round(2))

rows = []
for m, d in df.groupby("model"):
    # variance decomposition: sequential (type I) sums of squares, capability first.
    # Computed from residual sums of squares of nested models, because the resume id
    # is collinear with the design factors and anova_lm mis-assigns SS in that case.
    tot = ((d.score - d.score.mean()) ** 2).sum()
    rss_cap = smf.ols("score ~ C(job)*C(tier)", data=d).fit().ssr
    rss_demo = smf.ols("score ~ C(job)*C(tier) + C(agecond) + C(gender) + C(marital)", data=d).fit().ssr
    rss_pid = smf.ols("score ~ C(pid)", data=d).fit().ssr
    cap = (tot - rss_cap) / tot
    demo = (rss_cap - rss_demo) / tot
    other = (rss_demo - rss_pid) / tot   # remaining profile-specific (interactions)
    noise = rss_pid / tot                # within-resume run-to-run noise
    # effects with cluster-robust SE by profile
    f2 = smf.ols("score ~ C(job)*C(tier) + C(agecond, Treatment('28_base')) + C(gender, Treatment('男')) + C(marital, Treatment('未婚'))", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.pid})
    coefs = {}
    for k in f2.params.index:
        if "agecond" in k or "gender" in k or "marital" in k:
            nm = k.split("[T.")[1].rstrip("]")
            coefs[nm] = (round(f2.params[k],2), round(f2.pvalues[k],4))
    sd = d.groupby("pid").score.std()
    flips = d.groupby("pid").passd.nunique()
    rows.append(dict(model=m, cap=round(100*cap,3), demo=round(100*demo,3), profile_resid=round(100*other,2), run_noise=round(100*noise,2),
                     run_sd=round(sd.mean(),2), flip_pct=round(100*(flips>1).mean(),1)))
    print(f"\n== {m} effects (points vs 28-year-old / male / unmarried; cluster-robust p) ==")
    for k,v in coefs.items(): print(f"   {k:10s} {v[0]:6.2f}  p={v[1]}")
print("\n== variance shares (%) and run-to-run noise ==")
print(pd.DataFrame(rows).to_string(index=False))

# inter-model disagreement on same profile
pm = df.groupby(["pid","model"]).score.mean().unstack()
meta = df.drop_duplicates("pid").set_index("pid")[["job","tier"]]
pm = pm.join(meta)
mods = [c for c in pm.columns if c not in ("job","tier")]
pm["range"] = pm[mods].max(axis=1) - pm[mods].min(axis=1)
pm["n_pass"] = (pm[mods]>=60).sum(axis=1)
print("\n== between-model disagreement per profile ==")
print(pm.groupby("tier")[["range"]].mean().round(1).T)
pm["split"] = (pm.n_pass>0)&(pm.n_pass<len(mods))
print("share of profiles where models disagree on pass/fail, by tier:")
print(pm.groupby("tier").split.mean().round(2).to_dict())
print("correlation of profile mean scores between models:")
print(pm[mods].corr().round(2))
# within-tier correlation (signal beyond tier)
