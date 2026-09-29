# Airflow (local dev)

A local scheduler for the lake path of `recon`. Nothing is deployed; it is off by default.

## Start / run / stop
```bash
make airflow-up   # build image, start the container, wait for health
make airflow-run AIRFLOW_CONF='{"full_refresh": true}'   # first run: land + full build
make airflow-run       # later: incremental run (lookback 15 days)
make airflow-down      # remove the Airflow container only
```
Same by hand: `docker compose --profile airflow up -d --build --wait airflow`.

- UI: <http://localhost:8080>, login **admin / admin** (dev default; set `AIRFLOW_ADMIN_USER` /
  `AIRFLOW_ADMIN_PASSWORD` in `.env` or the shell to change it). Port 8080 taken on your machine?
  `AIRFLOW_PORT=8090 make airflow-up`.
- The DAGs are paused at creation: unpause `casarecon_daily` in the UI to let it run `@daily`,
  or trigger it by hand ("Trigger" → set params).
- `make airflow-run [AIRFLOW_DATE=YYYY-MM-DD] [AIRFLOW_CONF='{...}']` runs `run_dag.sh` in the
  container: triggers `casarecon_daily` through the REST API (the real scheduler + LocalExecutor),
  waits, prints each task's state, exits != 0 unless the run succeeds. A paused DAG does not start
  runs, so the script unpauses it for the run and pauses it again; on unpause the scheduler may
  also create that day's scheduled run (catchup=False → at most one), which stays queued while paused.

## What runs
Airflow 3.3 (`apache/airflow:slim-3.3.2-python3.12`), one container: api-server + scheduler +
dag-processor, SQLite metadata, LocalExecutor with parallelism 1 (DuckDB has one writer). No
Postgres, Redis, Celery or triggerer. The metadata DB lives in the container: run history is
lost on `airflow-down`, which is fine for dev.

casarecon is **not** installed into Airflow's Python (Airflow and dbt pin clashing deps). The
image has its own venv, `/opt/recon/.venv`, and every task is a `BashOperator` that runs
`recon ...` from `/opt/recon`. `./data`, `./reports` and `./config` are mounted there, so the
DuckDB file, the lake and the reports are the same files `make all` uses.
Plotly figures are written as HTML inside Airflow (no Chrome in the image for PNG export).

## `casarecon_daily`
`@daily`, start 2026-04-01, `catchup=False`, one active run, retries 1 (1 min delay).

| Task | Command |
|---|---|
| ingest_land | only if `full_refresh`: `recon generate` (if `data/raw` is empty) + `recon ingest land`; else skipped (exit 99) |
| ingest_load | `recon ingest load` (new or changed landing files → staged parquet / quarantine) |
| ingest_check | `recon ingest check` (freshness, volume, schema drift; no retry) |
| build | `CASARECON_SOURCE=lake recon build --incremental --lookback-days N`; full build if `full_refresh` or no DB yet |
| validate | `recon validate` (no retry) |
| analyze, alerts, report | `recon analyze`, `recon alerts`, `recon report` |

Params: `lookback_days` (15 = max settle lag), `full_refresh` (false).
Exit codes are the CLI's: 0 ok, 1 error, 2 usage, 5 data quality. Any non-zero fails the task.
The data-quality gates (`ingest_check`, `validate`) have `retries=0`: bad data stays bad.

## Backfill and the logical date
The pipeline works **as of the data** (latest timestamp in the lake/DB), not as of Airflow's
logical date. So an Airflow backfill of `casarecon_daily` (`airflow backfill create
--dag-id casarecon_daily --from-date D1 --to-date D2`) only re-runs the same as-of-data pipeline
once per logical date; it does not replay those days.

To replay days, trigger **`casarecon_backfill`** (manual only) with params `from` / `to`
(YYYY-MM-DD). It runs `recon ops backfill --from D1 --to D2`: reload landing files dated
D1..D2 (re-sent PSP files), DQ check, then an incremental build whose window reaches back to D1
(see [PLATFORM.md](PLATFORM.md#replay--backfill)). If `from` is empty it uses the run's logical
date (`ds`); `to` defaults to `from`.

## Memory (known limit)
Docker here has ~2 GB in total and the stream stack may run next to it, so the container
defaults to `mem_limit: 1536m` (`AIRFLOW_MEM_LIMIT` overrides it; 1g is too small for the full analyze). Idle Airflow uses ~480 MB
(api-server ~190, dag-processor ~140, scheduler + executor ~140; no triggerer / log servers).
DuckDB inside dbt is capped at 128 MB, 1 thread (the image's copy of `dbt/profiles.yml`), so
ingest + build fit in 1 GB. **`recon analyze` on the full 135k rows does not**: it is OOM-killed
(exit -9) at 1 GB. A full-refresh run peaks at ~1.3 GB, so run it with
`AIRFLOW_MEM_LIMIT=1536m` while the stream stack is down (verified: 8/8 tasks success, ~50 s).
Always start only this service (`up ... airflow`): a plain `docker compose --profile airflow up`
also starts the default `recon` service.
