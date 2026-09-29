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

## Status (M1)
Live: shell, filters, theme, states, Overview (worst-week card, KPIs, weekly trend charts), Outliers
(> $N table, CSV, masked customers, why-flagged panel). Placeholders: Drill-down, Root causes (M2), Alerts (M3).

Tests: `uv run pytest -q tests/dashboard` (fake data module, no DB needed).
