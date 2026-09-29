# 01 · Discrepancy Analysis System
**Purpose:** Pick the end-to-end shape (ingest → enrich → detect → analyze → dashboard + alerts) of CasaMarket's discrepancy tool (serves FR1; backbone for FR2–FR4).
**Frame:** lean local build (one command) + documented AWS scale path; scenario.md is the source of truth.

| # | Option | What it is | Pros | Cons | Simplicity | Maintainability | Scales later | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Python + DuckDB + dbt-duckdb | Python 3.12 + uv, one DuckDB file, dbt models raw → staging → marts, Python stats | In-process; dbt gives DAG, tests, contracts, docs for free; SQL ports to Yuno's dbt | dbt setup; must pin dbt 1.x (v2 DuckDB is Beta) | High | High | High | 🥇 Best |
| 2 | Python scripts + polars + Parquet | Plain scripts write Parquet files | Fewest deps; fast | Re-builds DAG, tests, lineage by hand; logic hidden in dataframes | High | Med | Med | 🥈 Runner-up |
| 3 | Notebook only | One Jupyter notebook | Fastest to first chart | Hidden state; no tests; weak pipeline story | High | Low | Low | ❌ Reject (may read marts) |
| 4 | SQLite + SQL | File DB, plain SQL | Zero install | Weak analytics SQL; no first-class dbt adapter; poor money/time types | High | Med | Low | ❌ Reject |
| 5 | Postgres + dbt-postgres | Server DB in Docker | Real server; mature dbt adapter | A container for 135k rows; not Yuno's OLAP | Med | Med | Med | ❌ Reject |
| 6 | BI tool (Metabase / Superset) | JVM BI server on top | Rich drill-down | Third-party DuckDB plugin; holds the file lock and blocks writes | Med | Med | High | ❌ Reject (scale path only) |
| 7 | Full lakehouse (Iceberg + StarRocks + Airflow) | Yuno prod stack in Compose | Mirrors prod | scenario.md: "not an enterprise data warehouse"; heavy on a laptop | Low | High | High | ❌ Reject (scale path only) |

## Top 2 choices
**🥇 Python + DuckDB + dbt-duckdb:** It is one in-process file, so `make all` runs on a reviewer's laptop in seconds. dbt gives the tests, contracts and lineage that score "good data engineering practice", and the same models port to Yuno's dbt at scale.
**🥈 Python scripts + polars + Parquet:** Second because DAG order, tests and lineage must be hand-written. It wins if the team has no dbt skills or needs the fewest possible dependencies.

## Reference stack
| Capability | Lean build (local) | Scale path (AWS / Yuno stack) |
|---|---|---|
| Runtime | Python 3.12 + uv; `uv.lock` committed | Same image on ECS/EKS, built in CI |
| Storage | DuckDB 1.4.x LTS, one `casa.duckdb` file | S3 + Iceberg (Glue) = truth; StarRocks PK tables = serving |
| Transforms | dbt-core 1.12 + dbt-duckdb 1.11 (not v2); thresholds from `thresholds.yaml` (pydantic) as dbt vars | Same dbt project on `dbt-starrocks` (experimental: spike first) |
| Money / FX | Integer minor units + currency exponent (CLP 0 decimals); daily FX table generated into `data/raw` as a source; seeds only for exponents, PSP fees, VAT; diff = FX-explained + residual | Daily FX feed (central bank / PSP) into Iceberg |
| Idempotency / pending | Append-only raw (`batch_id`); latest row per `transaction_id`; merge + re-open window for pending; failed/pending out of the rate | Iceberg MERGE / StarRocks PK upsert |
| DQ tests | dbt generic + unit tests, contracts on marts, incremental = full-refresh parity test; pytest | Same + source freshness + row counts vs PSP file totals |
| Stats | scipy + statsmodels (chi-square/Fisher, BH, Wilson CI, logit); HDBSCAN (scikit-learn) only as cross-check | Same package as an Airflow task |
| Dashboard | Streamlit + Plotly on localhost; DuckDB read-only; no logic in UI | Superset or Grafana on StarRocks |
| Alerts | dbt metric marts → Python evaluator with YAML rules (peer + change, min sample) → `alerts.jsonl` + report; optional Slack webhook | Same evaluator in Airflow → SNS → Slack / PagerDuty |
| Orchestration / run | Makefile targets → `uv run recon …` (Typer CLI, thin shell over the shared core) | MWAA (Airflow) + Cosmos for dbt |
| Docker | Optional Dockerfile for a machine without Python/make | Same image, Terraform-managed |
| Reproducibility | Fixed seed; 135k rows (45k × 3 months) default, `--rows 500` smoke; run manifest (seed, versions, counts) | Same + OpenLineage |
| Security | Synthetic data; no PAN; tokenised customer ID | IAM least privilege, KMS on S3, no PAN in analytics |

Key sources: [dbt: upgrading to v2 (DuckDB Beta)](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v2) · [dbt-duckdb on PyPI](https://pypi.org/project/dbt-duckdb/) · [DuckDB 1.4.5 LTS](https://duckdb.org/2026/06/17/announcing-duckdb-145) · [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency) · [dbt StarRocks setup (experimental)](https://docs.getdbt.com/docs/local/connect-data-platform/starrocks-setup)
