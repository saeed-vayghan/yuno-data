# 06 · Monitoring Dashboard
**Purpose:** Pick the localhost dashboard for FR3. It must answer "Which PSP had the worst week last month?" and "Show me all transactions with discrepancies over $50". It also shows the alerts from 07.
**Frame:** lean local build (one command) + AWS scale path, documented only. [scenario.md](../../../architect/00-scenario/scenario.md) is the source of truth; the [decision sheet](00-SUMMARY.md) wins on any detail.

| # | Option | What it is | Pros | Cons | Look & feel | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Streamlit + Plotly | Python web app | Same language as the pipeline; built-in search and sort on tables; `AppTest` for tests | Reruns the whole script (fixed by caching); weak login | High | High | High | 🥇 Best: fastest path to FR3 |
| 2 | Evidence | Pages written in SQL + Markdown | SQL-first, like dbt; polished look | Adds Node; core rewritten Aug 2026 | High | Med | Med | 🥈 Runner-up: a second runtime |
| 3 | Plotly Dash 4 | Python app with callbacks | Easy to test; strong charts | Lots of callback code; styling work | Med | Med | High | ❌ Slower to build |
| 4 | marimo / Jupyter + widgets | Notebook run as an app | SQL cells; quick to write | Weak layout; weak drill-down | Med | High | High | ❌ Fine for exploring only |
| 5 | Observable Framework | JavaScript static site | Best-looking charts | Needs Node; filters and tables built by hand | High | Low | Med | ❌ Too much hand work |
| 6 | Superset / Metabase | Full BI server | User roles; self-serve | Docker + extra DB + login | Med | Low | High | ❌ Not now; scale path only |
| 7 | Grafana | Ops panels + alerting | Great time charts | DuckDB plugin not official; poor row tables | Med | Low | Med | ❌ No transaction drill-down |
| 8 | CLI / static report | Report files, no server | No server; easy to share | No live filters | Med | High | High | ❌ Not the dashboard. The brief allows a CLI, and `recon` covers it (see 05) |

## Top 2 choices

### 🥇 Streamlit + Plotly

**Run**
- `make app` (or `recon dashboard`) opens http://localhost:8501, bound to localhost only.
- If there is no database yet, the app shows "Run `make all` first", not an error trace.

**Data access**
- The app reads the dbt marts, `alerts.jsonl` and `RECOMMENDATIONS.md`.
- It reads them through the shared `core` package. `recon worst-week` and `recon query` use the same functions.
- Each query opens a short read-only DuckDB connection and closes it right away.
- Results are cached (`st.cache_data`), keyed on the database file's modified time.
- So you can rebuild (`make all`) while the app runs. If the file is locked mid-build, the app shows "Rebuilding, retry".
- One test checks that the CLI and the dashboard give the same worst PSP-week.

**Worst-week rules** (one shared `core` function)
- Week = ISO week (Mon–Sun) by auth date.
- A week belongs to the month that holds its Thursday.
- "Last month" = the last full calendar month in the data.
- Ranked by net USD loss. Net = under-settled $ minus over-settled $.
- Gross under-settled $ is shown next to it, with the rate and n.
- PSP-weeks with n < 30 are shown greyed as "low sample" and ranked after the others. The answer is never empty.
- Why 30 and not 50: 30 is for display; 50 is for alert decisions (07).

**Pages (5)**
- **Overview:** KPIs, weekly trend, week-over-week change, and the worst-week card. The card links to Drill-down with filters set.
- **Drill-down:** filter by country, PSP, size tier, cross-border and weekday.
- **Outliers:** `large` rows. Min-$ filter, default 50 (USD at the auth-day rate). Search, sort, masked IDs, a "why flagged" column (> 5% or ≥ $20), and CSV download.
- **Root causes & actions:** cause labels, $ impact, and `RECOMMENDATIONS.md`.
- **Alerts:** rows from `alerts.jsonl`: rule, severity, status vs the last closed week.

**Scale path (docs only)**
- The same marts on StarRocks.
- Superset for self-serve (it has a StarRocks connector).
- The alert evaluator as an Airflow task (see 07).

### 🥈 Evidence
- Its SQL + Markdown pages fit dbt well and look polished.
- It is second because it adds Node next to Python.
- Its core was rewritten in Aug 2026, so there is some churn risk. The new core may build to a container, not a static site (still to check).
- Choose it if the team already uses Node and wants a shareable report.

## Brief-need map

| FR3 need | Page |
|---|---|
| Trends over time | Overview |
| Drill down by segment | Drill-down |
| Outliers to investigate | Outliers |
| Better or worse week-over-week | Overview |
| "Worst PSP week last month?" | Overview (card) |
| "Transactions over $50" | Outliers (default filter) |
| Recommendations in the dashboard | Root causes & actions |
| Alert system | Alerts |

Key sources: [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) · [DuckDB concurrency](https://duckdb.org/docs/stable/connect/concurrency) · [Evidence Core (Aug 2026)](https://evidence.dev/blog/evidence-core) · [Dash 4](https://dash.plotly.com/whats-new-in-dash-4) · [Superset StarRocks](https://superset.apache.org/user-docs/databases/supported/starrocks/) · [Grafana DuckDB plugin](https://github.com/motherduckdb/grafana-duckdb-datasource)
