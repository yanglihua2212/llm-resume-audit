# Table 7 with original-resume weights (5-year blind text = 3 x weight of 12/17-year texts)
# usage: python table7_weighted.py data/blind/
import glob, sys, pandas as pd, numpy as np
D=sys.argv[1] if len(sys.argv)>1 else "data/blind/"
if not D.endswith("/"): D+="/"
b=pd.concat([pd.read_csv(f,encoding="utf-8-sig",dtype={"tier":str,"raw":str}) for f in glob.glob(D+"*.csv")])
b=b[~b.raw.fillna("").str.startswith("ERROR")].drop_duplicates(["model","run","pid"],keep="last")
b["score"]=pd.to_numeric(b.score,errors="coerce"); b=b[(b.score>=1)&(b.score<=100)]
pv=b.pivot_table(index=["model","pid","exp_years"],columns="run",values="score").dropna().reset_index()
pv["m"]=pv[[1,2]].mean(axis=1); pv["flip"]=(pv[1]>=60)!=(pv[2]>=60)
pv["w"]=np.where(pv.exp_years==5,3,1)
print("N",len(pv)); print("flip unweighted %.4f weighted %.4f"%(pv.flip.mean(),np.average(pv.flip,weights=pv.w)))
for d in [0,2,4,6,8]:
    r=(pv.m-60).abs()<d; w=pv.w
    rs=np.average(r,weights=w); fa=(w*(pv.flip&~r)).sum()/(w*~r).sum() if (~r).any() else 0
    fc=(w*(pv.flip&r)).sum()/(w*pv.flip).sum()
    byexp={e:round(r[pv.exp_years==e].mean(),3) for e in [5,12,17]}
    print(d,"routed_w %.5f load %.5f autoflip_w %.5f caught_w %.5f"%(rs,0.2*rs,fa,fc),byexp)
