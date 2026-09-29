"""Routing + dedupe (pure): which alerts would be sent, where, and as trigger or resolve.

Routing: SEV2 / SEV3 -> `outbox` (the local file reports/notifications.jsonl, always written) +
`slack` when the severity is in alerts.yaml `slack.severities`; INFO -> nothing. INSUFFICIENT_DATA
and muted alerts are never sent. NEW -> trigger. ONGOING -> trigger only if no trigger was sent yet
in its open streak (history tells us). RESOLVED -> resolve. Dedupe key = alert key + period.
Slack only posts when `slack.enabled` and env SLACK_WEBHOOK_URL are both set (off by default).
"""

from casarecon.alerts.record import INSUFFICIENT, NEW, ONGOING, RESOLVED

NOTIFY_SEVERITIES = ("SEV2", "SEV3")  # INFO is report-only
DEFAULT_SLACK_SEVERITIES = ("SEV2", "SEV3")
OUTBOX_FIELDS = ("dedupe_key", "action", "channels", "period", "key", "severity", "status",
                 "owner", "open_since", "message")


def routing_of(slack_cfg: dict) -> dict[str, list[str]]:
    """severity -> channels, from alerts.yaml `slack: {severities: [...]}`."""
    to_slack = slack_cfg.get("severities", DEFAULT_SLACK_SEVERITIES)
    return {s: ["outbox", *(["slack"] if s in to_slack else [])] for s in NOTIFY_SEVERITIES}


def already_sent(alert: dict, prior: list[dict]) -> bool:
    """A trigger for this key was sent in an earlier period of the current open streak."""
    since = alert["open_since"] or alert["period"]
    return any(h["key"] == alert["key"] and h.get("sent") == "trigger"
               and since <= h["period"] < alert["period"] for h in prior)


def action_of(alert: dict, prior: list[dict]) -> str | None:
    if alert["status"] == INSUFFICIENT or alert["muted"]:
        return None
    if alert["status"] == NEW:
        return "trigger"
    if alert["status"] == ONGOING:
        return None if already_sent(alert, prior) else "trigger"
    return "resolve" if alert["status"] == RESOLVED else None


def plan(alerts: list[dict], prior: list[dict], routing: dict[str, list[str]]) -> list[dict]:
    """Outbox lines, in alert order. `prior` = history of earlier periods (memory.before)."""
    out = []
    for a in alerts:
        channels = list(routing.get(a["severity"], []))
        action = action_of(a, prior) if channels else None
        if action:
            row = {**a, "dedupe_key": f"{a['key']}|{a['period']}", "action": action,
                   "channels": channels}
            out.append({f: row[f] for f in OUTBOX_FIELDS})
    return out


def sent_map(outbox: list[dict]) -> dict[str, str]:
    """key -> action, stored in history so the next period can dedupe."""
    return {o["key"]: o["action"] for o in outbox}


def slack_text(outbox: list[dict]) -> str:
    """One Slack message for the lines routed to slack (empty string = nothing to post)."""
    lines = [f"[{o['action'].upper()}] {o['severity']} {o['key']} (open since {o['open_since']}): "
             f"{o['message']}" for o in outbox if "slack" in o["channels"]]
    return "\n".join(lines)
