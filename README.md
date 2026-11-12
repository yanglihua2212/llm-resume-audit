# Merit at the Average, Bias at the Margin — replication materials

Code, prompts, synthetic resumes and raw model outputs for an audit of five Chinese large language models
(DeepSeek, Qwen, GLM, Kimi, MiniMax) used as resume screeners. All resumes are synthetic; no personal data is included.

## Contents

| Folder | What it holds |
| --- | --- |
| `code/` | Experiment and analysis scripts (Python 3) |
| `data/` | Raw outputs: one CSV per model and experiment (`data/blind/`: Supplement 3; `data/external/`: Supplement 4) |
| `figures/` | Figures 1–5 of the paper |

### Experiments

| Script | Experiment | Output files |
| --- | --- | --- |
| `experiment.py` | Main experiment: 4 jobs × 5 capability tiers × 2 genders × 2 marital statuses × 5 age–experience conditions = 400 resumes, 3 runs per model | `results_<model>.csv` |
| `experiment_t3.py` | Supplement 1: 320 additional tier-3 (just-meets-requirements) resumes, 3 runs | `results_t3_<model>.csv` |
| `experiment_prompt.py` | Supplement 2: all 400 tier-3 resumes under a binary yes/no prompt (`bin`) and a fairness-instruction prompt (`fair`), 2 runs | `results_p_<bin|fair>_<model>.csv` |
| `experiment_mask.py` | Supplement 3: the 400 tier-3 resumes with date of birth and marital status removed (120 distinct blind texts), 2 runs | `blind/results_mask_<model>.csv` |
| `experiment_ext.py` | Supplement 4 (external validation): two new occupations and a new resume template; 96 original resumes × 2 runs and 64 blind texts × 4 runs | `external/results_ext_<model>.csv` |

The resume texts, job descriptions and prompts are defined inside these scripts, so each resume can be regenerated exactly.

### Analysis

| Script | Purpose |
| --- | --- |
| `analyze_main.py` | Table 3 and Section 5.1: tier means, variance decomposition, score-level effects, model agreement |
| `gm.py` | Section 5.2: pooled tier-3 age effects; gender and marital pass-rate ratios |
| `final_analysis.py` | Sections 5.3–5.5: paired adverse-impact ratios with cluster-bootstrap intervals (Tables 4–5), randomness and model-disagreement measures |
| `prompts.py` | Section 5.5: prompt-variant comparisons and score-level interaction tests |
| `cluster_sensitivity.py` | Robustness: bootstrap and regressions clustered by the 20 tier-3 base texts (Sections 5.3 and 6.3); tier-only variance shares (Section 5.1) |
| `method_eval.py` | Section 6: blind–repeat–route protocol vs. run averaging and counterfactual averaging (Tables 6–7) |
| `ext_eval.py` | Section 6.4: external validation (Table 8) |
| `table7_counts.py` | Table 7: raw counts behind every percentage (distinct blind text × model) |
| `sample_and_inference_checks.py` | Table B1 sample accounting; t-based cluster p-values; bootstrap zero-denominator check |
| `fig5_protocol.py` | Fig. 5 (protocol diagram) |
| `figdata.py`, `plots.py` | Figure data and figures (create an empty `figs/` folder first; run `figdata.py data`, then `plots.py data`) |

Run each analysis script with the path to `data/` as its argument, e.g. `python code/final_analysis.py data`. Bootstrap intervals use fixed random seeds; scripts with different seeds can differ in the second decimal.

## Data dictionary (results CSVs)

| Column | Meaning |
| --- | --- |
| `model` | Model short name (with `_bin` / `_fair` suffix in Supplement 2) |
| `run` | Repeat number |
| `pid` | Resume id (1–400 main; 1001–1320 Supplement 1; 2001+ Supplement 3; 3001–3096 original and 4001–4064 blind resumes in Supplement 4) |
| `job` | Job title (Chinese) |
| `tier` | Capability tier (5 best … 1 worst; `3.2`–`3.5` = Supplement 1 tier-3 base texts) |
| `gender`, `marital`, `age`, `exp_years` | Demographic cues and total years of experience (Supplement 3: `marital` = 遮蔽 and `age` = 0, i.e. not shown) |
| `score` | Parsed score 1–100 (Supplement 2 `bin`: see `raw`) |
| `raw` | Raw model answer; rows starting with `ERROR` were API failures and were retried (one Supplement 3 call to GLM was not recovered; failed Supplement 4 calls were re-run and appear as later rows) |

## Re-running the experiments

1. Create `keys.txt` next to the scripts with two lines: `DEEPSEEK=<your key>` and `QWEN=<your Alibaba Cloud Bailian key>`. This file is git-ignored; never commit keys.
2. Replace `YOUR-BAILIAN-WORKSPACE` in the scripts with your own Bailian endpoint.
3. Run, for example, `python code/experiment.py deepseek`. Runs resume automatically after interruption.

Model outputs are not deterministic and models are updated over time, so re-runs will differ in detail. Original calls ran on 11–13 November 2026.

## Licence

Code: MIT. Data and figures: CC BY 4.0.
