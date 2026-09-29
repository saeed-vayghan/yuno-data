# Ownership

**Rule:** only edit files you own. If you need a change in another owner's file, write it in
`casamarket-recon/HANDOFF.md` under that owner's heading.

Owners: **INFRA** = Architect + Engineer (infra/pipeline) · **BACKEND** = Engineer (backend) · **FRONTEND** = Designer.

| Path | Owner |
|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | INFRA |
| `Makefile`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.gitignore`, `.env.example` | INFRA |
| `README.md` (top level; FRONTEND fills `## Monitoring`), `OWNERSHIP.md`, `docs/**`, `.github/**` | INFRA |
| `config/**`, `contracts/**` | INFRA |
| `dbt/**` | INFRA |
| `src/casarecon/cli.py`, `src/casarecon/cli_query.py` | INFRA |
| `src/casarecon/ports.py` | INFRA |
| `src/casarecon/core/*.py` (config, paths, errors, filters, money, privacy, deps, log, weeks, `__init__`) | INFRA |
| `src/casarecon/core/queries/pipeline_q.py`, `src/casarecon/core/queries/pipeline_q2.py` | INFRA |
| `src/casarecon/generate/**`, `src/casarecon/pipeline/**`, `src/casarecon/validate/**` | INFRA |
| `src/casarecon/adapters/duckdb_store.py`, `src/casarecon/adapters/dbt_runner.py` | INFRA |
| `data/sample/**` | INFRA |
| `tests/conftest.py`, `tests/infra/**` | INFRA |
| `src/casarecon/analysis/**`, `src/casarecon/report/**`, `src/casarecon/alerts/**` | BACKEND |
| `src/casarecon/adapters/files.py`, `src/casarecon/adapters/notify_slack.py` | BACKEND |
| `src/casarecon/core/queries/ui_q.py`, `src/casarecon/core/queries/ui_q_*.py`, `src/casarecon/core/queries/reports_q.py` | BACKEND |
| `reports/**` (generated output) | BACKEND |
| `tests/backend/**` | BACKEND |
| `src/casarecon/dashboard/**` | FRONTEND |
| `.streamlit/**` | FRONTEND |
| `tests/dashboard/**` | FRONTEND |
| `HANDOFF.md` | everyone (append only, under the target owner) |

## Milestones

| Milestone | INFRA | BACKEND | FRONTEND |
|---|---|---|---|
| **M1** walking skeleton (`make smoke` end to end) | `generate` (rows, fx, writer), dbt seeds/staging/intermediate/`fct_transaction_discrepancy`/`mart_psp_weekly`, `pipeline/build.py`, `pipeline_q.py` (connect, db_version, status, psp_weekly, worst_week, query_transactions), `cli_query.py` (query, worst-week), 500-row `fixture_db` in `tests/conftest.py` | `ui_q.py` M1 rows (kpis, weekly_trend, outlier_summary, filter_options), unit tests on the fixture DB | app shell (`app.py`, theme, format, filters, layout, data), Overview (worst-week card, KPIs, trend) + Outliers pages, AppTest smoke |
| **M2** validate, analysis, reports, more pages | `validate/`, remaining marts (`mart_segment_rates`, `mart_outliers`, `mart_cause_summary`), `pipeline_q.py` rows 7-10 (segment_rates, cause_summary, excess_loss, lag_by_country_tier) | `analysis/`, `report/`, `adapters/files.py`, `ui_q.py` rows 15, 16, 18, 19, `reports_q.py` (load_findings, load_recommendations) | Drill-down + Root causes & actions pages, CLI-UI consistency tests |
| **M3** alerts, polish | Docker/CI polish, security tests, README assumptions + fresh-clone walk | `alerts/`, `adapters/notify_slack.py` (off by default), `ui_q.pending`, `reports_q.load_alerts` | Alerts page, accessibility pass, README screenshots/Monitoring section |

## Conventions
- Functional style: pure functions, frozen dataclasses / dicts / DataFrames; side effects only in `adapters/` and `cli.py`.
- Core never imports duckdb, streamlit, typer or requests; it gets adapters via `core/deps.py` (tests pass `store=`).
- Contract names, arguments and columns: `artifacts/yuno/engineer/02-develop-instruction/02-config-and-core.md` (CORE API CONTRACT).
- Files < 150 lines (hard max ~250). Each entry module exposes `main(...)`; the CLI maps errors to exit codes 0/1/2/5.
