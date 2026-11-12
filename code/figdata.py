import sys, glob, os, json
import numpy as np, pandas as pd
D=sys.argv[1]; rng=np.random.default_rng(7)
def rd(p): return pd.concat([pd.read_csv(f,encoding="utf-8-sig",dtype={"score":"float","tier":"str"}) for f in sorted(glob.glob(os.path.join(D,p)))])
main=rd("results_[!tp]*.csv"); main=main[main.score.notna()&(main.score>=1)&(main.score<=100)].drop_duplicates(["model","run","pid"],keep="last")
t3=rd("results_t3_*.csv"); t3=t3[t3.score.notna()&(t3.score>=1)&(t3.score<=100)].drop_duplicates(["model","run","pid"],keep="last")
fair=rd("results_p_fair_*.csv"); fair=fair[fair.score.notna()&(fair.score>=1)&(fair.score<=100)].drop_duplicates(["model","run","pid"],keep="last"); fair["model"]=fair.model.str.replace("_fair","")
b=rd("results_p_bin_*.csv"); b=b[~b.raw.astype(str).str.startswith("ERROR")].drop_duplicates(["model","run","pid"],keep="last"); r=b.raw.astype(str).str.strip()
b["pass"]=np.where(r.str.startswith("是"),1.0,0.0); b["model"]=b.model.str.replace("_bin","")
for d in (main,t3,fair,b):
    d["agecond"]=d.age.astype(str)+"_"+np.where(d.exp_years>5,"coupled",np.where(d.age==28,"base","fixed"))
    d["base"]=d.job+"|"+d.tier.astype(str)+"|"+d.gender+"|"+d.marital
main["tier_n"]=main.tier.astype(float).astype(int)
out={}
# Fig1: mean score by tier x model (main) + 95% CI
f1=main.groupby(["tier_n","model"]).score.agg(["mean","std","count"]).reset_index()
f1["se"]=f1["std"]/np.sqrt(f1["count"]); out["fig1"]=f1.to_dict("records")
# Fig2: AIR forest
t3p=pd.concat([main[main.tier_n==3],t3])
def air(d,col,c,B=4000):
    w=d.pivot_table(index=["base","model"],columns="agecond",values=col,aggfunc="mean")
    ks=w.index.get_level_values(0).unique().tolist(); g={k:w.loc[k] for k in ks}
    bs=[]
    for _ in range(B):
        s=pd.concat([g[ks[i]] for i in rng.integers(0,len(ks),len(ks))]); bs.append(s[c].mean()/s["28_base"].mean())
    return [w[c].mean()/w["28_base"].mean()]+list(np.percentile(bs,[2.5,97.5]))
rows=[]
for inst,d,col in [("Score ≥ 50",t3p.assign(p=(t3p.score>=50)*1.0),"p"),("Score ≥ 60",t3p.assign(p=(t3p.score>=60)*1.0),"p"),("Score ≥ 70",t3p.assign(p=(t3p.score>=70)*1.0),"p"),("Binary yes/no",b,"pass"),("Fairness instruction, ≥ 60",fair.assign(p=(fair.score>=60)*1.0),"p")]:
    for c in ["40_fixed","40_coupled"]:
        rows.append([inst,c]+air(d,col,c))
out["fig2"]=rows
# Fig3: tier3 pass rate (>=60) job x model, pooled main+t3
t3p["p"]=(t3p.score>=60)*1.0
out["fig3"]=t3p.pivot_table(index="job",columns="model",values="p").round(3).to_dict()
# Fig4: flip rate and model disagreement by tier (main) ; tier3 pooled
main["p"]=(main.score>=60)*1.0
fl=main.groupby(["model","pid","tier_n"]).p.nunique().reset_index(); fl["f"]=fl.p>1
pm=main.groupby(["pid","tier_n","model"]).p.mean().unstack()
npass=(pm>=0.5).sum(axis=1); dis=((npass>0)&(npass<5)).groupby(level=1).mean()
out["fig4"]={"flip":fl.groupby("tier_n").f.mean().to_dict(),"disagree":dis.to_dict()}
json.dump(out,open("figs/figdata.json","w"),ensure_ascii=False,default=float)
print(json.dumps(out["fig2"],ensure_ascii=False,default=float)); print(out["fig3"]); print(out["fig4"])
