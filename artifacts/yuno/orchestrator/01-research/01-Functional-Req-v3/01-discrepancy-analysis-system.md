# 01 · Discrepancy Analysis System
**Purpose:** Pick the end-to-end shape of CasaMarket's discrepancy tool: ingest → enrich → detect → analyze → reports, dashboard and alerts. Serves FR1 and carries FR2–FR4.
**Frame:** lean local build (one command) + AWS scale path, documented only. scenario.md is the source of truth; the [v3 decision sheet](00-SUMMARY.md) wins on any detail.

| # | Option | What it is | Pros | Cons | Simplicity | Maintainability | Scales later | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Python + DuckDB + dbt-duckdb | One DuckDB file; dbt models raw → staging → marts | dbt gives tests, contracts and lineage | dbt project setup; pin dbt 1.x | Med | High | High | 🥇 Best |
| 2 | DuckDB + plain SQL files (no dbt) | Python runs SQL files in order | Fewest moving parts; same SQL | Tests, order and docs by hand | High | Med | Med | 🥈 Runner-up |
| 3 | Python scripts + polars + Parquet | Plain scripts write Parquet files | Few deps; fast | Drops SQL; logic hidden in dataframes | High | Med | Med | ❌ Reject |
| 4 | Notebook only | One Jupyter notebook | Fastest first chart | Hidden state; no tests | High | Low | Low | ❌ Reject (may read marts) |
| 5 | SQLite + SQL | File DB, plain SQL | Zero install | No decimal/time types; community dbt adapter only | High | Med | Low | ❌ Reject |
| 6 | Postgres + dbt-postgres | Server DB in Docker | Mature dbt adapter | A server for 135k rows; not OLAP | Med | Med | Med | ❌ Reject |
| 7 | BI tool (Metabase / Superset) | JVM BI server on top | Rich drill-down | JVM container; third-party DuckDB plugin | Med | Med | High | ❌ Reject (scale path only) |
| 8 | Full lakehouse (Iceberg + StarRocks + Airflow) | Yuno prod stack in Compose | Mirrors prod | Brief: "not an enterprise data warehouse" | Low | High (at scale) | High | ❌ Reject (scale path only) |

## Top 2 choices
**🥇 Python + DuckDB + dbt-duckdb:** One in-process file, so `make all` runs on a laptop in about a minute at 135k rows. The 500-row smoke run takes seconds. dbt adds setup, so Simplicity is Med. But its tests, contracts and lineage are what "good data engineering practices" rewards. The model structure and tests port to Yuno's dbt; some SQL dialect edits are expected.
**🥈 DuckDB + plain SQL files (no dbt):** Same engine and same SQL, with less setup. Second because run order, tests and docs must be written by hand. It wins if the team has no dbt skills.

## Reference stack
| Capability | Lean build (local) | Scale path (AWS / Yuno stack) |
|---|---|---|
| Runtime | Python 3.12 + uv; `uv.lock` committed | Same image on ECS/EKS, built in CI |
| Ingest | Generator writes CSV files to `data/raw` | PSP files → S3 → Iceberg |
| Load | dbt source reads CSV with explicit column types | Iceberg tables with a fixed schema |
| Storage | DuckDB, one `data/casarecon.duckdb` file | S3 + Iceberg (Glue) as the source of truth |
| Serving | Same DuckDB file | StarRocks primary-key tables |
| DuckDB version | 1.4.x LTS | Current LTS, upgraded in CI |
| DuckDB support | 1.4 community support ends 17 Nov 2026 | Move to 1.5.x after testing with dbt-duckdb |
| Transforms | dbt-core 1.12 + dbt-duckdb 1.11 (not dbt v2) | Same models on `dbt-starrocks`; dialect edits expected |
| Build | Full rebuild from raw each run | Incremental Iceberg MERGE / StarRocks upsert |
| Idempotency | Rerun gives the same output; a test checks it | Merge + re-open window for late settlements |
| Money | Integer minor units (CLP has 0 decimals) | Same |
| FX rates | Daily FX table generated into `data/raw` | Daily FX feed (central bank or PSP) |
| FX and flag rules | See [02](02-detection-root-cause-methods.md) and the decision sheet | Same |
| Reference data | dbt seeds: currency exponents, PSP fees, VAT rates | Finance-owned contract tables |
| Config | `thresholds.yaml` + `alerts.yaml`; one small pydantic class | Same files, versioned in Git |
| Data quality | dbt generic + unit tests; contracts on marts | Same + source freshness checks |
| Code tests | pytest on the shared Python core | Same, run in CI |
| Row checks | Bucket shares and pattern checks in `recon validate` | Row counts vs PSP file totals |
| Stats | scipy + statsmodels; HDBSCAN optional | Same package as an Airflow task |
| Reports | `reports/FINDINGS.md` + `reports/figures/` | Same, published each run |
| Recommendations | `reports/RECOMMENDATIONS.md`, 3–5 ranked actions | Same, shared with the client |
| Report numbers | Filled from a findings table; none hand-typed | Same |
| Dashboard | Streamlit + Plotly on localhost; no logic in UI | Superset or Grafana on StarRocks |
| Dashboard DB access | Short read-only connection per query, then closed | StarRocks serves many readers |
| Dashboard cache | Keyed on the DuckDB file's modified time | Built-in BI cache |
| Alerts | 6 YAML rules + small Python evaluator ([07](07-alerting-metrics.md)) | Same evaluator as an Airflow task |
| Alert output | `alerts.jsonl` + report; Slack optional, off by default | SNS → Slack / PagerDuty |
| CLI | Typer `recon`, a thin shell over the shared core | Same commands inside Airflow tasks |
| Command order | generate → build → validate → analyze → alerts → report | Same order as an Airflow DAG |
| Run path 1 | `make all` | MWAA (Airflow) + Cosmos for dbt |
| Run path 2 | `pip install uv && uv run recon all` | Same CLI in the container |
| Run path 3 | `docker compose up` (supported and tested) | Same image, managed by Terraform |
| Make targets | `make all` · `make app` · `make alerts` · `make test` | CI runs `make test` |
| Run time | About a minute at 135k rows; smoke run in seconds | Scheduled daily |
| Test data | Fixed seed; 135k rows default; `--rows 500` smoke run | Real PSP files |
| Run manifest | Seed, versions and row counts per run | Same + OpenLineage |
| Security | Synthetic data; no card numbers; tokenised customer ID | IAM least privilege; KMS on S3 |

**Notes**
- **Why full rebuild:** 135k rows rebuild fast. No merge code means fewer bugs.
- **Open dashboard:** each query closes its connection, so `make all` works while the app runs. If the file is locked mid-build, the app shows "rebuilding, retry".
- **DuckDB 1.4 LTS:** kept for stability; a take-home is a snapshot. Upgrade to 1.5.x once dbt-duckdb is tested on it.
- **Seeds are not cheating:** PSP fees and VAT are contract data a real merchant has. The analysis must still find each pattern from the data, and it is scored against truth labels in `data/truth`.

Key sources: [dbt: upgrading to v2 (DuckDB Beta)](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v2) · [dbt-duckdb on PyPI](https://pypi.org/project/dbt-duckdb/) · [DuckDB release calendar](https://duckdb.org/release_calendar) · [endoflife.date: DuckDB](https://endoflife.date/duckdb) · [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency) · [dbt StarRocks setup (experimental)](https://docs.getdbt.com/docs/local/connect-data-platform/starrocks-setup)
