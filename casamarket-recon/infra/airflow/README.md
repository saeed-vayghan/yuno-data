# infra/airflow

Local dev Airflow that runs the existing `recon` commands on a schedule. Off by default
(compose profile `airflow`). Full notes: [docs/AIRFLOW.md](../../docs/AIRFLOW.md).

| File | What |
|---|---|
| `compose.yml` | one `airflow` service (profile `airflow`, `mem_limit` 1536m default / `AIRFLOW_MEM_LIMIT`, UI on :8080 / `AIRFLOW_PORT`), included by the root `docker-compose.yml` |
| `Dockerfile` | `apache/airflow:slim-3.3.2-python3.12` + casarecon in its own venv `/opt/recon/.venv` (Airflow and dbt deps clash) |
| `entrypoint.sh` | writes the dev login, then `dev` = api-server + scheduler + dag-processor (SQLite, LocalExecutor) |
| `run_dag.sh` | `make airflow-run`: trigger a DAG through the REST API and wait for it |
| `dags/casarecon_daily.py` | ingest_land → ingest_load → ingest_check → build → validate → analyze → alerts → report |
| `dags/casarecon_backfill.py` | `recon ops backfill --from --to` |
| `targets.mk` | `make airflow-up`, `make airflow-run`, `make airflow-down` |

`./data`, `./reports` and `./config` are mounted into `/opt/recon`, so outputs land in the repo.
Tests: `tests/infra/test_airflow_dags.py` (plain `ast`, no Airflow install needed).
