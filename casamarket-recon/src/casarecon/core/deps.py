"""Tiny composition point: default adapters for each port. Tests pass fakes via `store=`.

Lazy imports keep core free of duckdb/requests at import time.
"""

from pathlib import Path
from types import SimpleNamespace

from casarecon.core import paths
from casarecon.ports import DbtRunner, Notifier, ReportFiles, Store


def get_store() -> Store:
    return get_store_at(paths.db_path())


def get_store_at(path: Path) -> Store:
    """Read-only store on any DuckDB file (e.g. the `.tmp` build before the swap)."""
    from casarecon.adapters.duckdb_store import DuckDbStore

    return DuckDbStore(path)


def get_files() -> ReportFiles:
    from casarecon.adapters import files

    return SimpleNamespace(**{n: getattr(files, n) for n in (
        "read_json", "write_json", "read_text", "write_text", "read_jsonl", "write_jsonl",
        "read_csv", "write_csv", "read_parquet", "write_figures")})


def get_notifier() -> Notifier:
    from casarecon.adapters.slack import post

    return post


def get_dbt_runner() -> DbtRunner:
    from casarecon.adapters.dbt_runner import run_dbt

    return run_dbt
