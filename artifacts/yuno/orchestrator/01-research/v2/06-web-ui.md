# 06 · Monitoring Dashboard
**Purpose:** Pick the localhost dashboard for FR3. It must answer "Which PSP had the worst week last month?" and "Show me all transactions with discrepancies over $50", and show the evaluator's alerts.
**Frame:** lean local build (one command) + documented AWS scale path; scenario.md is the source of truth.

| # | Option | What it is | Pros | Cons | Look & feel | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Streamlit + Plotly | Python app, reads DuckDB 1.4.x LTS read-only | Pure Python like the pipeline; built-in searchable, sortable table; filters in the URL; `AppTest` smoke test | Reruns the whole script (fix with caching); weak auth | High | High | High (logic in dbt) | 🥇 Best: fastest path to FR3 |
| 2 | Evidence (BI as code) | SQL + Markdown pages, static build | SQL-first like dbt; polished look | Adds Node; new Core rewrite (Aug 2026), churn risk | High | Med | Med | 🥈 Runner-up: good, but a second runtime |
| 3 | Plotly Dash 4 | Python app with explicit callbacks | Very testable; strong charts | Callback boilerplate; styling work | Med | Med | High | ❌ Reject: slower to build |
| 4 | marimo app | Reactive notebook run as an app | DuckDB SQL cells; clean | Weak layout and drill-down | Med | High | High | ❌ Reject: fine for EDA only |
| 5 | Observable Framework | JS static site, DuckDB-WASM | Best-looking charts | JS/Node; hand-built filters and tables | High | Low | Med | ❌ Reject: too much hand work |
| 6 | Superset / Metabase | Full BI server | RBAC, self-serve; Superset speaks StarRocks | Docker + metadata DB + login; DuckDB driver is community-only | Med | Low | High | ❌ Reject now: AWS scale path |
| 7 | Grafana | Ops panels + alerting | Great time series and alerts | DuckDB plugin unsigned; poor transaction tables | Med | Low | Med | ❌ Reject: no tx drill-down |
| 8 | CLI / static report (Quarto) | Generated report, no server | Zero server; easy to share | No live filters or search; fails "interact" test | Med | High | High | ❌ Reject as the dashboard (not interactive); kept as the separate `recon` CLI, see 05 |

## Top 2 choices
**🥇 Streamlit + Plotly:** `make app` opens DuckDB 1.4.x LTS read-only and only runs `SELECT`s on dbt marts, so every metric lives in dbt, not the UI. Definitions: worst week = net USD loss per ISO week (skip PSP-weeks with < 30 tx); last month = last full month in the data; over $50 = absolute USD difference at the auth-date FX rate. Scale path (docs only): same marts on StarRocks, Superset 6.x for self-serve, the evaluator as an Airflow task posting to Slack.
Pages: Overview (KPIs, weekly trend, week-over-week change) · Worst PSP-week (last month) · Transactions over $50 (search, sort, masked IDs) · Drill-down (country, PSP, tier, cross-border, weekday) · Alerts (`alerts.jsonl`: severity, owner, NEW/ONGOING/RESOLVED) · Root causes & actions.
**🥈 Evidence:** Its SQL + Markdown pages fit dbt well and look polished. It comes second because it adds Node next to Python, and its core was rewritten a month ago. Choose it if the team already uses Node and wants a static, shareable report.

Key sources: [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) · [Evidence Core (Aug 2026)](https://evidence.dev/blog/evidence-core) · [Dash 4](https://dash.plotly.com/whats-new-in-dash-4) · [Superset StarRocks dialect](https://superset.apache.org/user-docs/databases/supported/starrocks/) · [Grafana DuckDB plugin (unsigned)](https://github.com/motherduckdb/grafana-duckdb-datasource)
