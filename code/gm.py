# Section 5.2: pooled tier-3 score effects of age, and gender / marital pass-rate ratios
# Usage: python gm.py data
import sys, glob, os
import numpy as np, pandas as pd
D=sys.argv[1]; rng=np.random.default_rng(5)
def load(p):
    d=pd.concat([pd.read_csv(f,encoding="utf-8-sig",dtype={"score":"float","tier":"str"}) for f in sorted(glob.glob(os.path.join(D,p)))])
    d=d[d.score.notna()].drop_duplicates(["model","run","pid"],keep="last"); return d
m=load("results_[!tp]*.csv"); t=load("results_t3_*.csv")
d=pd.concat([m[m.tier.astype(float).astype(int)==3],t]); d=d[(d.score>=1)&(d.score<=100)]
d["agecond"]=d.age.astype(str)+"_"+np.where(d.exp_years>5,"coupled",np.where(d.age==28,"base","fixed"))
d["pass"]=(d.score>=60).astype(int)
print("tier3 rows",len(d),"profiles",d.pid.nunique())
for var,a,b in [("gender","女","男"),("marital","已婚已育","未婚")]:
    other=[c for c in ["job","tier","marital","gender","agecond"] if c!=var]
    d["key"]=d[other].astype(str).agg("|".join,axis=1)
    w=d.pivot_table(index=["key","model"],columns=var,values="pass",aggfunc="mean")
    keys=w.index.get_level_values(0).unique().tolist(); g={k:w.loc[k] for k in keys}
    rs=[]
    for _ in range(3000):
        s=pd.concat([g[keys[i]] for i in rng.integers(0,len(keys),len(keys))]); rs.append(s[a].mean()/s[b].mean())
    print(var,a,"/",b,round(w[a].mean(),3),round(w[b].mean(),3),"AIR",round(w[a].mean()/w[b].mean(),2),np.percentile(rs,[2.5,97.5]).round(2))
# score-level age effect pooled tier3
import statsmodels.formula.api as smf
f=smf.ols("score ~ C(job)*C(tier) + C(model) + C(agecond, Treatment('28_base')) + C(gender) + C(marital)",data=d).fit(cov_type="cluster",cov_kwds={"groups":d.pid.astype(str)+d.model})
print(f.params.filter(like="agecond").round(2).to_dict()); print(f.pvalues.filter(like="agecond").round(4).to_dict())
