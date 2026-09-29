# Monitoring Dashboard: Decision Brief (v1)

## Question
Which localhost dashboard is modern but minimal for CasaMarket ops, and runs with one command on top of the DuckDB + dbt marts? It must show discrepancy trends, drill-downs (country, PSP, amount tier, cross-border, weekday), outlier transactions, and week-over-week (WoW) change. It must also answer "Which PSP had the worst week last month?" and "Show all transactions with discrepancies over $50". (A) What to build now (lean core). (B) The documented scale path on Yuno's AWS stack. It is not built.

## Debate (🏛️ Jamshid vs ⚡ Kaveh)

1. 🏛️ **Jamshid:** Use Evidence (BI as code). Pages are SQL + Markdown, it reads DuckDB, and it builds to static files. Its SQL-first style matches dbt and moves cleanly to StarRocks later. Reviewers see "analytics engineering", not a Python toy.
2. ⚡ **Kaveh:** Three objections. (1) It adds a second runtime (Node) next to Python + uv + dbt, so `make run` gets two package managers. (2) Evidence Core was relaunched on 26 Aug 2026 with a new CLI, new syntax and a `migrate` command. Building on a one-month-old rewrite is a churn risk. (3) "Show me all tx > $50" needs a searchable, sortable table with free filters. Streamlit's `st.dataframe` has that built in (search, sort, lazy loading since 1.61, row selection).
3. 🏛️ **Jamshid:** I accept 1 and 2. On 3, Evidence has DataTable search too, but I agree it is not better. My condition is the same rule as before: **the UI owns no logic.** Every metric (discrepancy %, flag, tier, WoW delta, worst PSP-week) lives in dbt marts with tests. The app only runs `SELECT`s.
4. ⚡ **Kaveh:** Agreed, and I make it testable. (1) All SQL goes in `dashboard/queries.py` as pure functions `(con, filters) -> DataFrame`. `pytest` runs them against a small fixture DuckDB. (2) The app opens DuckDB with `read_only=True`, so a running dbt build never fights the app for the file lock. (3) One `AppTest` smoke test renders every page. (4) Filters bind to query params (`bind`, 1.55), so a drill-down is a shareable URL.
5. 🏛️ **Jamshid:** What about Superset or Metabase? They are the real ops tools, and Superset has a StarRocks dialect.
6. ⚡ **Kaveh:** They are right for (B) and wrong for (A). Superset needs Docker, a metadata DB and a login. Metabase's DuckDB driver is a community JAR. Grafana's DuckDB plugin is unsigned and needs the Ubuntu image. None of them is "one command" for a reviewer, and the brief says "not an enterprise data warehouse".
7. 🏛️ **Jamshid:** Agreed. Then (B) is Superset 6.x on StarRocks marts for self-serve, plus Grafana (or Airflow + Slack) for alerts. The marts keep the same names, so only the dbt adapter changes.
8. ⚡ **Kaveh:** One more point: money. Amounts are in MXN/COP/ARS/CLP, but "$50" means USD. The mart must carry `discrepancy_usd` from a dated FX table. Never convert in the UI. Also set `client.disableDataExport` off only for the demo, and never show customer IDs unmasked.
9. 🏛️ **Jamshid:** Accepted. Charts use Plotly (`theme="streamlit"`), not the new `st.echarts_chart` (1.64, two weeks old). Recommendations appear as a read-only page rendered from `RECOMMENDATIONS.md`.
10. ⚡ **Kaveh:** **Agreed:** Streamlit + Plotly on read-only DuckDB marts for (A). Superset on StarRocks + alerts for (B). 🏛️ **Jamshid:** Agreed.

## Trade-off table

| Option | Look & feel | Pros | Cons | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|
| **Streamlit 1.64** | Clean, light/dark, themeable | Pure Python; `st.dataframe` search/sort/select; query-param binding; `AppTest`; `uv run` one command | Script reruns (use `st.cache_data`, fragments); weak RBAC | ✅ High | ✅ High (logic in dbt) | **Pick for (A)** |
| Evidence (Core, Aug 2026) | Polished static BI | SQL + Markdown; DuckDB; git-native; static build | Node runtime; fresh rewrite + migration churn | ⚠️ Medium | ⚠️ Churn risk | Strong runner-up |
| Observable Framework | Beautiful, bespoke | Static; DuckDB-WASM; best charts (Plot) | JS/Node; you hand-build filters and tables | ⚠️ Medium | ⚠️ JS skills needed | Skip |
| Plotly Dash 4 | Refreshed, WCAG AA | Explicit callbacks; very testable | Callback boilerplate; styling work | ⚠️ Medium | ✅ | Good, slower |
| Panel 1.9 | Decent (Tabulator) | Strong tables; reactive | Smaller community; more API | ⚠️ Medium | ⚠️ | No edge |
| marimo (`marimo run`) | Clean notebook-app | Reactive; native DuckDB SQL cells; great for Core 2 EDA | App layout and drill-down weaker than Streamlit | ✅ High | ✅ | Use for analysis notebook |
| Shiny for Python 1.7 | Good (bslib) | Fine-grained reactivity | Less known to reviewers | ⚠️ Medium | ✅ | Viable, no edge |
| Metabase / Superset 6.x | Standard BI, dark mode | Self-serve, RBAC, StarRocks dialect (Superset) | Docker + metadata DB + login; DuckDB driver community-only | ❌ Low | ✅ for teams | **Scale path (B)** |
| Grafana | Ops-style panels | Best alerting; time series | DuckDB plugin unsigned; poor tx tables | ❌ Low | ✅ | Alerts in (B) |
| React SPA + FastAPI | Product-grade | Full control | Two stacks, build, CORS; overkill | ❌ Low | ⚠️ | No |
| FastAPI + HTMX | Minimal, crisp | One language; server-side masking | Hand-written templates and charts | ⚠️ Medium | ✅ | No (too slow to build) |
| Static report (Quarto) | Clean document | Zero server; great for findings | No live drill-down or search | ✅ High | ✅ | Optional export of findings |

## Recommendation

**(A) Lean build**
- Libraries: `streamlit==1.64.*`, `plotly`, `duckdb>=1.5,<2` (2.0 is due in Oct 2026; pin it), `pandas`. There is no extra service.
- Command: `make run` = `generate → dbt build (with tests) → uv run streamlit run dashboard/app.py`. `make app` starts the app only. Docker Compose wraps the same command.
- Structure: `dashboard/app.py` (navigation only), `dashboard/pages/*.py`, `dashboard/queries.py` (pure SQL functions), `tests/test_queries.py`, `tests/test_app.py` (`AppTest`).
- Reads only these marts: `fct_transactions_enriched`, `mart_weekly_segment` (week × country × PSP × tier, with rate, $ and WoW delta), `mart_outliers` (rule + z-score/IQR flags with reason), and `mart_root_causes` (test statistics from Core 2).
- Caching: `@st.cache_data` keyed by filter values. The DuckDB connection uses `st.cache_resource(read_only=True)`.

**(B) Scale path (documented, not built)**
- Same dbt models on `dbt-starrocks`; Flink writes auth/settlement events; Airflow runs daily dbt with tests (a failed test means no publish).
- Superset 6.x on StarRocks marts: row-level security by merchant, SSO, no PAN (tokens only, PCI-DSS scope stays out of BI).
- Alerts: Grafana or an Airflow task posts to Slack when WoW discrepancy $ > threshold or a PSP-country rate breaks its control limit.
- Streamlit stays as an internal "investigation" tool, or it retires once Superset covers the drill-downs.

## Layout sketch + design rules

```
┌ Sidebar: CasaMarket · data as of 2026-.. · filters: date range, country, PSP, tier, cross-border ┐
│ 1 Overview    KPI row: discrepancy rate 17.9% (▲1.2pp WoW) │ $ lost (USD) │ flagged tx │ outliers   │
│               Weekly trend line (rate + $), with the 2% "FX noise" band shaded                  │
│ 2 Drill-down  Heatmap PSP × country (rate) → click a cell → weekly bars + top transactions         │
│               "Worst PSP-week last month" card: PSP_B, week 34, $4.1k, 9.8%                       │
│ 3 Outliers    Searchable table: min $ slider (default 50), rule/reason, days to settle, masked ID   │
│ 4 Root causes Top findings with effect size + p-value/CI (weekend, >$300 CO timing, rounding)       │
│ 5 Actions     3–5 recommendations with estimated $ impact (from RECOMMENDATIONS.md)                │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Show USD and local currency, one decimal rule.** Filters and thresholds use `discrepancy_usd` from the mart. The table also shows the local amount and currency.
2. **Every number has context.** Each KPI shows a WoW delta, and each rate shows n. Hide a segment when it has fewer than ~20 transactions, and say why.
3. **Titles are takeaways.** For example: "PSP_B in Argentina settles 3.4pp worse", not "Rate by PSP".
4. **One accent color, semantic red/amber only for flags.** Always add a text label, and make it work in light and dark mode.
5. **Zero-logic, zero-input start.** Sample data is preloaded, and every filter lives in the URL. Show a friendly empty state, never a stack trace or an unmasked ID.

## Open disagreements

| Point | 🏛️ Jamshid | ⚡ Kaveh | Tie-breaker |
|---|---|---|---|
| Findings report format | Evidence/Quarto static report next to the app, a shareable artifact for the CFO | A generated `REPORT.md` plus the Root-causes page is enough; one more tool is not worth it | If time remains after the stretch goals, export a Quarto HTML report; otherwise use Markdown |
| Alerts in (B) | Grafana on StarRocks: ops-native, with a time-series UI | Airflow task + dbt tests + Slack: fewer systems | Use whatever Yuno ops already runs |

## Sources
- [Streamlit 2026 release notes (1.64.0, 15 Sep 2026; lazy `st.dataframe`, `bind`, `disableDataExport`)](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- [Evidence Core announcement (26 Aug 2026)](https://evidence.dev/blog/evidence-core)
- [Observable Framework releases](https://github.com/observablehq/framework/releases)
- [marimo SQL cells (DuckDB)](https://docs.marimo.io/guides/working_with_data/sql/)
- [Panel releases (1.9.x, 2026)](https://github.com/holoviz/panel/releases)
- [What's new in Dash 4](https://dash.plotly.com/whats-new-in-dash-4)
- [Shiny for Python 1.7 (Aug 2026)](https://opensource.posit.co/blog/2026-08-04_shiny-r-1-14-python-1-7/)
- [Apache Superset 6.1 release](https://preset.io/blog/apache-superset-6-1-release/) · [Superset StarRocks dialect](https://superset.apache.org/user-docs/databases/supported/starrocks/)
- [Metabase DuckDB driver (community, MotherDuck)](https://github.com/motherduckdb/metabase_duckdb_driver) · [Grafana DuckDB datasource (unsigned)](https://github.com/motherduckdb/grafana-duckdb-datasource)
- [DuckDB 1.5.6 (28 Sep 2026; 2.0 expected Oct 2026)](https://duckdb.org/2026/09/28/announcing-duckdb-156)
