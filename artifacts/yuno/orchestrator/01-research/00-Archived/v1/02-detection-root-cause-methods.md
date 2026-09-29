# Discrepancy Detection & Root-Cause Methods: Decision Brief (v1)

## Question
CasaMarket (MX/CO/AR/CL, MXN/COP/ARS/CLP, 3–5 PSPs) says 18% of approved transactions settle for a different amount than authorized, about $127k last quarter. How do we (1) define a *meaningful* discrepancy, (2) enrich each transaction, (3) find root causes **with statistical evidence**, (4) split systematic from random, (5) flag outliers, (6) label a likely cause, and (7) put $ on each fix? Frame: a lean local tool with one-command run (brief: "focused analytical tool, not an enterprise data warehouse"), the most correct option inside that limit, and a scale path that is documented but not built.

## Debate (🏛️ Jamshid vs ⚡ Kaveh)
1. 🏛️ **Jamshid:** Use a dual threshold in USD, per-currency FX bands, HDBSCAN for signatures, Isolation Forest for outliers, and RuleFit to find segments like "PSP_B × AR". That covers every analysis question in the brief.
2. ⚡ **Kaveh:** Objections. (1) At 500 rows, PSP × country has ~20 cells of ~25 rows. That is too few to detect a 3–4 pp lift, so the analysis would "find" noise. (2) Isolation Forest, RuleFit (imodels) and pyod add dependencies and give output ops cannot read. Rubric points go to "statistical evidence" and "clarity". (3) Clustering raw numbers mostly finds one big FX-noise blob. (4) Thresholds must respect minor units. CLP has 0 decimals in ISO 4217, but some PSPs send CLP/COP with 2 [1][2]. That is a classic ×100 or rounding bug, and a USD cut-off alone hides it. (5) Testing ~40 segments without correction gives ~2 false "findings" at α = 0.05.
3. 🏛️ **Jamshid:** I accept (1): the generator defaults to real volume (45k/month × 3 months, seeded), with `--n 500` as a smoke test. DuckDB handles this in seconds. I accept (4) and (5) (BH-FDR [5]). On (3), a partial rebuttal: HDBSCAN has been in scikit-learn since 1.3 (now 1.9.x), so it adds no dependency [6]. Its "noise" label is exactly the brief's "random vs systematic". Compromise: rules first, HDBSCAN only as a cross-check.
4. ⚡ **Kaveh:** Agreed, if HDBSCAN runs only on flagged rows, on engineered features (Δ%, sign, rounding residue, lag, PSP, currency pair), and we report cluster purity against the rule labels. K-means and GMM are out: they need k and force every point into a cluster. For segments: a binomial GLM with main effects plus a few interactions chosen in advance (PSP×country, country×size tier, weekend). A depth-3 tree finds segments on one half of the data, and we confirm them on the other half.
5. 🏛️ **Jamshid:** Fine. Outliers are multi-dimensional, though. Isolation Forest sees combinations that a per-segment z-score misses.
6. ⚡ **Kaveh:** A robust z-score (MAD) per PSP × currency segment can be explained in one line ("12× the normal spread for PSP_B-ARS"). It runs as DuckDB SQL (`median`, `mad`), and 3.5 is the published cut-off [7]. The brief's ops question is "show me transactions over $50", which is a rule, not a model. Isolation Forest stays out of the lean build.
7. 🏛️ **Jamshid:** Accepted. For $ impact: report gross and net (over-settlement offsets loss). The saving is the *excess* loss over the baseline rate, with bootstrap CIs. Scale it by loss per transaction, not by raw sums, and reconcile the result to the CFO's $127k.
8. ⚡ **Kaveh:** Agreed. One addition: the generator writes the injected cause to a separate ground-truth file. A test scores the rule labels against it (precision/recall per cause), so we prove the detector finds what we planted. **Agreed on all points except change-point detection (see Open disagreements).**

## Definitions
| Term | Rule | Why |
|---|---|---|
| Population | Rate denominator = `auth_status = approved AND settlement_status = settled` | A failed auth has no settlement, so counting it would dilute the rate |
| Failed auth | Excluded from rates. Kept for the approval-rate context | The brief's statuses mix. Settled-but-failed = **DQ error** (dbt test) |
| Pending | Excluded from rates. Tracked as **open exposure** (count, $ and age). Pending > 7 d = alert | Otherwise late settlements look like "no discrepancy" |
| Δ (local) | `settled_amount − authorized_amount` in **settlement currency minor units** (integers) | Integers avoid float drift. Decimals come from a per-currency seed (CLP 0, COP/MXN/ARS 2) [1][2] |
| Sign | Δ < 0 = **under-settlement** (loss). Δ > 0 = over-settlement | Report both. Net hides offsetting errors |
| Δ% | `Δ / authorized_amount` | Scale-free, so it compares across currencies |
| Δ USD | Δ × daily reference USD rate on the **auth date** (seed table) | One ruler for $ thresholds and Pareto |
| FX-expected settle | For cross-border: `auth_amt × fx(settle_date) / fx(auth_date)` | FX movement is *explained*, not a defect |
| FX residual | `settled − FX-expected`, as % | Flag on the residual, so ARS volatility does not drown the signal |
| Rounding noise | \|Δ\| ≤ 1 minor unit of the settle currency (CLP: 1 peso) | "2 cents on $500 is noise" |
| FX tolerance | Cross-border, \|FX residual\| ≤ band (default 2% per brief; per-currency value in a seed) | The brief: legitimate FX noise is typically < 2% |
| **Meaningful** | Not noise AND (\|Δ%\| > 2% after FX adjustment OR \|Δ USD\| ≥ $5) AND \|Δ USD\| ≥ $0.50 floor | Dual threshold: % catches small tickets, $ catches big ones, the floor kills cents |
| **Large / outlier** | \|Δ%\| > 5% OR \|Δ USD\| > $20 (brief tiers). **Investigate** = \|Δ USD\| > $50 OR robust z > 3.5 | Matches the brief's tiers and ops question |
| Category | `exact · rounding · fx_tolerance · meaningful · large` (one per row, mutually exclusive) | Rates add up to 100% and map to the brief's 60–70 / 15–20 / 10–18 / 3–5% mix |

**Enrichment fields** (`fct_transactions`): amount_usd, size tier ($10–50 / 50–200 / 200+), country, currency, currency_pair, is_cross_border, PSP, product category, auth_ts, settle_ts, settle_lag_days (+ bucket 1–3/4–7/7+), auth_dow, is_weekend, auth_week, Δ local/USD/%, sign, category, settle/auth ratio, rounding residue (settled mod 10^k per currency), implied FX vs reference FX, FX residual %, robust_z, is_investigate, likely_cause, cluster_id. The customer ID is a pseudonymous key. No PAN ever enters the data (PCI-DSS).

## Trade-off table
| Method | Purpose | Pros | Cons | Evidence strength | Simplicity | Verdict |
|---|---|---|---|---|---|---|
| SQL aggregates in DuckDB (dbt marts) | Rates by country/PSP/tier/dow/lag, Pareto | Fast, testable, readable, no Python needed | No inference by itself | Descriptive | ★★★★★ | **Use** (foundation) |
| Rate + **Wilson CI** (statsmodels) | "Rate for PSP_B-AR = 14% [11–17%]" | Correct coverage at small n. Wald is not [3][4] | One interval per segment | Medium | ★★★★★ | **Use** |
| Rate ratio / lift + bootstrap CI | "Cross-border 3.2× domestic [2.6–3.9]" | Matches the brief's example phrasing | Resampling cost (trivial here) | Medium–high | ★★★★ | **Use** |
| Chi-square / Fisher exact (scipy) | Is the rate independent of PSP, country, dow? | Standard. Fisher for cells < 5 | Tests "any difference", not which one | Medium | ★★★★★ | **Use**, then post-hoc per cell |
| Mann-Whitney / Kruskal-Wallis + Spearman | Magnitude by group; size vs \|Δ%\|; lag vs \|Δ\| | No normality assumption. Heavy tails are OK | Only ranks. Report medians + effect size too | Medium | ★★★★★ | **Use** |
| **Benjamini-Hochberg FDR** | Many segment tests | One line (`multipletests`) [5] | Slightly less power | Makes all the above credible | ★★★★★ | **Use** (mandatory) |
| Binomial GLM (logit) + chosen interactions | Adjusted effects: is it PSP_B, or AR, or PSP_B × AR? | Separates confounders. Odds ratios with CIs | Sparse cells blow up (use volume, merge rare levels) | **High** | ★★★★ | **Use** (key evidence) |
| Shallow decision tree (depth ≤ 3, min_leaf ≥ 50) | Find segments the GLM did not pre-specify | Readable rules, in sklearn | Unstable, so confirm on a holdout | Exploratory | ★★★★ | **Use** as discovery only |
| RuleFit / imodels | Rule discovery | Rich rules | Extra dependency, many overlapping rules | Exploratory | ★★ | Reject (lean) |
| **Rule-based cause labels** | Likely cause per row | Deterministic, explainable, testable against ground truth | Only finds causes we can describe | High (checked vs injected truth) | ★★★★ | **Use** (primary) |
| HDBSCAN (sklearn ≥ 1.3) | Signatures; noise = random | No k. Finds varying density. Labels noise [6] | Needs scaled features. min_cluster_size is a tuning knob | Supporting | ★★★ | **Use** as a cross-check on flagged rows |
| k-means / GMM | Clustering | Familiar | Needs k, forces every point into a cluster, dislikes odd shapes | Weak | ★★★ | Reject |
| DBSCAN | Clustering | Labels noise | One eps does not fit mixed densities | Weak | ★★★ | Reject (HDBSCAN supersedes it) |
| Robust z (MAD) per segment | Outliers | SQL-able, explainable, 3.5 cut-off [7] | Univariate | Medium | ★★★★★ | **Use** + $ rules |
| Isolation Forest / pyod | Multi-dim outliers | Label-free | Opaque score. pyod is an extra dependency | Weak for ops | ★★ | Reject (lean). Scale path only |
| Weekly p-chart (Wilson bands) + before/after test | "Better or worse week over week?" | Simple, readable, SQL + one CI | No automatic break dating | Medium | ★★★★★ | **Use** |
| ruptures (change points) | Date the break (e.g. the migration) | Finds unknown breaks | ~13 weekly points. Extra dependency | Weak at this n | ★★ | Open (see below) |

## Likely-cause rules
Rules run in priority order. The first match wins. No match = `unexplained`, which is itself a finding. Sanity check on thresholds: the generator's ground-truth file must give precision and recall ≥ 0.9 per cause.

| Cause | Signature | Test (evidence) |
|---|---|---|
| Rounding | \|Δ\| ≤ 1–100 minor units. The settled residue is concentrated (e.g. CLP/COP ending 00, or ×100 / ÷100 scale) for one PSP × currency pair | Chi-square test of residue uniformity per PSP × pair vs the other PSPs. Excess rate with Wilson CI |
| FX timing | Cross-border. \|FX residual\| small (≤ 0.3%) while \|Δ%\| ≤ ~3%. The sign follows the FX move | Spearman(Δ%, FX drift) > 0 on cross-border rows. Rate ratio cross-border vs domestic |
| Partial capture | Under-settlement. Ratio ≈ a clean fraction (½, ⅔, ¾, 0.8, 0.9 ± 0.1%) or auth − one line item | Spike test: share of ratios on clean fractions vs a uniform expectation (binomial) |
| Fee deduction | Under-settlement. Δ ≈ −(fixed + p% × amount), stable per PSP | OLS of Δ on amount per PSP: high R², stable intercept/slope. Kruskal on Δ% across PSPs |
| Tax recalculation | \|Δ\| / amount ≈ the country VAT share (MX 16%, CO 19%, AR 21%, CL 19% → rate/(1+rate)) on part or all of the amount | Share of rows within ± 0.5 pp of the VAT shares vs other countries |
| Fraud / risk hold | Under-settlement, irregular %, long lag (> 5 d), not a clean fraction | Mann-Whitney of lag for this group vs the rest. Association with the lag bucket |
| Timing / settlement delay | Any category with lag ≥ 4 d or > 7 d (outliers), e.g. CO > $300 | GLM term for lag bucket. Kruskal of \|Δ\| by lag bucket |
| Unexplained | None of the above | Size and $ reported. Top candidates for manual review |

## Recommendation
**(A) Lean build (keep the baseline: Python 3.12 + uv, DuckDB 1.4.x LTS [8], dbt-duckdb [9], Makefile, optional Docker)**
- `make run` = generate (seeded, default 3 months × 45k, `--n 500` smoke test) → `dbt build` (seeds: currency decimals, FX rates, thresholds, VAT; raw → staging → `fct_transactions` → marts; tests: unique/not-null ids, accepted statuses, settle ≥ auth time, amounts > 0, category sums to 100%) → `analysis/` Python → `reports/` (CSV + PNG + `findings.md`) → dashboard on localhost.
- Detection, enrichment, MAD z, cause rules, Pareto and the weekly p-chart are all **SQL in dbt**. Python does only the inference: Wilson, bootstrap ratio CIs, chi-square/Fisher, Mann-Whitney/Kruskal, GLM, the depth-3 tree, HDBSCAN, BH-FDR.
- Each finding is written as: claim + effect size + CI + adjusted p + $. Example: "PSP_B-ARS meaningful rate 17.8% vs 13.9% (RR 1.28 [1.15–1.42], q < 0.001), $X/quarter".
- $ impact: Pareto of gross under-settlement by cause × PSP × country. Savings per recommendation = (segment rate − baseline rate) × volume × median loss, with a bootstrap range. Annualize from loss per transaction at 45k/month. Recoverable causes (rounding, fees, PSP errors) are split from avoidable ones (FX locking, capture practice). Reconcile to the $127k.

**(B) Scale path (documented only)**
- Flink joins auth events and settlement records by transaction ID in event time, with state TTL ≥ max settle lag + late settlements to a side output. It computes Δ and the category in-stream and writes to StarRocks.
- The same dbt models run on StarRocks (dbt-starrocks). The seeds become reference tables, and FX rates come from a daily feed. Airflow runs settlement-file ingestion → `dbt build` → a stats job (ECS/Batch) → alerts.
- Alerts: the weekly p-chart breach per PSP × country, and a daily MAD/$50 outlier list. dbt test failures page the data owner. Isolation Forest and change-point detection are added only once there is ≥ 1 year of history.
- PCI-DSS: tokens only, no PAN. Pseudonymous customer ID. Least-privilege IAM. The analysis marts hold no cardholder data.

## Key practices
- Money is stored as integer minor units with per-currency decimals from a seed. Never use floats for Δ.
- Keep one definition of "meaningful" in config, and show sensitivity: the rate at 1%, 2% and 3% bands.
- Denominators are explicit: approved + settled only. Pending is shown as open exposure.
- Every rate gets a Wilson CI. Every family of tests gets BH-FDR. Report effect sizes, not just p-values.
- Adjust before you blame: GLM odds ratios decide "PSP_B vs Argentina vs both".
- Tree segments found on one half of the data must be confirmed on the other half.
- The planted ground truth scores the detector. The pipeline never reads it.
- Scale $ by loss per transaction, report gross and net, and reconcile to the CFO's number.

## Open disagreements
- **Change-point detection:** 🏛️ Jamshid wants `ruptures` to date the break automatically (the brief mentions a recent platform migration). ⚡ Kaveh says ~13 weekly points is too few for a reliable automatic break, and the migration date is known, so a before/after test (two-proportion + Wilson) plus the p-chart answers it with no new dependency. *Tie-breaker:* ship the p-chart + before/after test. Try `ruptures` on daily rates only if the time box allows, and keep it only if it agrees with the known date.

## Sources
1. ISO 4217 currency codes and minor units (CLP 0, COP 2). https://en.wikipedia.org/wiki/ISO_4217
2. Adyen Docs, *Currency codes and minor units* (CLP/COP use 2 minor units in Adyen, unlike ISO). https://docs.adyen.com/development-resources/currency-codes
3. Brown, Cai & DasGupta, *Interval Estimation for a Binomial Proportion*, Statistical Science 16(2), 2001 (Wilson recommended over Wald). https://projecteuclid.org/journals/statistical-science/volume-16/issue-2/Interval-Estimation-for-a-Binomial-Proportion/10.1214/ss/1009213286.full
4. statsmodels 0.14.6, `proportion_confint` (method="wilson"). https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html
5. statsmodels, `multipletests` (method="fdr_bh"). https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html
6. scikit-learn 1.9.1, `sklearn.cluster.HDBSCAN` (added in 1.3). https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html
7. Iglewicz & Hoaglin modified z-score (MAD, cut-off 3.5). https://metricgate.com/docs/robust-z-score-modified/
8. DuckDB, *Announcing DuckDB 1.4.5 LTS* (Jun 2026). https://duckdb.org/2026/06/17/announcing-duckdb-145
9. dbt-duckdb releases. https://github.com/duckdb/dbt-duckdb/releases
