"""Final analysis: main experiment + tier-3 supplement + prompt variants.
Usage: python3 final_analysis.py <folder with results_*.csv>"""
import sys, glob, os
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
D = sys.argv[1]
rng = np.random.default_rng(2026)

def load(pattern):
    fs = sorted(glob.glob(os.path.join(D, pattern)))
    if not fs: return None
    d = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype={"score": "float", "tier": "str"}) for f in fs])
    keep_bin = "p_bin" in pattern
    if keep_bin:
        d = d[~d.raw.astype(str).str.startswith("ERROR")].copy()
    else:
        d = d[d.score.notna()].copy()
    d = d.drop_duplicates(["model", "run", "pid"], keep="last")
    d["agecond"] = d.age.astype(str) + "_" + np.where(d.exp_years > 5, "coupled", np.where(d.age == 28, "base", "fixed"))
    d["base"] = d.job + "|" + d.tier.astype(str) + "|" + d.gender + "|" + d.marital
    return d

main = load("results_[!tp]*.csv")
t3 = load("results_t3_*.csv")
pb = load("results_p_bin_*.csv")
pf = load("results_p_fair_*.csv")
print("main rows", len(main), "| t3 rows", 0 if t3 is None else len(t3),
      "| bin rows", 0 if pb is None else len(pb), "| fair rows", 0 if pf is None else len(pf))
main = main[(main.score >= 1) & (main.score <= 100)]
main["tier_n"] = main.tier.astype(float).astype(int)

def paired_air(d, outcome, conds=("35_fixed", "35_coupled", "40_fixed", "40_coupled"), B=5000):
    w = d.pivot_table(index=["base", "model"], columns="agecond", values=outcome, aggfunc="mean")
    bases = w.index.get_level_values(0).unique().tolist()
    groups = {b: w.loc[b] for b in bases}
    res = []
    for c in conds:
        est_r = w[c].mean() / w["28_base"].mean(); est_d = (w[c] - w["28_base"]).mean()
        rs, ds = [], []
        for _ in range(B):
            sel = pd.concat([groups[bases[i]] for i in rng.integers(0, len(bases), len(bases))])
            rs.append(sel[c].mean() / sel["28_base"].mean()); ds.append((sel[c] - sel["28_base"]).mean())
        res.append([c, round(w["28_base"].mean(), 3), round(w[c].mean(), 3), round(est_d, 3),
                    round(np.percentile(ds, 2.5), 3), round(np.percentile(ds, 97.5), 3),
                    round(est_r, 2), round(np.percentile(rs, 2.5), 2), round(np.percentile(rs, 97.5), 2), len(bases)])
    return pd.DataFrame(res, columns=["cond", "p28", "pcond", "diff", "d_lo", "d_hi", "AIR", "lo", "hi", "n_base"])

# ---- tier-3 pool: main tier 3 + supplement ----
t3pool = pd.concat([main[main.tier_n == 3], t3]) if t3 is not None else main[main.tier_n == 3]
t3pool = t3pool[(t3pool.score >= 1) & (t3pool.score <= 100)]
print("\n== Tier-3 paired adverse-impact ratios by cutoff (pooled models) ==")
for cut in [50, 60, 70]:
    t3pool["pass"] = (t3pool.score >= cut).astype(int)
    print(f"-- cutoff {cut}"); print(paired_air(t3pool, "pass").to_string(index=False))
t3pool["pass"] = (t3pool.score >= 60).astype(int)
print("\n== Tier-3 cutoff 60 by model ==")
for m, d in t3pool.groupby("model"):
    r = paired_air(d, "pass", conds=("40_fixed",), B=2000)
    print(m, r[["p28", "pcond", "AIR", "lo", "hi"]].values.tolist())
fl = t3pool.groupby(["model", "pid"])["pass"].nunique()
print("\nTier-3 run-to-run flip rate:", round(100 * (fl > 1).mean(), 1), "%")
pm = t3pool.groupby(["pid", "model"]).score.mean().unstack()
npass = (pm >= 60).sum(axis=1)
print("Tier-3 model disagreement (some pass, some fail):", round(100 * ((npass > 0) & (npass < pm.shape[1])).mean(), 1), "%")

for name, d in [("binary yes/no prompt", pb), ("fairness-instruction prompt", pf)]:
    if d is None: continue
    print(f"\n== {name} ==")
    if name.startswith("binary"):
        raw = d.raw.astype(str).str.strip()
        d["pass"] = np.where(raw.str.startswith("是"), 1, np.where(raw.str.startswith("否") | raw.str.startswith("不") | raw.str.contains("不雇佣"), 0, np.nan))
        d = d[d["pass"].notna()]
    else:
        d = d[(d.score >= 1) & (d.score <= 100)]; d["pass"] = (d.score >= 60).astype(int)
    print("overall pass rate:", round(d["pass"].mean(), 3))
    print(paired_air(d, "pass").to_string(index=False))
