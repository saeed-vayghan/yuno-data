"""Repo paths. Functions (not constants) so env overrides work in tests."""

import os
from pathlib import Path


def _find_root() -> Path:
    env = os.environ.get("CASARECON_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve().parents[3]  # src/casarecon/core/paths.py -> repo root
    return here if (here / "pyproject.toml").exists() else Path.cwd().resolve()


REPO_ROOT: Path = _find_root()


def _env_path(var: str, default: Path) -> Path:
    return Path(os.environ.get(var, default)).resolve()


def db_path() -> Path:
    """Absolute DuckDB path (env CASARECON_DB)."""
    return _env_path("CASARECON_DB", REPO_ROOT / "data" / "casarecon.duckdb")


def raw_dir() -> Path:
    return _env_path("CASARECON_RAW_DIR", REPO_ROOT / "data" / "raw")


def truth_dir() -> Path:
    return _env_path("CASARECON_TRUTH_DIR", REPO_ROOT / "data" / "truth")


def reports_dir() -> Path:
    return _env_path("CASARECON_REPORTS_DIR", REPO_ROOT / "reports")


def figures_dir() -> Path:
    return reports_dir() / "figures"


SAMPLE_DIR: Path = REPO_ROOT / "data" / "sample"
CONFIG_DIR: Path = REPO_ROOT / "config"
DBT_DIR: Path = REPO_ROOT / "dbt"
SEEDS_DIR: Path = DBT_DIR / "seeds"
