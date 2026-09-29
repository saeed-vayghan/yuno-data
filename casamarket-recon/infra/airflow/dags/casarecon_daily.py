"""casarecon_daily: the lake path of `recon`, once a day (local dev only).

ingest_land (only when params.full_refresh) -> ingest_load -> ingest_check -> build -> validate
-> analyze -> alerts -> report. Each task runs one `recon` command from its own venv
(/opt/recon/.venv), so Airflow's Python never imports casarecon or dbt.
Exit codes: 0 ok, 1 error, 2 usage, 5 data quality. The DQ gates (ingest_check, validate) do
not retry: bad data stays bad on a second try.
"""

import os
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

HOME = os.environ.get("RECON_HOME", "/opt/recon")
ENV = {"PATH": f"{HOME}/.venv/bin:/usr/bin:/bin", "CASARECON_SOURCE": "lake"}
SKIP = 99  # BashOperator: this exit code marks the task skipped

# Full refresh: (generate raw if missing) -> land per-PSP files. Else skip.
LAND = ("{% if params.full_refresh %}[ -f data/raw/transactions.csv ] || recon generate; "
        "recon ingest land{% else %}echo 'full_refresh=false: nothing to land'; exit 99{% endif %}")
# Incremental over the restatement window; full build on a full refresh or when there is no DB yet.
BUILD = ("{% if params.full_refresh %}recon build{% else %}"
         "if [ -f data/casarecon.duckdb ]; then recon build --incremental --lookback-days "
         "{{ params.lookback_days }}; else recon build; fi{% endif %}")


def recon(task_id: str, command: str, **kw) -> BashOperator:
    return BashOperator(task_id=task_id, bash_command=f"cd {HOME} && {command}",
                        env=ENV, append_env=True, **kw)


with DAG(
    dag_id="casarecon_daily",
    schedule="@daily",
    start_date=datetime(2026, 4, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    params={
        "lookback_days": Param(15, type="integer", minimum=0, description="Restatement window (days)."),
        "full_refresh": Param(False, type="boolean", description="Re-land raw files + full build."),
    },
    tags=["casarecon", "local-dev"],
):
    steps = [
        recon("ingest_land", LAND, skip_on_exit_code=SKIP),
        recon("ingest_load", "recon ingest load", trigger_rule="none_failed"),
        recon("ingest_check", "recon ingest check", retries=0),
        recon("build", BUILD),
        recon("validate", "recon validate", retries=0),
        recon("analyze", "recon analyze"),
        recon("alerts", "recon alerts"),
        recon("report", "recon report"),
    ]
    for up, down in zip(steps, steps[1:]):
        up >> down
