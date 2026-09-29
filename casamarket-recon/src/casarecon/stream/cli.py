"""`recon stream ...`: local streaming path (Redpanda + Flink SQL). Thin shell over `casarecon.cli.run_step`
(exit codes 0 ok, 1 error, 2 usage, 5 data quality). Kafka commands need `uv run --with kafka-python`."""

import json
from typing import Annotated, Any

import typer

app = typer.Typer(help="Streaming path: replay events to Redpanda, compare Flink output with batch.",
                  no_args_is_help=True)

BOOTSTRAP = Annotated[str, typer.Option(help="Kafka bootstrap servers (Redpanda).")]


def _run(target: str, **kwargs: Any) -> Any:
    from casarecon.cli import run_step  # lazy: casarecon.cli imports this module at load time

    return run_step(target, **kwargs)


@app.command()
def replay(
    speed: Annotated[float, typer.Option(help="Event seconds per wall second (0 = no wait).")] = 86400.0,
    limit: Annotated[int | None, typer.Option(help="Only the first N events (event-time order).")] = None,
    bootstrap: BOOTSTRAP = "localhost:19092",
) -> None:
    """Publish data/raw transactions as `auths` + `settlements` events, in event-time order."""
    out = _run("casarecon.stream.replay:main", speed=speed, limit=limit, bootstrap=bootstrap)
    typer.echo(json.dumps(out))


@app.command()
def compare() -> None:
    """Category match of the Flink sink vs the batch fct, per category (exit 5 below 99%)."""
    _run("casarecon.stream.compare:main")


@app.command()
def tail(
    limit: Annotated[int, typer.Option(help="Max messages.")] = 10,
    timeout: Annotated[float, typer.Option(help="Stop after N seconds without data.")] = 5.0,
    bootstrap: BOOTSTRAP = "localhost:19092",
) -> None:
    """Print `large_discrepancies` messages (from the start of the topic)."""
    for msg in _run("casarecon.stream.kafka_io:consume", topic="large_discrepancies",
                    bootstrap=bootstrap, limit=limit, timeout_s=timeout):
        typer.echo(json.dumps(msg))
