# CasaMarket settlement reconciliation (`recon`)

Finds and explains gaps between authorized and settled amounts across PSPs, countries and currencies.
Pipeline: synthetic data -> dbt/DuckDB -> analysis + alerts + reports -> CLI and Streamlit dashboard.

## Quick start
```bash
uv sync                 # Python 3.12 env from uv.lock
make smoke              # recon all --rows 500 (~5 s)
make all                # full run (135k rows)
make test               # pytest (builds a 500-row fixture DB in a tmp dir)
make app                # dashboard on http://localhost:8501
uv run recon worst-week --month last
uv run recon query --min-usd 50 --format csv
```

## Docker
`docker compose up` builds the image, runs `recon all`, then serves the dashboard on port 8501
(`recon dashboard --host 0.0.0.0` inside the container). `data/` and `reports/` are mounted volumes.

## Layout
See `OWNERSHIP.md` for every path and its owner. Each major folder has a short README.

## Exit codes
0 ok · 1 error (e.g. no DB yet: "Run `make all` first") · 2 bad usage/filter · 5 data quality (a dbt test failed; the last good DB is kept).

## Milestones
- **M1 walking skeleton:** generate -> build -> worst-week/query -> dashboard shell, end to end on `make smoke`.
  `recon all` = generate -> build -> validate -> analyze -> alerts -> report; a step not built yet stops it with exit 1.
- **M2:** validate gate, analysis, reports, more dashboard pages.
- **M3:** alerts + Alerts page, Docker/CI polish, README assumptions.

## Assumptions
- "Over $50" = FX-adjusted residual in USD (auth-day rate) strictly > 50. "Last month" = last full calendar month
  in the data (as of = latest timestamp in the data, never the wall clock); a week belongs to the month of its Thursday.
- Worst week = highest net USD loss (under - over) per PSP x ISO week; weeks under 30 settled rows rank last ("low sample").
- Dependency pins: duckdb 1.4.x, dbt-core 1.12.x, dbt-duckdb 1.11.x resolved together (no fallback needed).
