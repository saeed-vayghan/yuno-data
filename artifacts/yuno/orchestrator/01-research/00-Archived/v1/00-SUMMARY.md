# v1 Summary: CasaMarket Settlement Discrepancies

**Source of truth:** [scenario.md](../../../../architect/00-scenario/scenario.md).
**Frame:** lean local build (one command) + documented AWS scale path.
Each brief is an Architect vs Engineer debate.

## Briefs → requirements

| # | Brief | Serves | Pick |
|---|---|---|---|
| 01 | [Discrepancy analysis system](01-discrepancy-analysis-system.md) | FR1 pipeline (backbone for all) | Python 3.12 + uv, DuckDB, dbt-duckdb (raw → staging → marts), Makefile |
| 02 | [Detection & root-cause methods](02-detection-root-cause-methods.md) | FR1 flagging, FR2 RCA, FR4 $ impact | FX-adjusted categories; Wilson CIs, chi-square/Fisher + BH, logistic GLM; cause rules scored against planted truth; $ Pareto |
| 04 | [Synthetic data](04-synthetic-data-tools.md) | Test data spec (10 pts) | Custom seeded generator from a YAML spec; exact bucket quotas; planted patterns; truth file kept separate |
| 05 | [CLI tool](05-cli-tool.md) | FR3 (CLI reports) + one-command run | Typer `recon`, thin shell over the shared core; fixed exit codes |
| 06 | [Monitoring dashboard](06-web-ui.md) | FR3 dashboard | Streamlit + Plotly on DuckDB (read-only); no logic in the UI |
| 07 | [Alert system & metrics](07-alerting-metrics.md) | FR3 alert system | dbt metric marts + Python evaluator: YAML rules (peer rule + change rule, minimum sample) |

**Removed as not needed by scenario.md:**
- **03 stream vs batch:** the brief is batch analysis.

## Decisions that settle conflicts between the briefs

| Topic | Decision |
|---|---|
| DuckDB version | 1.4.x LTS (test with dbt-duckdb 1.11 on a fresh clone) |
| dbt | dbt-core 1.12 + dbt-duckdb 1.11; not dbt v2 yet |
| FX rates | Generated daily table in `data/raw` (source). Seeds: currency exponents, PSP fees, VAT only |
| Thresholds | `thresholds.yaml` (pydantic) → dbt vars |
| Data volume | 135k rows (45k × 3 months) by default; `--rows 500` smoke run (500 is too few to detect a 3–4 pt lift) |
| Alerts | dbt computes metrics; Python evaluator applies rules |
| Run entry | `make` targets call the `recon` CLI (`make all` = `uv run recon all`) |

## Ambiguities in the brief (and how we handle them)

| Ambiguity | Handling |
|---|---|
| "18% mismatch" vs "60–70% exact match" | Follow the data spec; report the realized rates; the >2% share ≈ 17% |
| Buckets overlap | Exclusive buckets over settled rows: exact 65 / small 18 / meaningful 13 / large 4 |
| "+3–4% higher rate" | Read as percentage points (~+3.5 pt) |
| $127k: gross or net | Report under-settlement, over-settlement and net separately |
| "Worst week", "last month" | Net USD loss per ISO week (min 30 transactions); last full month in the data |
| Tips (hospitality) | Shown as "ruled out" for home goods |
