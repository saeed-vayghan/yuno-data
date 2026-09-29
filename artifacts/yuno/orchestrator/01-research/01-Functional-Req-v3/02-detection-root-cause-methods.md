# 02 · Detection & Root-Cause Methods
**Purpose:** Pick the methods that flag meaningful discrepancies (FR1), prove root causes with statistics (FR2), and put $ on each fix (FR4).
**Frame:** lean local build (one command) + AWS scale path, documented only. [scenario.md](../../../architect/00-scenario/scenario.md) is the source of truth; the [decision sheet](00-SUMMARY.md) sets every number below.

| # | Method | What it is | Pros | Cons | Evidence strength | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Category rules + FX adjustment (dbt SQL) | Each settled row gets one category | Same input, same answer | Describes; does not explain | Low | High | High | ✅ Use (FR1 base) |
| 2 | Segment tests + logistic GLM (Python) | Rates with confidence ranges, plus one model | Answers all 5 RCA questions | Needs the full 135k run | High | Med | High | 🥇 Best |
| 3 | Rule-based cause labels | One likely cause per non-exact row | Ops can act on each row | Finds only causes we can describe | Med | Med | High | 🥈 Runner-up |
| 4 | Signature table | Groups non-exact rows by shared traits | Shows "systematic vs random" in plain words | Traits are hand-picked | Med | High | High | ✅ Use (clusters) |
| 5 | HDBSCAN (scikit-learn) | Automatic clustering of non-exact rows | Checks the signature table | Needs tuning; hard to explain | Low | Med | Med | ⚪ Optional (only if time) |
| 6 | Outlier = `large` row | Outliers are the `large` category | Matches the brief's own words | None worth noting | Med | High | High | ✅ Use (outliers) |
| 7 | Excess-loss Pareto | $ lost above the peer rate, per segment | Ranks FR4 actions by $ | Needs a fair peer group | Med | Med | High | ✅ Use (FR4 $) |
| 8 | Robust z-score (MAD) | Distance from the typical gap | One-line reason per row | Most rows are exact, so it divides by 0 | Low | Med | Med | ❌ Reject |
| 9 | Depth-3 decision tree | Finds segments nobody asked about | Readable rules | Unstable; needs a holdout step | Low | Med | Med | ❌ Reject (scale path) |
| 10 | Heavy ML (Isolation Forest, k-means, change-point tools) | Label-free outliers and clusters | Can find unknown patterns | Opaque; extra libraries | Low | Low | Low | ❌ Reject (scale path) |

## Top 2 choices
**🥇 Segment tests + logistic GLM:** This gives the "statistical evidence" the rubric asks for (25 pts).
- **Segment tests** ask "is this gap real?": a rate with a Wilson range, a rate ratio (lift), and a chi² test (Fisher for small groups).
- **The GLM** asks "which factor really drives it?". It splits "PSP_B" from "Argentina".
  - Main effects: PSP, country, size tier, cross-border, weekend, lag bucket.
  - Interactions: PSP × country, country × size.
  - Lag is also an outcome (P2), so its effect shows a link, not a cause.
- **BH-FDR** corrects for testing many segments at once.
- Every finding reads: claim + lift + range + corrected p + $.
  - Example: "PSP_B in AR: 20.5% vs 17% (1.2× [1.1–1.3], q < 0.001)".
- Week-over-week trends: see [07 Alerts](07-alerting-metrics.md).

**🥈 Rule-based cause labels:** Each non-exact row gets one cause the ops team can act on.
- They run on **all non-exact rows**, not only flagged ones. P4 rounding, the PSP_C fee and tax sit below the flag.
- The planted truth in `data/truth` scores the rules (goal: precision and recall ≥ 0.9 per cause). It is never a dbt source.
- This proves the detector works. It does not prove real-world causes.
- The labels feed the $ Pareto for FR4.

## Cause labels (first match wins)
| Order | Label | Rule (what we see in the data) | Planted as |
|---|---|---|---|
| 1 | `fx_timing` | Cross-border; raw Δ ≠ 0, residual ≤ 1 minor unit | X1 |
| 2 | `psp_rounding` | Settled is a multiple of 1,000 units and just under expected | P4 |
| 3 | `partial_capture` | Settled ≈ (n−1)/n of auth | X2 |
| 4 | `psp_fee` | Same fixed $ amount (≥ $1) under, repeated in one PSP | X3 |
| 5 | `tax_recalc` | MX or CO, under by < 2% | X4 |
| 6 | `fraud_hold` | High-risk row, 10–20% under | X5 |
| 7 | `psp_adjustment` | Under by 2–5% | X6 |
| 8 | `tip` | Over-settled (settled > expected) | none: report "tip: ruled out" |
| 9 | `unexplained` | Anything left | — |

- The rules never use the PSP name, so the analysis finds P4 on PSP_D; we don't tell it.
- Slow settlement (P2) is a flag column (`lag_days`), not a cause label.

## Signature table (Q5: systematic vs random)
- Group non-exact rows by: PSP × country × cause label × sign (under or over) × last digits of the settled amount (e.g. ends in 000).
- A group with many rows and one shape = **systematic**. Small scattered groups = **random**.
- HDBSCAN (optional): run it on the same rows, and show one table of how well its clusters match the labels.

## RCA question → test
| Brief question | Test | Output |
|---|---|---|
| Q1 Which countries/currencies? | Rate + Wilson range; chi² | Rate by country |
| Q2 Which PSPs? | PSP vs peers in the same country; GLM PSP × country | Lift per PSP |
| Q3 Size vs likelihood? | Rate by size tier; chi² | Rate by tier |
| Q3 Size vs amount? | Spearman rank test on \|residual USD\| | Rank correlation |
| Q4 Day of week? | Weekend vs weekday rate; chi² | Lift |
| Q4 Settle delay? | Rate by lag bucket; Mann-Whitney on lag | Lift; lag gap in days |
| Q5 Clusters? | Signature table (+ optional HDBSCAN) | Groups with a cause |
| All of the above | BH-FDR | Corrected p (q) |

## $ impact (FR4)
- **Excess loss** = (segment rate − peer rate) × volume × **mean** loss.
- Show the **median** loss beside it, because a few big losses pull the mean up.
- **Saving** = excess loss × a stated reduction %.
- Show gross (under-settled) and net (under − over) $.
- Rank by cause × PSP × country.
- Say "compared with $127k (estimate)". Synthetic data cannot reconcile to a real CFO number.

## Category → brief tier
| Our category | Brief tier | Brief range | Target share* |
|---|---|---|---|
| `exact` + `rounding` | Match exactly | 60–70% | 67% + 1% |
| `fx_tolerance` | Small (0.1–2%) | 15–20% | 18% |
| `meaningful` + `large` | Meaningful (> 2%) | 10–18% | 14% |
| `large` | Large (> 5% or > $20) | 3–5% | 4% |

\* Share of approved + settled rows. `make validate` checks the shares on these brief tiers.

## Definitions
| Term | Rule |
|---|---|
| Rate base | Approved + settled rows only |
| Failed auths | Left out of rates |
| Pending rows | Shown as open exposure (count, $, age) |
| Currency model | Both amounts are in the local currency (MXN, COP, ARS, CLP) |
| Cross-border | `payer_currency = USD`; the PSP converts |
| Money type | Integer minor units; CLP has 0 decimals, the others 2 |
| Expected settle (cross-border) | auth × local_per_usd(settle day) / local_per_usd(auth day) |
| Expected settle (domestic) | auth |
| Residual | settled − expected |
| Residual % | residual / expected |
| Residual USD | Residual at the auth-day rate |
| Cut-offs | Always on \|residual %\| and \|residual USD\| |
| `exact` | Δ = 0 |
| `rounding` | \|Δ\| ≤ 1 minor unit |
| `fx_tolerance` | ≤ 2% and < $20; also holds small domestic gaps |
| `meaningful` | 2–5% and < $20 |
| `large` | > 5% or ≥ $20 |
| Flag | `is_meaningful` = `meaningful` or `large` (about 14%) |
| Brief hint check | 2¢ on $500 → `fx_tolerance`, not flagged; $20 → `large`, flagged |
| Outlier | A `large` row; the dashboard filter defaults to > $50 |
| Weekend | Sat/Sun in the country's local time |
| Peer group | The other PSPs in the same country |
| Lag | Days from auth to settle |
| Config | All cut-offs live in `thresholds.yaml` |
| Sensitivity | The report also shows the flag rate at 1%, 2% and 3% |

Key sources: [Wilson CI (Brown, Cai & DasGupta 2001)](https://projecteuclid.org/journals/statistical-science/volume-16/issue-2/Interval-Estimation-for-a-Binomial-Proportion/10.1214/ss/1009213286.full) · [statsmodels multipletests (fdr_bh)](https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html) · [statsmodels logistic GLM](https://www.statsmodels.org/stable/glm.html) · [scikit-learn HDBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html) · [Adyen currency minor units](https://docs.adyen.com/development-resources/currency-codes)
