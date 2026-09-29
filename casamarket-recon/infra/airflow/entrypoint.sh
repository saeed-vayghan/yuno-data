#!/usr/bin/env bash
# Dev entrypoint. `dev` = a lean `airflow standalone`: api-server (UI + task API) + scheduler
# (LocalExecutor) + dag-processor on SQLite; no triggerer, no log-serving side processes.
# Anything else goes to the official entrypoint (e.g. `airflow dags test ...`).
set -euo pipefail
pw_file="${AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE:-/opt/airflow/passwords.json}"
printf '{"%s": "%s"}\n' "${AIRFLOW_ADMIN_USER:-admin}" "${AIRFLOW_ADMIN_PASSWORD:-admin}" > "$pw_file"

if [[ "${1:-}" == "dev" ]]; then
  airflow db migrate
  airflow dag-processor &
  airflow scheduler --skip-serve-logs &
  airflow api-server --port 8080 &
  wait -n  # one component died: stop the container so `docker compose ps` shows it
  exit 1
fi
exec /entrypoint "$@"
