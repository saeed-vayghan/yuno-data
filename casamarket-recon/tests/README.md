# tests
`infra/` (INFRA), `backend/` (BACKEND), `dashboard/` (FRONTEND). Unit + integration + smoke only. Run: `uv run pytest -q`.
Never test against data/casarecon.duckdb. Fixtures (`conftest.py`): `fixture_db` = 500-row DB (generate seed 42 + dbt build)
in a tmp dir, env vars redirected for the session, so `core.*` and the CLI read it; `tmp_env` = empty tmp paths (no DB).
