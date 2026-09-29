"""Shared fixtures (INFRA). Tests never touch data/casarecon.duckdb.

- `fixture_db` (session): generate 500 rows (seed 42) + dbt build into a tmp dir, once per session.
  Env vars CASARECON_DB / _RAW_DIR / _TRUTH_DIR / _REPORTS_DIR point there for the rest of the
  session, so `core.*` functions and the CLI read the fixture DB. Yields the DB path.
- `tmp_env` (function): empty tmp paths (no DB) for "missing data" tests.
"""

from pathlib import Path

import pytest

FIXTURE_ROWS, FIXTURE_SEED = 500, 42


def _point_env_at(mp: pytest.MonkeyPatch, root: Path) -> None:
    mp.setenv("CASARECON_DB", str(root / "casarecon.duckdb"))
    mp.setenv("CASARECON_RAW_DIR", str(root / "raw"))
    mp.setenv("CASARECON_TRUTH_DIR", str(root / "truth"))
    mp.setenv("CASARECON_REPORTS_DIR", str(root / "reports"))


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory) -> Path:
    """500-row DuckDB built once per session: generate + build (the real pipeline)."""
    from casarecon.generate.run import main as generate
    from casarecon.pipeline.build import main as build

    root = tmp_path_factory.mktemp("fixture_db")
    mp = pytest.MonkeyPatch()
    _point_env_at(mp, root)
    generate(rows=FIXTURE_ROWS, seed=FIXTURE_SEED)
    build()
    yield root / "casarecon.duckdb"
    mp.undo()


@pytest.fixture
def tmp_env(tmp_path, monkeypatch):
    """Point DB, raw, truth and reports paths at an empty tmp dir."""
    _point_env_at(monkeypatch, tmp_path)
    return tmp_path
