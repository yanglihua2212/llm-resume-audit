import sys, glob, os
import numpy as np, pandas as pd
D=sys.argv[1]; rng=np.random.default_rng(11)
def rd(p):
    return pd.concat([pd.read_csv(f,encoding="utf-8-sig",dtype={"score":"float","tier":"str"}) for f in sorted(glob.glob(os.path.join(D,p)))])
orig=pd.concat([rd("results_[!tp]*.csv"),rd("results_t3_*.csv")])
orig=orig[orig.score.notna()&(orig.score>=1)&(orig.score<=100)]
orig=orig[orig.tier.astype(str).str.startswith("3")].drop_duplicates(["model","run","pid"],keep="last")
orig["prompt"]="score"; orig["pass"]=(orig.score>=60).astype(float)
fair=rd("results_p_fair_*.csv"); fair=fair[fair.score.notna()&(fair.score>=1)&(fair.score<=100)].drop_duplicates(["model","run","pid"],keep="last")
fair["model"]=fair.model.str.replace("_fair",""); fair["prompt"]="fair"; fair["pass"]=(fair.score>=60).astype(float)
b=rd("results_p_bin_*.csv"); b=b[~b.raw.astype(str).str.startswith("ERROR")].drop_duplicates(["model","run","pid"],keep="last")
r=b.raw.astype(str).str.strip()
b["pass"]=np.where(r.str.startswith("是"),1.0,np.where(r.str.startswith("否")|r.str.startswith("不")|r.str.contains("不"),0.0,np.nan))
print("bin unparsed:", b["pass"].isna().sum(), r[b["pass"].isna()].head(3).tolist())
b=b[b["pass"].notna()]; b["model"]=b.model.str.replace("_bin",""); b["prompt"]="binary"
all_=pd.concat([orig,fair,b])
all_["agecond"]=all_.age.astype(str)+"_"+np.where(all_.exp_years>5,"coupled",np.where(all_.age==28,"base","fixed"))
all_["base"]=all_.job+"|"+all_.tier.astype(str)+"|"+all_.gender+"|"+all_.marital
print("\npass rate by prompt x model:")
print(all_.pivot_table(index="model",columns="prompt",values="pass").round(3))
def air(d,c="40_fixed",B=3000):
    w=d.pivot_table(index=["base","model"],columns="agecond",values="pass",aggfunc="mean")
    ks=w.index.get_level_values(0).unique().tolist(); g={k:w.loc[k] for k in ks}
    est=w[c].mean()/w["28_base"].mean(); bs=[]
    for _ in range(B):
        s=pd.concat([g[ks[i]] for i in rng.integers(0,len(ks),len(ks))]); bs.append(s[c].mean()/s["28_base"].mean())
    return round(w["28_base"].mean(),3),round(w[c].mean(),3),round(est,2),np.percentile(bs,[2.5,97.5]).round(2).tolist()
print("\nAIR 40_fixed and 40_coupled by prompt (pooled):")
for p in ["score","fair","binary"]:
    d=all_[all_.prompt==p]
    print(p, "40_fixed", air(d), "| 40_coupled", air(d,"40_coupled"), "| 35_fixed", air(d,"35_fixed",1500))
# score-level age penalty: original vs fair (same pids)
import statsmodels.formula.api as smf
sc=all_[all_.prompt.isin(["score","fair"])].copy()
f=smf.ols("score ~ C(base)*C(prompt) + C(model)*C(prompt) + C(agecond, Treatment('28_base'))*C(prompt)",data=sc).fit(cov_type="cluster",cov_kwds={"groups":sc.pid.astype(str)})
for k in f.params.index:
    if "agecond" in k: print(k, round(f.params[k],2), "p=",round(f.pvalues[k],4))
# DiD of pass for 40_fixed: bootstrap difference of AIR between fair and score
def airw(d):
    w=d.pivot_table(index=["base","model"],columns="agecond",values="pass",aggfunc="mean"); return w
ws=airw(all_[all_.prompt=="score"]); wf=airw(all_[all_.prompt=="fair"]); wb=airw(all_[all_.prompt=="binary"])
ks=ws.index.get_level_values(0).unique().tolist()
for name,w2 in [("fair-score",wf),("binary-score",wb)]:
    ds=[]
    for _ in range(3000):
        idx=[ks[i] for i in rng.integers(0,len(ks),len(ks))]
        a=pd.concat([ws.loc[k] for k in idx]); c=pd.concat([w2.loc[k] for k in idx])
        ds.append(c["40_fixed"].mean()/c["28_base"].mean()-a["40_fixed"].mean()/a["28_base"].mean())
    print(name,"AIR diff 40_fixed 95%CI",np.percentile(ds,[2.5,50,97.5]).round(2))
print("\nper-model 40_fixed AIR by prompt:")
for m in sorted(all_.model.unique()):
    print(m,[ (p, air(all_[(all_.prompt==p)&(all_.model==m)],B=800)[2]) for p in ["score","fair","binary"]])
# binary decision flip across 2 runs
fl=b.groupby(["model","pid"])["pass"].nunique(); print("binary run flip rate:",round(100*(fl>1).mean(),1),"%")
