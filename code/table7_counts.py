# Table 7: raw counts at one unit (distinct blind tier-3 text x model)
# Usage: python table7_counts.py data
# Table 7 reconciliation: raw counts at one consistent unit (distinct blind text x model)
import glob, os, sys, numpy as np, pandas as pd
D = sys.argv[1]; CUT = 60
def load(p):
    fs = sorted(glob.glob(os.path.join(D, p)) + glob.glob(os.path.join(D, "blind", p)))
    if p.startswith("results_[!tp]"): fs = [f for f in fs if "mask" not in f]
    d = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype={"tier": str, "raw": str}) for f in fs])
    d = d[~d.raw.fillna("").str.startswith("ERROR")].drop_duplicates(["model", "run", "pid"], keep="last")
    d["score"] = pd.to_numeric(d.score, errors="coerce"); return d[(d.score >= 1) & (d.score <= 100)]
b = load("results_mask_*.csv")
pv = b.pivot_table(index=["model", "pid"], columns="run", values="score")
print("blind text-model pairs:", len(pv), "with both runs:", pv.dropna().shape[0])
pv = pv.dropna()
pv["m"] = pv[[1, 2]].mean(axis=1); pv["flip"] = (pv[1] >= CUT) != (pv[2] >= CUT)
main = load("results_[!tp]*.csv"); m12 = main[main.run <= 2].groupby(["model", "pid", "tier"]).score.mean().reset_index()
rows = []
for d in [0, 2, 4, 6, 8]:
    r = (pv.m - CUT).abs() < d
    N = len(pv); F = int(pv.flip.sum()); Rn = int(r.sum()); FR = int((pv.flip & r).sum()); A = N - Rn; FA = F - FR
    other = ((m12[m12.tier != "3"].score - CUT).abs() < d).mean()
    load_all = 0.2 * Rn / N + 0.8 * other
    rows.append([d, N, F, Rn, FR, A, FA, Rn / N, FA / A if A else np.nan, FR / F, other, load_all])
t = pd.DataFrame(rows, columns=["delta", "N", "flips", "routed", "flips_routed", "auto", "flips_auto", "routed_share", "flip_rate_auto", "flips_caught", "other_tiers_routed", "load_all"])
pd.set_option("display.width", 200); print(t.round(4).to_string(index=False))
# check identity
t["check"] = (t.flips / t.N) * (1 - t.flips_caught) / (1 - t.routed_share)
print(t[["delta", "flip_rate_auto", "check"]].round(4).to_string(index=False))
