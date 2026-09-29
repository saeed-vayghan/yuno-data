"""Alert memory (pure): open_since from history, mute / ack from alert_state, history lines.

History = one line per alert per evaluated period (data/alerts/history.jsonl). Only periods
*before* the one being evaluated are read, and re-running a period replaces its lines, so the
same period twice gives the same output (byte-stable reports).
"""

from casarecon.alerts.record import FIELDS, INSUFFICIENT, NEW, ONGOING, RESOLVED
from casarecon.core.queries.ui_q_base import prev_week

OPEN = (NEW, ONGOING)
HISTORY_FIELDS = ("period", "key", "rule_id", "severity", "status", "open_since", "muted", "sent")


def before(history: list[dict], period: str) -> list[dict]:
    """History lines of earlier periods only (the current period is being re-evaluated)."""
    return [h for h in history if h["period"] < period]


def _streak_start(end: str, fired: set[str]) -> str:
    """Walk back from `end` while the previous week also fired."""
    start = end
    while prev_week(start) in fired:
        start = prev_week(start)
    return start


def open_since(alert: dict, history: list[dict]) -> str | None:
    """First period of the current open streak. NEW -> this period. ONGOING / RESOLVED: it fired
    in W-1 (evaluate.py proved it), so walk back from W-1 through history. No history -> W-1."""
    status, period = alert["status"], alert["period"]
    if status == NEW:
        return period
    if status not in (ONGOING, RESOLVED):
        return None
    fired = {h["period"] for h in history if h["key"] == alert["key"] and h["status"] in OPEN}
    return _streak_start(prev_week(period), fired)


def is_muted(key: str, period: str, state: dict) -> bool:
    """Muted while period <= until (ISO weeks 'YYYY-Www' compare as strings)."""
    entry = (state.get("mute") or {}).get(key)
    return bool(entry) and period <= str(entry.get("until", ""))


def ack_of(alert: dict, state: dict) -> dict | None:
    """The ack entry if it belongs to the current streak (acked at or after open_since)."""
    entry = (state.get("ack") or {}).get(alert["key"])
    since = alert.get("open_since")
    return entry if entry and since and str(entry.get("period", "")) >= since else None


def annotate(alerts: list[dict], prior: list[dict], state: dict) -> list[dict]:
    """Add open_since + muted to each record (FIELDS order = alerts.jsonl). prior = before(...)."""
    out = []
    for a in alerts:
        extra = {"open_since": open_since(a, prior),
                 "muted": a["status"] != INSUFFICIENT and is_muted(a["key"], a["period"], state)}
        out.append({f: {**a, **extra}[f] for f in FIELDS})
    return out


def history_lines(alerts: list[dict], sent: dict[str, str]) -> list[dict]:
    """One history line per alert; `sent` = key -> 'trigger' | 'resolve' for this period."""
    return [{f: {**a, "sent": sent.get(a["key"])}[f] for f in HISTORY_FIELDS} for a in alerts]


def replace_period(history: list[dict], period: str, lines: list[dict]) -> list[dict]:
    """Drop `period`'s old lines, add the new ones; keep periods in order (stable within one)."""
    kept = [h for h in history if h["period"] != period]
    return sorted(kept + lines, key=lambda h: h["period"])


def streak(key: str, history: list[dict]) -> list[dict]:
    """History lines of one key, oldest first (for `recon alert history KEY`)."""
    return [h for h in history if h["key"] == key]

