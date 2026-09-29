"""`recon ops backfill --from D1 --to D2`: replay a date range from the lake.

Steps (each one is a `recon` sub-command, so each keeps its own checks and exit codes):
1. `recon ingest load`: loads every new or changed landing file (e.g. a PSP re-sent a day) to staged.
   Unchanged files are skipped by hash; their staged parts are already there.
2. `recon ingest check --as-of D2`: freshness / volume / schema-drift up to the range end.
3. `recon build --incremental --lookback-days N` with `CASARECON_SOURCE=lake`. N reaches from the
   range start to the data as-of, so every replayed day falls inside the restatement window.
The range must have landing files (`landing/psp=*/date=D/settlements.csv`), else exit 1.
A step that exits 5 stops the replay with exit 5 (data quality); any other failure exits 1.
"""

from collections.abc import Callable, Sequence
from datetime import date, timedelta
from pathlib import Path

from casarecon.core.errors import BadFilter, CasaReconError, DataQualityError, InputMissing
from casarecon.ingest.settings import lake_dir

Runner = Callable[[Sequence[str], dict[str, str]], int]
LAKE_ENV = {"CASARECON_SOURCE": "lake"}


def days(start: date, end: date) -> list[date]:
    if end < start:
        raise BadFilter(f"--to {end} is before --from {start}")
    return [start + timedelta(d) for d in range((end - start).days + 1)]


def lookback_days(start: date, as_of: date) -> int:
    """Days from the range start to as-of, inclusive (the incremental window must cover both)."""
    return max((as_of - start).days + 1, 1)


def plan(start: date, end: date, as_of: date | None = None) -> list[tuple[list[str], dict[str, str]]]:
    """Ordered (recon args, extra env) steps. Pure, so `--dry-run` and tests can show it."""
    days(start, end)  # validates the range
    n = lookback_days(start, max(as_of or end, end))
    return [(["ingest", "load"], {}), (["ingest", "check", "--as-of", end.isoformat()], {}),
            (["build", "--incremental", "--lookback-days", str(n)], dict(LAKE_ENV))]


def landing_days(lake: Path, start: date, end: date) -> list[date]:
    """Days in the range that have at least one landing file (lake layout from docs/ARCH-M4.md)."""
    wanted = {d.isoformat(): d for d in days(start, end)}
    found = {p.parent.name.removeprefix("date=") for p in lake.glob("landing/psp=*/date=*/settlements.csv")}
    return sorted(wanted[k] for k in found & set(wanted))


def data_as_of() -> date | None:
    """Latest timestamp in the current DB (as a date), or None when there is no DB yet."""
    from casarecon import core
    from casarecon.core.errors import DbMissing

    try:
        return core.status()["as_of"].date()
    except DbMissing:
        return None


def main(*, start: date, end: date, as_of: date | None = None, dry_run: bool = False,
         runner: Runner | None = None) -> list[str]:
    """Run (or only list, with dry_run) the replay steps. Returns the commands as strings."""
    steps = plan(start, end, as_of or data_as_of())
    shown = [" ".join([*(f"{k}={v}" for k, v in env.items()), "recon", *args]) for args, env in steps]
    if dry_run:
        return shown
    lake = lake_dir()
    if not landing_days(lake, start, end):
        raise InputMissing(f"no landing files for {start}..{end} in {lake}. Run `recon ingest land` first.")
    if runner is None:
        from casarecon.ops.shell import run_recon as runner
    for (args, env), cmd in zip(steps, shown, strict=True):
        code = runner(args, env)
        if code == 5:
            raise DataQualityError(f"backfill stopped: `{cmd}` failed a data-quality check")
        if code != 0:
            raise CasaReconError(f"backfill stopped: `{cmd}` exited {code}")
    return shown
