# v2 Summary: Final Picks (CasaMarket)

**Source of truth:** [scenario.md](../../../architect/00-scenario/scenario.md).
**Frame:** lean local build (one command) + documented AWS scale path.
Full stack: [01 reference stack](01-discrepancy-analysis-system.md).

| # | Topic | Serves | 🥇 Best | 🥈 Runner-up |
|---|---|---|---|---|
| 01 | [Discrepancy analysis system](01-discrepancy-analysis-system.md) | FR1 | Python 3.12 + uv, DuckDB 1.4.x LTS, dbt-core 1.12 + dbt-duckdb 1.11, Makefile | Plain Python + polars + Parquet (no dbt skills) |
| 02 | [Detection & root-cause methods](02-detection-root-cause-methods.md) | FR1, FR2, FR4 | Segment tests + logistic GLM (Wilson CIs, chi²/Fisher, BH-FDR) | Rule-based cause labels scored against planted truth |
| 04 | [Synthetic data](04-synthetic-data-tools.md) | Test data | Custom seeded generator from a YAML spec | Same generator on Polars (scale path) |
| 05 | [CLI tool](05-cli-tool.md) | FR3 (CLI reports) + one-command run | Typer `recon`, thin shell over the shared core | Click (fallback) |
| 06 | [Monitoring dashboard](06-web-ui.md) | FR3 | Streamlit + Plotly, read-only DuckDB, `make app` | Evidence (BI as code) |
| 07 | [Alert system & metrics](07-alerting-metrics.md) | FR3 | dbt tests + YAML rules run by a Python evaluator, `make alerts` → `alerts.jsonl` + report | Grafana alerting (scale path) |

## Key decisions

| Topic | Decision |
|---|---|
| Categories | exact → rounding → fx_tolerance (≤ 2%, ≤ $20) → meaningful (2–5%, ≤ $20) → large (> 5% or > $20); flag = meaningful + large |
| FX | Cross-border judged on the residual after the FX move; daily FX table in `data/raw` |
| Money | Integer minor units; CLP 0 decimals |
| Data | 135k rows by default, `--rows 500` smoke run; shares 65 / 18 / 13 / 4; truth labels kept separate; `make validate` gate |
| Alerts | Peer rule + change rule; minimum sample 50, else "insufficient data" |
| Dashboard | Answers "worst PSP week last month" (net USD loss, min 30 txns) and "transactions over $50" |
| Run | `make` targets call the CLI: `recon generate \| build \| validate \| analyze \| report \| query \| worst-week \| alerts check \| dashboard \| all` |

**Removed as not needed by scenario.md:** 03 stream vs batch.
