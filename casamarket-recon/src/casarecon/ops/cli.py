"""`recon ops ...`: local dev tooling. Thin shell: each command runs one entry function through
`casarecon.cli.run_step` (same exit codes: 0 ok, 1 error, 2 usage, 5 data quality)."""

import json
from datetime import datetime
from typing import Annotated, Any

import typer

app = typer.Typer(help="Local dev tooling: lineage, PII scan, replay/backfill.", no_args_is_help=True)

DATE = ["%Y-%m-%d"]


def _run(target: str, **kwargs: Any) -> Any:
    from casarecon.cli import run_step  # lazy: casarecon.cli imports this module at load time

    return run_step(target, **kwargs)


@app.command()
def lineage() -> None:
    """dbt docs generate -> data/.dbt/lineage/target + reports/lineage/LINEAGE.md."""
    out = _run("casarecon.ops.lineage:main")
    typer.echo(f"lineage: {out['models']} models -> {out['summary']} (docs site: {out['docs']})")


@app.command("pii-scan")
def pii_scan() -> None:
    """Banned fields anywhere + full customer IDs in outputs (exit 5 on a hit)."""
    out = _run("casarecon.ops.pii:main")
    typer.echo(f"pii-scan: clean ({out['files']} files)")


@app.command()
def backfill(
    start: Annotated[datetime, typer.Option("--from", formats=DATE, help="First day (YYYY-MM-DD).")],
    end: Annotated[datetime, typer.Option("--to", formats=DATE, help="Last day (YYYY-MM-DD).")],
    as_of: Annotated[datetime | None, typer.Option("--as-of", formats=DATE,
                                                   help="Data as-of (default: latest in the DB).")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Only print the steps.")] = False,
) -> None:
    """Replay days from the lake: ingest load per day, then an incremental build covering them."""
    steps = _run("casarecon.ops.backfill:main", start=start.date(), end=end.date(),
                 as_of=as_of.date() if as_of else None, dry_run=dry_run)
    typer.echo(json.dumps({"dry_run": dry_run, "steps": steps}, indent=2))
