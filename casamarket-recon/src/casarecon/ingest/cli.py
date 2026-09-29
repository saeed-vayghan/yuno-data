"""`recon ingest ...` (registered by casarecon.cli PLUGINS). Thin: each command runs one entry
through `casarecon.cli.run_step`, imported lazily (casarecon.cli imports this module)."""

from typing import Annotated

import typer

app = typer.Typer(help="PSP file landing, contract check, lake zones and arrival DQ.", no_args_is_help=True)


def _run(target: str, **kwargs) -> None:
    from casarecon.cli import run_step

    run_step(target, **kwargs)


@app.command()
def land(reset: Annotated[bool, typer.Option(help="Start a fresh lake first.")] = True) -> None:
    """Split data/raw into per-PSP daily files: data/lake/landing/psp=<PSP>/date=<D>/settlements.csv."""
    _run("casarecon.ingest.land:main", reset=reset)


FORCE = "YYYY-MM-DD: also reprocess landing files dated {} (inclusive), even if loaded or quarantined before."


@app.command()
def load(date_from: Annotated[str | None, typer.Option("--from", help=FORCE.format("from"))] = None,
         date_to: Annotated[str | None, typer.Option("--to", help=FORCE.format("up to"))] = None) -> None:
    """Contract-check new landing files -> staged parquet (settle_month=YYYY-MM) or quarantine."""
    _run("casarecon.ingest.load:main", date_from=date_from, date_to=date_to)


@app.command()
def check(as_of: Annotated[str | None, typer.Option(help="YYYY-MM-DD (default: latest file date).")] = None
          ) -> None:
    """Freshness, volume and schema-drift checks -> reports/ingest_dq.json (exit 5 on FAIL)."""
    _run("casarecon.ingest.check:main", as_of=as_of)
