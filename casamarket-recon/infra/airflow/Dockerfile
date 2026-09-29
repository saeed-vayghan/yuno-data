# Local dev Airflow (standalone, SQLite, LocalExecutor) + casarecon in its OWN venv.
# Airflow's Python deps clash with dbt, so casarecon never goes into Airflow's env:
# DAG tasks call /opt/recon/.venv/bin/recon through BashOperator.
FROM apache/airflow:slim-3.3.2-python3.12
COPY --from=ghcr.io/astral-sh/uv:0.9.13 /uv /usr/local/bin/uv

USER root
RUN mkdir -p /opt/recon && chown airflow:0 /opt/recon
USER airflow
WORKDIR /opt/recon
ENV UV_PYTHON=/usr/python/bin/python3.12 UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 UV_NO_CACHE=1
COPY --chown=airflow:0 pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=airflow:0 src ./src
COPY --chown=airflow:0 dbt ./dbt
# The image's copy of dbt/profiles.yml only: cap DuckDB so dbt fits next to Airflow in 1 GB
# (it spills to disk instead). Drop this once profiles.yml reads a memory env var (HANDOFF.md).
RUN sed -i 's/^\( *\)threads: 4$/\1threads: 1\n\1settings: {memory_limit: "128MB", threads: 1}/' dbt/profiles.yml \
    && grep -q memory_limit dbt/profiles.yml
COPY --chown=airflow:0 config ./config
COPY --chown=airflow:0 contracts ./contracts
RUN uv sync --frozen --no-dev && /opt/recon/.venv/bin/recon --help >/dev/null

COPY --chown=airflow:0 infra/airflow/entrypoint.sh /opt/airflow/entrypoint-dev.sh
COPY --chown=airflow:0 infra/airflow/run_dag.sh /opt/airflow/run_dag.sh
WORKDIR /opt/airflow
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/opt/airflow/entrypoint-dev.sh"]
