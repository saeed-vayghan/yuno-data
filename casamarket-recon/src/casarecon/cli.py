"""`recon` CLI: a thin shell. Each command lazy-imports one entry function and runs it through
`run_step`, which owns the exit-code mapping. Owner: INFRA. No metric logic here."""

import importlib
import time
from collections.abc import Callable
from typing import Annotated, Any

import typer

from casarecon.core import log
from casarecon.core.errors import BadFilter, CasaReconError, DataQualityError, DbBusy, DbMissing

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_DQ = 0, 1, 2, 5

app = typer.Typer(help="CasaMarket settlement reconciliation.", no_args_is_help=True,
                  add_completion=False)


def _entry(target: str) -> Callable[..., Any]:
    """'casarecon.generate.run:main' -> the function (lazy import keeps --help fast)."""
    module, _, name = target.partition(":")
    return getattr(importlib.import_module(module), name)


def run_step(target: str, **kwargs: Any) -> Any:
    """Run one entry function; map errors to exit codes (0 ok, 1 error, 2 usage, 5 data quality)."""
    logger = log.get("cli")
    try:
        return _entry(target)(**kwargs)
    except NotImplementedError as e:
        typer.echo(f"step not built yet: {target} ({e}); stopping here", err=True)
    except DataQualityError as e:
        logger.error("step failed: %s", e)
        raise typer.Exit(EXIT_DQ)
    except BadFilter as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(EXIT_USAGE)
    except DbMissing:
        typer.echo("No data yet. Run `make all` first.", err=True)
    except DbBusy:
        typer.echo("rebuilding, retry", err=True)
    except CasaReconError as e:
        typer.echo(str(e), err=True)
    except Exception:
        logger.exception("unexpected error")
    raise typer.Exit(EXIT_ERROR)


ROWS = Annotated[int | None, typer.Option(help="Rows to generate (default: generator.yaml).")]
SEED = Annotated[int | None, typer.Option(help="Random seed (default: generator.yaml).")]
CLI_QUERY = "casarecon.cli_query"


@app.callback()
def _main(verbose: Annotated[bool, typer.Option("--verbose", "-v", help="DEBUG logs.")] = False) -> None:
    log.setup(verbose)


@app.command()
def generate(rows: ROWS = None, seed: SEED = None) -> None:
    """Generate synthetic transactions + FX rates into data/raw."""
    run_step("casarecon.generate.run:main", rows=rows, seed=seed)


@app.command()
def build(
    incremental: Annotated[bool, typer.Option(
        "--incremental", help="Update the current DB: reprocess only the restatement window.")] = False,
    lookback_days: Annotated[int | None, typer.Option(
        help="Restatement window in days (default 15 = max settle lag).")] = None,
) -> None:
    """Build the DuckDB file with dbt (the only command that writes the DB). Default: full rebuild."""
    run_step("casarecon.pipeline.build:main", incremental=incremental, lookback_days=lookback_days)


@app.command()
def validate() -> None:
    """Validation gate: shares and planted-pattern bands."""
    run_step("casarecon.validate.run:main")


@app.command()
def analyze() -> None:
    """Statistical analysis -> reports/findings.json + figures."""
    run_step("casarecon.analysis.run:main")


@app.command()
def alerts() -> None:
    """Evaluate alert rules -> reports/alerts.jsonl (+ Slack if enabled)."""
    run_step("casarecon.alerts.run:main")


@app.command()
def report() -> None:
    """Render FINDINGS.md and recommendations."""
    run_step("casarecon.report.run:main")


@app.command()
def query(
    min_usd: Annotated[float | None, typer.Option(help="Strict: abs_residual_usd > MIN_USD.")] = 50,
    psp: Annotated[list[str] | None, typer.Option(help="Repeatable.")] = None,
    country: Annotated[list[str] | None, typer.Option(help="Repeatable.")] = None,
    limit: Annotated[int | None, typer.Option()] = None,
    format: Annotated[str, typer.Option("--format", help="table|csv|json")] = "table",
) -> None:
    """Transactions with discrepancies over $N (FX-adjusted USD)."""
    run_step(f"{CLI_QUERY}:query", min_usd=min_usd, psp=tuple(psp or ()),
             country=tuple(country or ()), limit=limit, fmt=format)


@app.command("worst-week")
def worst_week(
    month: Annotated[str, typer.Option(help="last | YYYY-MM")] = "last",
    format: Annotated[str, typer.Option("--format", help="table|json")] = "table",
) -> None:
    """Which PSP had the worst week last month."""
    run_step(f"{CLI_QUERY}:worst_week", month=month, fmt=format)


@app.command()
def dashboard(port: int = 8501, host: str = "localhost") -> None:
    """Open the Streamlit dashboard."""
    run_step("casarecon.dashboard.launch:main", port=port, host=host)


# A step that is not built yet (NotImplementedError) stops the run with exit 1.
STEPS = ("generate", "build", "validate", "analyze", "alerts", "report")


@app.command("all")
def all_(rows: ROWS = None, seed: SEED = None) -> None:
    """generate -> build -> validate -> analyze -> alerts -> report; stop at the first failure."""
    logger = log.get("cli")
    for name in STEPS:
        start = time.perf_counter()
        kwargs = {"rows": rows, "seed": seed} if name == "generate" else {}
        globals()[name](**kwargs)
        logger.info(log.kv(step=name, secs=round(time.perf_counter() - start, 1)))


# Sub-command groups owned by other packages (M4). Each module exposes a Typer `app`.
# A missing module is skipped, so a group appears only once its package is built.
PLUGINS = {
    "ingest": "casarecon.ingest.cli:app",   # recon ingest ...  (landing, quarantine, lake zones, DQ)
    "alert": "casarecon.alerts.cli:app",    # recon alert ...   (history, ack, mute, notify)
    "ops": "casarecon.ops.cli:app",         # recon ops ...     (backfill/replay, lineage, platform)
}
for _name, _target in PLUGINS.items():
    try:
        app.add_typer(_entry(_target), name=_name)
    except ModuleNotFoundError:
        pass
