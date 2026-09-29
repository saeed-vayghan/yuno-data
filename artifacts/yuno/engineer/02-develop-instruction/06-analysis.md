# 06 · Root-cause analysis (`recon analyze`)

**Goal:** answer the brief's 5 FR2 questions with statistical evidence, score the cause labels against truth, put $ on each segment, and write `reports/findings.json` + `reports/analysis/*.csv`.

**Time box:** 30 min · **Core**

## Inputs
- Files 02 part B (Core query functions), 04 (marts), 05 (gate passes).
- Brief FR2 · decision sheet "Analysis", "Time and worst week" · research 02 · IMPLEMENTATION-PLAN S3.2–S3.4.
- Diagram: `../../architect/03-system-design/04-analysis-reports.svg`.

## Steps

1. **`analysis/stats.py`** (pure functions, unit-tested):
   ```python
   def wilson(k: int, n: int) -> tuple[float, float]           # proportion_confint(k, n, method="wilson")
   def lift(rate: float, peer_rate: float) -> float
   def rate_test(k1, n1, k2, n2) -> float                       # chi2_contingency; Fisher if any expected cell < 5
   def bh(pvals: list[float]) -> list[float]                    # multipletests(method="fdr_bh")[1]
   def spearman(x, y) -> tuple[float, float]
   def mann_whitney(a, b) -> float
   def excess_loss(rate, peer_rate, n, mean_loss) -> float      # max(rate - peer_rate, 0) * n * mean_loss
   ```
   Core `segment_rates()` reuses `wilson` and `lift` from here (core may import `analysis.stats`; `stats` imports nothing from core).

2. **`analysis/rca.py`: one function per brief question.** All rates use settled rows; flag = `is_meaningful`.
   | Q | Brief question | Method | Source | CSV |
   |---|---|---|---|---|
   | Q1 | Countries / currencies | rate + Wilson, each vs rest; chi² | `segment_rates("country")`, `("currency")` | `q1_country.csv` |
   | Q2 | Problem PSPs | PSP × country vs **other PSPs in same country** (peer rule) | `segment_rates("psp_country")`, `excess_loss()` | `q2_psp_country.csv` |
   | Q3 | Size vs likelihood / magnitude | rate by tier (chi²); Spearman on `abs(residual_pct)` vs `amount_usd` (non-exact rows) | `segment_rates("amount_tier")`, fct | `q3_size.csv` |
   | Q4 | Time: weekday, settle delay | weekend vs weekday ratio; rate + mean loss by `lag_bucket`; Mann-Whitney on lag, CO > $300 vs other CO (P2) | `segment_rates("is_weekend")`, `("lag_bucket")`, `lag_by_country_tier()` | `q4_time.csv` |
   | Q5 | Clusters: systematic vs random | signature table (below) | fct | `q5_signatures.csv` |
   - Put **every** p-value from Q1–Q5 into one list and run `bh()` once. Report `q`, not raw p.

3. **Signature table (Q5):** group non-exact settled rows by `psp × country × likely_cause × direction × rounding_flag`.
   - Columns: `n, share_of_cause_in_country, psp_share_of_country_volume, concentration = share_of_cause / psp_share, usd`.
   - Label `systematic` if `n ≥ 30` and `concentration ≥ 1.5`; else `random`.
   - Expected: PSP_D × CL/CO × `psp_rounding`, PSP_C × `psp_fee`, PSP_B × AR × `psp_adjustment` show as systematic.
   - HDBSCAN: optional, only if everything else is done.

4. **`analysis/glm.py`: one logistic GLM** on settled rows:
   ```python
   smf.glm("is_meaningful ~ C(psp) * C(country) + C(amount_tier) + is_cross_border + is_weekend + C(lag_bucket)",
           data=df, family=sm.families.Binomial()).fit()
   ```
   - Output `glm.csv`: term, odds ratio, 95% CI, p.
   - If it fails to converge or warns of perfect separation: drop `PSP × country` cells with n < 200, refit, and log `glm_dropped=[…]` (goes into FINDINGS).

5. **Truth check:** join `likely_cause` with `data/truth/labels.parquet` on `transaction_id`; precision and recall per cause → `truth_check.csv`. Goal ≥ 0.9 each. `tip` must have 0 rows (report "tip: ruled out").

6. **Sensitivity:** flag rate with the `meaningful` cut at 1%, 2%, 3% (`sensitivity_pcts`) → `sensitivity.csv` (compute from `abs(residual_pct)` in Python; do not rebuild dbt).

7. **$ impact:**
   - Per cause × PSP × country from `cause_summary()`: gross under, gross over, net; must sum to the fct total.
   - Excess loss per segment = `(rate − peer_rate) × n × mean_loss_usd`, median loss beside it.
   - The data window is one quarter (3 months), so window $ = `usd_quarter`.
   - One line: total gross under-settled USD "compared with $127k (estimate; synthetic data)".

8. **Worst week (for FINDINGS):** `core.worst_week("last")`: ISO week by auth date, week belongs to the month of its Thursday, "last" = last full calendar month in the data, ranked by `net_usd`, `n < 30` greyed/ranked last.

9. **`analysis/findings.py` → `reports/findings.json`:** shape `{"as_of", "summary", "findings": [...], "not_significant": [...]}`. `findings` is ranked by `usd_quarter` desc and holds only q < 0.05. One item:
   ```json
   {"id": "F1", "key": "psp_b_ar_peer", "headline": "…", "metric": "flag rate", "segment": "PSP_B|AR",
    "n": 6120, "rate": 0.171, "ci": [0.162, 0.181], "peer_rate": 0.136, "lift": 1.26, "q": 0.00001,
    "usd_quarter": 18400.12, "usd_median": 11.2, "share_of_loss": 0.14, "likely_cause": "psp_adjustment",
    "figure": "figures/f1_psp_country_heatmap.png"}
   ```
   Expected keys (at least 4 must pass q < 0.05 on the full run): `psp_b_ar_peer` (P1), `weekend` (P3), `psp_d_rounding` (P4), `co_over_300_lag` (P2; metric = late share, `usd_quarter` = excess loss, may be small, add `"usd_note": "delay, not loss"`), `psp_c_fee_drift` (month 3 vs months 1–2), `cross_border` (brief example), `partial_capture`, `fraud_hold`.
   `"summary"` holds total rows, flag rate, gross/net USD, worst week, truth-check min, GLM dropped terms; `"as_of"` comes from `core.status()` — **no wall-clock time**.

10. **`analysis/figures.py`:** one Plotly chart per finding (country bars + CI, PSP × country heatmap, tier, weekday, lag vs loss, cause Pareto, weekly trend). Save PNG via kaleido; on any error save `.html` and log a warning. File names are fixed (`f1_….png`).

11. **Wire `recon analyze`**: runs steps 2–10; writes `reports/analysis/*.csv`, `reports/findings.json`, `reports/figures/*`.

12. **`tests/test_stats.py`:** Wilson 10/100 ≈ (0.055, 0.174); BH on a known list; Fisher used when a cell < 5; excess loss never negative.

## Done when
| Command | Expected |
|---|---|
| `uv run pytest -q tests/test_stats.py` | passes |
| `uv run recon analyze` (full run) | exit 0 |
| `ls reports/analysis/` | `q1_country.csv q2_psp_country.csv q3_size.csv q4_time.csv q5_signatures.csv glm.csv truth_check.csv sensitivity.csv` |
| `uv run python -c "import json; f=json.load(open('reports/findings.json'))['findings']; ok=[x for x in f if x['q']<0.05 and all(x[k] is not None for k in ['n','rate','ci','peer_rate','lift','q','usd_quarter'])]; print(len(ok))"` | ≥ 4 |
| `uv run python -c "import pandas as p; print(p.read_csv('reports/analysis/truth_check.csv')[['precision','recall']].min().min())"` | ≥ 0.9 |
| each `figure` path in findings.json exists under `reports/` | true |

## Serves
FR2 (all 5 questions, "immediately understand which factors are driving") · Done "≥ 3–4 patterns backed by data" · RCA 25 (Wilson, chi²/Fisher, BH, GLM, signatures, truth check, $ Pareto) · Deliverable 3.

## Pitfalls
- **Peer rule:** PSP_B × AR is compared with the other PSPs **in AR**, not with all rows; otherwise Argentina's own level hides or inflates P1.
- **P1 is in points:** "+3.5 pts", not "+3.5%".
- **P2 is a lag pattern**, not a flag-rate pattern. Test lag (Mann-Whitney + late share), not `is_meaningful`.
- **Lag is also an outcome** (P2); in the GLM its effect is a link, not a cause. Say so.
- **Smoke run:** at 500 rows most tests are not significant. `analyze` must still exit 0; the "≥ 4 findings" check only applies to the full run.
- `excess_loss` with `rate < peer_rate` is 0, not negative.
- `findings.json` must be byte-stable: sort keys (`json.dump(..., sort_keys=True, indent=2)`), round floats (6 dp), no timestamps. Its hash is the idempotency check (file 10).
- kaleido needs Chrome in some versions; never let PNG export fail the command.

## Hand-off
- File 07 renders FINDINGS.md / RECOMMENDATIONS.md only from `findings.json` + CSVs.
- File 08 reuses `stats.bh`, `stats.wilson`.
- Frontend: `load_findings()` returns `findings.json` items; figures are in `reports/figures/`.
