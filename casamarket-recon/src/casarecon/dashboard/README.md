# dashboard

Streamlit monitoring app. Run `make app` (= `uv run recon dashboard`) -> http://localhost:8501.
Entry: `launch.main(port, host)` runs `streamlit run app.py` from the repo root (so `.streamlit/config.toml` applies).

## Layout
| File | Role |
|---|---|
| `app.py` | page config, 5-page `st.navigation`, global sidebar filters |
| `data.py` | **the UI adapter**: the only module that calls `casarecon.core`; `st.cache_data` wrappers keyed on `core.db_version()` |
| `states.py` | no DB / rebuilding / not built yet / error / empty messages; `guarded(page)` and `section(block)` |
| `filters.py` | sidebar widgets <-> `session_state["filters"]` (a core `Filters`) <-> URL; cross-page handoff |
| `widgets.py` | page-only filters (min $, size tier, cross-border, cause) |
| `layout.py` | page header, as-of banner, active-filter line, placeholder page |
| `format.py`, `charts.py`, `cards.py`, `tables.py`, `theme.py` | pure helpers: formatters, Plotly figures, card text, table views, Okabe-Ito colours |
| `views/*.py` | thin page scripts (folder is not `pages/`: Streamlit would also auto-discover that one) (Overview, Drill-down, Outliers, Root causes & actions, Alerts) |

## Rules
- Pages call `data.*` and pure helpers only: no SQL, no `duckdb`, no direct `core` calls.
- A missing core function (`NotImplementedError`) greys out only its block ("not available yet").
- Money: local amounts with ISO code and seed exponent (`CLP 12,345`, `MXN 1,234.56`); USD 2 dp.
- Colour never carries meaning alone: arrows + signs on deltas, words on categories, direct labels on lines.

## Status (M2)
Live: Overview (worst-week card -> Drill-down, KPIs, trends, week-over-week), Drill-down (segment +
page filters, KPIs, flag rate by group with 95% ranges, category mix, table + CSV up to 50k rows),
Outliers (> $N table, CSV, masked customers, core detail panel, "See similar rows" -> Drill-down),
Root causes & actions (loss by cause, drill into cause, findings, PSP × country heatmap, excess loss,
recommendations, FINDINGS.md). Placeholder: Alerts (M3).
Cross-page links replace the filters with exactly what they name (`filters.set_handoff`).

Tests: `uv run pytest -q tests/dashboard` (fake data module, no DB needed).
