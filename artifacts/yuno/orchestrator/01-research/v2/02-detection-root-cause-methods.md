# 02 · Detection & Root-Cause Methods
**Purpose:** Pick the methods that flag meaningful discrepancies (FR1), prove root causes with statistics (FR2), and put $ on each fix (FR4).
**Frame:** lean local build (one command) + documented AWS scale path; scenario.md is the source of truth.

| # | Method | What it is | Pros | Cons | Evidence strength | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Tier rules + FX split (dbt SQL) | Each settled row gets one category from `thresholds.yaml` (dbt vars); cross-border rows are tiered on the FX residual | Deterministic; testable with dbt unit tests; rates add to 100%; ARS FX moves do not hide real leaks | Descriptive only; the cut-offs are a choice | Low | High | High | ✅ Use (FR1 base) |
| 2 | Segment tests + binomial GLM (Python) | Rate + Wilson CI per segment; chi² / Fisher; Mann-Whitney / Kruskal / Spearman for size and lag; BH-FDR on all; one logit with main effects + pre-chosen interactions (PSP×country, country×size, weekend, lag bucket) | Answers all 5 RCA questions; adjusted odds ratios split "PSP_B" from "Argentina"; honest about false positives | Sparse cells need merged levels; needs the 135k run for power (500 rows is too small) | High | Med | High | 🥇 Best |
| 3 | Rule-based likely-cause labels | Priority rules, first match wins: rounding, FX timing, partial capture, fee, tax, fraud hold, delay, else `unexplained` | One readable cause per row; scored against planted truth (precision/recall ≥ 0.9 per cause); feeds the $ Pareto | Finds only causes we can describe | High | Med | High | 🥈 Runner-up |
| 4 | Signature table (clusters) | Group flagged rows by PSP × currency pair × tier × residual shape (e.g. always ends in .00) | Answers "systematic vs random" in words a CFO reads | Hand-picked features | Med | High | High | ✅ Use (clusters) |
| 5 | HDBSCAN (scikit-learn) | Density clustering on flagged rows only (Δ%, sign, residue, lag, PSP, pair); noise label = random | No k; no new dependency; checks the signatures | Tuning knob; clusters are hard to explain | Low | Med | Med | ✅ Use (cross-check only; report purity vs rule labels) |
| 6 | Robust z (MAD) + $ rules | Modified z per PSP × currency in SQL; investigate if z > 3.5 or \|Δ USD\| > $50 | One-line reason ("12× normal spread"); matches the ops question "rows over $50" | One metric at a time | Med | High | High | ✅ Use (outliers) |
| 7 | Excess-loss Pareto + bootstrap | $ saving = (segment rate − baseline rate) × volume × median loss, with bootstrap range; gross and net; ranked by cause × PSP × country | Ranks FR4 actions by real $; reconciles to the CFO's $127k; splits recoverable vs avoidable | Depends on a fair baseline | Med | Med | High | ✅ Use (FR4 $) |
| 8 | Depth-3 decision tree | Finds segments the GLM did not pre-specify; confirm on a holdout half | Readable rules; in scikit-learn | Unstable; exploratory only | Low | Med | Med | ✅ Use (discovery only) |
| 9 | Heavy ML (Isolation Forest, pyod, RuleFit, k-means/GMM, ruptures) | Label-free outliers, rule mining, forced clusters, auto change points | Finds unknown patterns | Opaque scores; extra deps; k-means forces every point into a cluster; ~13 weekly points too few for change points | Low | Low | Low | ❌ Reject (scale path only) |

## Top 2 choices
**🥇 Segment tests + binomial GLM:** This gives the "statistical evidence" the rubric asks for (25 pts). Every finding is written as claim + effect size + CI + adjusted p + $, e.g. "PSP_B in AR: 20.5% vs 17% (RR 1.2 [1.1–1.3], q < 0.001)". The GLM adjusts for overlap, so we blame the right thing: PSP, country or both.
**🥈 Rule-based likely-cause labels:** Each flagged row gets a cause the ops team can act on. The planted truth file (`data/truth/labels.csv`, never a dbt source) scores the rules, which proves the detector finds what we planted. The labels also drive the $ Pareto for FR4.

## Definitions
| Term | Rule |
|---|---|
| Denominator / status | Rates use approved + settled rows only. Failed auths are excluded. Pending rows are open exposure (count, $, age); pending > 7 days is an alert. Declined-but-settled = DQ test failure. |
| Currency rounding | Money is integer minor units; the exponent comes from a seed (CLP 0; MXN/COP/ARS 2). \|Δ\| ≤ 1 minor unit or \|Δ USD\| < $0.50 = `rounding`. A ×100 or residue pattern per PSP × pair is a cause, not noise. |
| FX adjustment | Cross-border: expected settle = auth × fx(settle day) / fx(auth day), from the daily FX table in `data/raw`. Residual % = (settled − expected) / expected. Δ USD uses the auth-day rate. |
| Categories | One per row, in order: `exact` (Δ = 0) → `rounding` → `fx_tolerance` (residual ≤ 2%, ≤ $20) → `meaningful` (2–5%, ≤ $20) → `large` (> 5% or > $20). |
| Meaningful (flag) | Flag = `meaningful` or `large`. All cut-offs live in `thresholds.yaml`; the report shows the rate at 1%, 2% and 3% bands. |

Key sources: [Wilson CI (Brown, Cai & DasGupta 2001)](https://projecteuclid.org/journals/statistical-science/volume-16/issue-2/Interval-Estimation-for-a-Binomial-Proportion/10.1214/ss/1009213286.full) · [statsmodels multipletests (fdr_bh)](https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html) · [scikit-learn HDBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html) · [Modified z-score (MAD, 3.5)](https://metricgate.com/docs/robust-z-score-modified/) · [Adyen currency minor units](https://docs.adyen.com/development-resources/currency-codes)
