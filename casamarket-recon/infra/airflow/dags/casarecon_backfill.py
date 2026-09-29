"""casarecon_backfill: replay days from the lake (local dev only). Manual trigger only.

`recon ops backfill --from D1 --to D2` = ingest load (per day, re-sent files) -> ingest check ->
incremental build whose window covers D1..as-of. D1/D2 default to the run's logical date.
"""

import os
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

HOME = os.environ.get("RECON_HOME", "/opt/recon")
DAY = {"type": ["null", "string"], "format": "date"}

with DAG(
    dag_id="casarecon_backfill",
    schedule=None,
    start_date=datetime(2026, 4, 1),
    catchup=False,
    max_active_runs=1,
    params={"from": Param(None, **DAY, description="First day (YYYY-MM-DD). Default: logical date."),
            "to": Param(None, **DAY, description="Last day (YYYY-MM-DD). Default: from.")},
    tags=["casarecon", "local-dev"],
):
    BashOperator(
        task_id="backfill",
        bash_command=(f"cd {HOME} && recon ops backfill"
                      " --from {{ params['from'] or ds }} --to {{ params['to'] or params['from'] or ds }}"),
        env={"PATH": f"{HOME}/.venv/bin:/usr/bin:/bin", "CASARECON_SOURCE": "lake"},
        append_env=True,
        retries=0,  # exit 5 (a DQ check failed) must not be retried
    )
