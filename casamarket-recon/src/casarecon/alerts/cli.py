"""`recon alert ...` sub-commands (Typer group, loaded by cli.py PLUGINS). Thin: each command
runs one function of alerts/manage.py through cli.run_step (same exit codes as `recon`)."""

from typing import Annotated

import typer

app = typer.Typer(help="Alert memory: list, ack, mute, history.", no_args_is_help=True)
MANAGE = "casarecon.alerts.manage"
KEY = Annotated[str, typer.Argument(help="Alert key, e.g. 'peer|PSP_B|AR' (quote the |).")]
NOTE = Annotated[str, typer.Option(help="Free text, e.g. a ticket id.")]


def _run(name: str, **kwargs: object) -> None:
    from casarecon.cli import run_step  # lazy: cli.py imports this module while it loads

    run_step(f"{MANAGE}:{name}", **kwargs)


@app.command("list")
def list_(all_: Annotated[bool, typer.Option("--all", help="Also RESOLVED and INFO rows.")] = False) -> None:
    """Open alerts of the last run with open_since, muted and ack."""
    _run("show_list", show_all=all_)


@app.command()
def ack(key: KEY, note: NOTE = "") -> None:
    """Acknowledge an alert (owner has seen it) for its current open streak."""
    _run("ack", key=key, note=note)


@app.command()
def mute(key: KEY, until: Annotated[str, typer.Option(help="Last muted ISO week, YYYY-Www.")],
         note: NOTE = "") -> None:
    """Mute an alert until a week: still recorded, not notified."""
    _run("mute", key=key, until=until, note=note)


@app.command()
def unmute(key: KEY) -> None:
    """Remove a mute."""
    _run("unmute", key=key)


@app.command()
def history(key: KEY) -> None:
    """One line per evaluated week for this key (from data/alerts/history.jsonl)."""
    _run("history", key=key)
