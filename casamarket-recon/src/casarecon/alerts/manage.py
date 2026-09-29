"""`recon alert list | ack | mute | unmute | history`: read / change alert memory, print text.

Reads reports/alerts.jsonl (last `recon alerts` run), data/alerts/history.jsonl and
config/alert_state.yaml. ack / mute only write alert_state.yaml; `muted` in alerts.jsonl and the
outbox follow on the next `recon alerts`. Unknown key or bad week -> BadFilter (exit 2).
"""

import sys

from casarecon.alerts import memory, sink
from casarecon.alerts.record import INSUFFICIENT, RESOLVED
from casarecon.core import paths
from casarecon.core.errors import BadFilter
from casarecon.core.filters import WEEK_RE

LIST_COLS = ("key", "severity", "status", "open_since", "muted", "ack", "owner")
HISTORY_COLS = ("period", "status", "severity", "open_since", "muted", "sent")


def _latest() -> list[dict]:
    return sink.read_jsonl(paths.reports_dir() / "alerts.jsonl")


def _table(rows: list[dict], cols: tuple[str, ...]) -> str:
    cells = [[("-" if r.get(c) is None else str(r.get(c))) for c in cols] for r in rows]
    width = [max([len(c)] + [len(row[i]) for row in cells]) for i, c in enumerate(cols)]
    fmt = lambda vals: "  ".join(v.ljust(w) for v, w in zip(vals, width)).rstrip()  # noqa: E731
    return "\n".join([fmt(cols), *(fmt(row) for row in cells)]) + "\n"


def _ack_text(alert: dict, state: dict) -> str | None:
    entry = memory.ack_of(alert, state)
    return f"{entry['period']}: {entry.get('note', '')}" if entry else None


def list_rows(alerts: list[dict], state: dict, show_all: bool = False) -> list[dict]:
    """Pure: open alerts (NEW / ONGOING) + their ack; show_all adds RESOLVED and INFO rows."""
    keep = [a for a in alerts if show_all or a["status"] not in (RESOLVED, INSUFFICIENT)]
    return [{**a, "ack": _ack_text(a, state)} for a in keep]


def _known(key: str) -> dict:
    """The newest record for `key` (alerts.jsonl first, then history)."""
    rows = [a for a in _latest() if a["key"] == key] or memory.streak(key, sink.read_history())
    if not rows:
        raise BadFilter(f"unknown alert key: {key} (see `recon alert list --all`)")
    return rows[-1]


def show_list(show_all: bool = False) -> None:
    alerts = _latest()
    if not alerts:
        sys.stdout.write("No alerts yet. Run `recon alerts` (or `make all`) first.\n")
        return
    rows = list_rows(alerts, sink.read_state(), show_all)
    sys.stdout.write(f"Alerts for {alerts[0]['period']} ({len(rows)} shown)\n")
    sys.stdout.write(_table(rows, LIST_COLS) if rows else "No open alerts.\n")


def ack(key: str, note: str = "") -> None:
    period = _known(key)["period"]
    state = sink.read_state()
    state["ack"][key] = {"period": period, "note": note}
    path = sink.write_state(state)
    sys.stdout.write(f"acked {key} at {period} -> {path}\n")


def mute(key: str, until: str, note: str = "") -> None:
    if not WEEK_RE.match(until):
        raise BadFilter(f"bad --until: {until} (expected YYYY-Www, e.g. 2026-W27)")
    _known(key)
    state = sink.read_state()
    state["mute"][key] = {"until": until, "note": note}
    path = sink.write_state(state)
    sys.stdout.write(f"muted {key} until {until} (recorded, not notified) -> {path}\n"
                     "Takes effect on the next `recon alerts`.\n")


def unmute(key: str) -> None:
    state = sink.read_state()
    if state["mute"].pop(key, None) is None:
        raise BadFilter(f"not muted: {key}")
    sys.stdout.write(f"unmuted {key} -> {sink.write_state(state)}\n")


def history(key: str) -> None:
    rows = memory.streak(key, sink.read_history())
    if not rows:
        raise BadFilter(f"no history for {key} (history: {sink.history_path()})")
    sys.stdout.write(f"History of {key} ({len(rows)} periods)\n" + _table(rows, HISTORY_COLS))
