import json, sys, glob, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
d=json.load(open("figs/figdata.json"))
INK="#0b0b0b"; INK2="#52514e"; GRID="#e4e3df"
C=["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4"]
MODELS=["deepseek","qwen","glm","kimi","minimax"]; MN={"deepseek":"DeepSeek","qwen":"Qwen","glm":"GLM","kimi":"Kimi","minimax":"MiniMax"}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.edgecolor":INK2,"axes.labelcolor":INK,"xtick.color":INK2,"ytick.color":INK2,"axes.spines.top":False,"axes.spines.right":False})
def style(ax):
    ax.grid(axis="y",color=GRID,lw=0.8); ax.set_axisbelow(True)

# Fig 1
f1=pd.DataFrame(d["fig1"]); fig,ax=plt.subplots(figsize=(7,4.2)); style(ax)
for i,m in enumerate(MODELS):
    s=f1[f1.model==m].sort_values("tier_n"); x=s.tier_n+(i-2)*0.09
    ax.errorbar(x,s["mean"],yerr=1.96*s["se"],fmt="o",ms=6,color=C[i],ecolor=C[i],elinewidth=1.2,capsize=0,label=MN[m],mec="white",mew=0.8)
ax.axhline(60,color=INK2,ls="--",lw=1); ax.text(0.55,61.5,"60-point cutoff",color=INK2,fontsize=9)
ax.set_xticks([1,2,3,4,5]); ax.set_xticklabels(["1\nunqualified","2\njust below","3\njust meets","4\ngood","5\nexcellent"])
ax.set_xlabel("Capability tier"); ax.set_ylabel("Mean score (1–100)"); ax.set_ylim(0,100); ax.set_xlim(0.5,5.5)
ax.legend(frameon=False,ncol=5,loc="upper left",bbox_to_anchor=(0,1.12),handletextpad=0.2,columnspacing=1)
fig.tight_layout(); fig.savefig("figs/fig1_scores_by_tier.png",dpi=300); plt.close()

# Fig 2 forest
rows=d["fig2"]; insts=["Score ≥ 50","Score ≥ 60","Score ≥ 70","Binary yes/no","Fairness instruction, ≥ 60"]
fig,ax=plt.subplots(figsize=(7,4.2)); ax.grid(axis="x",color=GRID,lw=0.8); ax.set_axisbelow(True)
for j,(cond,lab,mk,col) in enumerate([("40_fixed","Age 40, 5 yrs experience","o",C[0]),("40_coupled","Age 40, 17 yrs experience","s",C[1])]):
    for k,inst in enumerate(insts):
        r=[x for x in rows if x[0]==inst and x[1]==cond][0]; y=len(insts)-1-k+(0.14 if j==0 else -0.14)
        ax.plot([r[3],r[4]],[y,y],color=col,lw=1.6,solid_capstyle="round")
        ax.plot(r[2],y,marker=mk,ms=7,color=col,mec="white",mew=0.8,ls="none",label=lab if k==0 else None)
ax.axvline(1,color=INK2,lw=1); ax.axvline(0.8,color=INK2,lw=1,ls="--")
ax.text(0.8,len(insts)-0.45,"four-fifths rule",ha="center",color=INK2,fontsize=9); ax.text(1,len(insts)-0.45,"parity",ha="center",color=INK2,fontsize=9)
ax.set_yticks(range(len(insts))); ax.set_yticklabels(insts[::-1]); ax.set_ylim(-0.6,len(insts)-0.2)
ax.set_xlabel("Pass-rate ratio vs. age 28 (5 yrs), tier-3 resumes, 95% CI")
ax.spines["left"].set_visible(False); ax.tick_params(axis="y",length=0)
ax.legend(frameon=False,loc="lower right"); fig.tight_layout(); fig.savefig("figs/fig2_age_air.png",dpi=300); plt.close()

# Fig 3 heatmap
h=pd.DataFrame(d["fig3"]); JN={"数据分析师":"Data analyst","后端开发工程师":"Backend engineer","财务会计":"Accountant","人力资源专员":"HR specialist"}
h=h.loc[["数据分析师","后端开发工程师","财务会计","人力资源专员"],MODELS]
from matplotlib.colors import LinearSegmentedColormap
cm=LinearSegmentedColormap.from_list("b",["#f3f8fe","#cde2fb","#86b6ef","#3987e5","#1c5cab","#0d366b"])
fig,ax=plt.subplots(figsize=(6.4,3.4)); im=ax.imshow(h.values,cmap=cm,vmin=0,vmax=1,aspect="auto")
for i in range(h.shape[0]):
    for j in range(h.shape[1]):
        v=h.values[i,j]; ax.text(j,i,f"{v*100:.0f}%",ha="center",va="center",color="white" if v>0.5 else INK,fontsize=10)
ax.set_xticks(range(5)); ax.set_xticklabels([MN[m] for m in MODELS]); ax.set_yticks(range(4)); ax.set_yticklabels([JN[j] for j in h.index])
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0); ax.set_xticks(np.arange(-.5,5,1),minor=True); ax.set_yticks(np.arange(-.5,4,1),minor=True)
ax.grid(which="minor",color="white",lw=2); ax.tick_params(which="minor",length=0)
cb=fig.colorbar(im,ax=ax,fraction=0.04,pad=0.02); cb.outline.set_visible(False); cb.set_label("Tier-3 pass rate (score ≥ 60)")
cb.ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
fig.tight_layout(); fig.savefig("figs/fig3_job_model_heatmap.png",dpi=300); plt.close()

# Fig 4 randomness & disagreement by tier (main experiment)
f4=d["fig4"]; tiers=[1,2,3,4,5]
fl=[f4["flip"][str(t)] if str(t) in f4["flip"] else f4["flip"][t] for t in tiers]
D=sys.argv[1]
m=pd.concat([pd.read_csv(f,encoding="utf-8-sig",dtype={"score":"float"}) for f in sorted(glob.glob(os.path.join(D,"results_[!tp]*.csv")))])
m=m[m.score.notna()].drop_duplicates(["model","run","pid"],keep="last"); m["t"]=m.tier.astype(float).astype(int)
pm=m.groupby(["pid","t","model"]).score.mean().unstack(); npass=(pm>=60).sum(axis=1)
dis=((npass>0)&(npass<5)).groupby(level=1).mean()
fig,ax=plt.subplots(figsize=(7,3.8)); style(ax); w=0.36; x=np.arange(5)
b1=ax.bar(x-w/2-0.01,fl,w,color=C[0],label="Same model flips pass/fail across 3 runs (resume–model pairs)")
b2=ax.bar(x+w/2+0.01,[dis[t] for t in tiers],w,color=C[1],label="Models disagree on pass/fail (resumes)")
for bars in (b1,b2):
    for bb in bars:
        if bb.get_height()>0.02: ax.text(bb.get_x()+bb.get_width()/2,bb.get_height()+0.01,f"{bb.get_height()*100:.0f}%",ha="center",color=INK,fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(["1\nunqualified","2\njust below","3\njust meets","4\ngood","5\nexcellent"])
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); ax.set_ylim(0,0.5)
ax.set_ylabel("Share"); ax.set_xlabel("Capability tier (main experiment, cutoff 60)")
ax.legend(frameon=False,loc="upper right"); fig.tight_layout(); fig.savefig("figs/fig4_noise_disagreement.png",dpi=300); plt.close()
print("tier3 disagreement main:",dis.to_dict())
