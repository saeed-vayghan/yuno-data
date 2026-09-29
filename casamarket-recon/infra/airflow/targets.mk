# make targets for infra/airflow (owned by the airflow agent). Local dev only; see docs/AIRFLOW.md.
AIRFLOW_DC   = docker compose --profile airflow
AIRFLOW_DATE ?= $(shell date +%F)
AIRFLOW_CONF ?= {"full_refresh": false, "lookback_days": 15}

.PHONY: airflow-up airflow-run airflow-down
# Build the image, start the one Airflow container, wait until /api/v2/monitor/health is OK.
airflow-up:
	$(AIRFLOW_DC) up -d --build --wait airflow
	@echo "Airflow UI: http://localhost:$${AIRFLOW_PORT:-8080}  (login: $${AIRFLOW_ADMIN_USER:-admin} / $${AIRFLOW_ADMIN_PASSWORD:-admin})"
# Trigger casarecon_daily through the scheduler (REST API) and wait; exit != 0 unless it succeeds.
# First run on a fresh lake: make airflow-run AIRFLOW_CONF='{"full_refresh": true}'
airflow-run:
	$(AIRFLOW_DC) exec -T airflow /opt/airflow/run_dag.sh casarecon_daily $(AIRFLOW_DATE) '$(AIRFLOW_CONF)'
# Stop and remove only the Airflow container (leaves `recon` and the stream stack alone).
airflow-down:
	$(AIRFLOW_DC) rm -sf airflow
