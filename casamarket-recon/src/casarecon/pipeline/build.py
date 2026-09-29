"""Entry point for `recon build`: dbt build into `<stem>_tmp.duckdb`, then an atomic swap. Owner: INFRA.

The only writer of the DuckDB file. A failed model or dbt test raises DataQualityError (exit 5)
and keeps the last good DB untouched.
"""

import os
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from casarecon.core import log, paths
from casarecon.core.config import dbt_vars
from casarecon.core.deps import get_dbt_runner, get_store_at
from casarecon.core.errors import CasaReconError, DataQualityError, InputMissing
from casarecon.pipeline import manifest
from casarecon.ports import DbtRunner, Store

RAW_FILES = ("transactions.csv", "fx_rates_daily.csv")
SCHEMAS = ("ref", "staging", "intermediate", "marts")


def _remove(db_file: Path) -> None:
    for p in (db_file, db_file.with_name(db_file.name + ".wal")):
        p.unlink(missing_ok=True)


def dbt_args(work_dir: Path) -> list[str]:
    """dbt CLI args; target/log dirs sit next to the DB so parallel builds never share them."""
    return ["build", "--vars", dbt_vars(), "--target-path", str(work_dir / "target"),
            "--log-path", str(work_dir / "logs")]


def row_counts(store: Store) -> dict[str, int]:
    """{'marts.fct_transaction_discrepancy': 500, ...} for every table the build made."""
    tables = store.query(
        "select table_schema || '.' || table_name as t from information_schema.tables"
        f" where table_schema in ({', '.join('?' for _ in SCHEMAS)}) order by 1", SCHEMAS)["t"]
    if tables.empty:
        return {}
    union = " union all ".join(f"select '{t}' as t, count(*) as n from {t}" for t in tables)
    return {r.t: int(r.n) for r in store.query(union).itertuples()}


def write_manifest(counts: dict[str, int]) -> Path:
    """Fresh reports/run_manifest.json with the build section (the only wall-clock timestamp)."""
    info = {"built_at": datetime.now(UTC).isoformat(timespec="seconds"), "row_counts": counts,
            "versions": {p: version(p) for p in ("dbt-core", "dbt-duckdb", "duckdb")}}
    return manifest.update("build", info, reset=True)


def main(*, runner: DbtRunner | None = None,
         store_at: Callable[[Path], Store] | None = None) -> dict[str, int]:
    """Build data/casarecon.duckdb from data/raw. Returns row counts per table."""
    logger = log.get("build")
    db, raw = paths.db_path(), paths.raw_dir()
    missing = [f for f in RAW_FILES if not (raw / f).exists()]
    if missing:
        raise InputMissing(f"missing {', '.join(missing)} in {raw}. Run `recon generate` first.")
    tmp = db.with_name(f"{db.stem}_tmp{db.suffix}")  # no extra dot: dbt-duckdb names the catalog after the stem
    db.parent.mkdir(parents=True, exist_ok=True)
    _remove(tmp)
    env = {"CASARECON_BUILD_PATH": str(tmp), "CASARECON_RAW_DIR": str(raw)}
    code = (runner or get_dbt_runner())(dbt_args(db.parent / ".dbt"), env)
    if code != 0:
        _remove(tmp)
        if code == 1:
            raise DataQualityError("dbt build failed (a model or test failed, see log); last good DB kept")
        raise CasaReconError(f"dbt crashed (exit {code})")
    counts = row_counts((store_at or get_store_at)(tmp))
    os.replace(tmp, db)
    write_manifest(counts)
    for table, n in counts.items():
        logger.info(log.kv(step="build", table=table, rows=n))
    return counts
