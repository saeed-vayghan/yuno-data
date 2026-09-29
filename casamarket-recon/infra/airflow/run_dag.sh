#!/usr/bin/env bash
# Trigger a DAG run through the scheduler (REST API) and wait for it. Exit 0 only on success.
# Runs inside the container: run_dag.sh DAG_ID LOGICAL_DATE [CONF_JSON]
# Paused DAGs do not start runs, so the DAG is unpaused for the run and paused again after.
set -euo pipefail
dag=$1 day=$2 conf=${3:-"{}"} api=http://localhost:8080
json() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }
token=$(curl -fsS -X POST "$api/auth/token" -H 'Content-Type: application/json' \
  -d "{\"username\": \"${AIRFLOW_ADMIN_USER:-admin}\", \"password\": \"${AIRFLOW_ADMIN_PASSWORD:-admin}\"}" | json '["access_token"]')
call() { curl -fsS -H "Authorization: Bearer $token" -H 'Content-Type: application/json' "$@"; }
pause() { call -X PATCH "$api/api/v2/dags/$dag" -d "{\"is_paused\": $1}" >/dev/null; }

run=$(call -X POST "$api/api/v2/dags/$dag/dagRuns" \
  -d "{\"logical_date\": \"${day}T00:00:00Z\", \"conf\": $conf}" | json '["dag_run_id"]')
was_paused=$(call "$api/api/v2/dags/$dag" | json '["is_paused"]')
[[ $was_paused == True ]] && { pause false; trap 'pause true' EXIT; }
echo "$dag: triggered $run"
while :; do
  state=$(call "$api/api/v2/dags/$dag/dagRuns/$run" | json '["state"]')
  [[ $state == success || $state == failed ]] && break
  sleep 10
done
call "$api/api/v2/dags/$dag/dagRuns/$run/taskInstances" | python3 -c "
import json, sys
for t in sorted(json.load(sys.stdin)['task_instances'], key=lambda t: t['start_date'] or '~'):
    print('  %-13s %s' % (t['task_id'], t['state']))"
echo "$dag: $state"
[[ $state == success ]]
