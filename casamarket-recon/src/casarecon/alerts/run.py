"""Entry point for `recon alerts`: read core -> evaluate rules (pure) -> alert memory (open_since,
mute) -> route + dedupe -> write jsonl / md / outbox + history -> Slack (opt-in).

Exit 0 even when alerts fire (alerts are output, not errors). Owner: ALERTS.
"""

from pathlib import Path

from casarecon.alerts import memory, sink
from casarecon.alerts import notify as routing
from casarecon.alerts.evaluate import evaluate
from casarecon.alerts.markdown import render
from casarecon.alerts.record import RuleInput
from casarecon.alerts.rules_money import pending_limits
from casarecon.core import deps, log, paths
from casarecon.core.config import Config, load_config
from casarecon.core.queries.pipeline_q import status
from casarecon.core.queries.ui_q import week_over_week
from casarecon.core.queries.ui_q_alerts import alert_frame
from casarecon.core.queries.ui_q_base import prev_week
from casarecon.ports import Notifier, Store


def _rule(cfg: Config, rule_id: str) -> dict:
    return next((r for r in cfg.alerts.rules if r["id"] == rule_id), {})


def remember(alerts: list[dict], week: str, history: list[dict], state: dict,
             slack_cfg: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Pure: (annotated alerts, outbox, new history). Only periods before `week` are read, and
    `week`'s old lines are replaced, so re-running the same week gives the same bytes."""
    prior = memory.before(history, week)
    alerts = memory.annotate(alerts, prior, state)
    outbox = routing.plan(alerts, prior, routing.routing_of(slack_cfg))
    lines = memory.history_lines(alerts, routing.sent_map(outbox))
    return alerts, outbox, memory.replace_period(history, week, lines)


def main(*, store: Store | None = None, out_dir: Path | None = None,
         notify: Notifier | None = None, cfg: Config | None = None) -> list[dict]:
    """Evaluate the last closed week; write reports/alerts.jsonl + alerts.md + notifications.jsonl
    and data/alerts/history.jsonl; return the records."""
    cfg = cfg or load_config()
    s = store or deps.get_store()
    st = status(store=s)  # the one week rule (core.weeks): as_of + last closed week
    week, stamp = st["last_closed_week"], st["as_of"]
    prev = prev_week(week)
    late_days = _rule(cfg, "settle_lag").get("late_days", cfg.thresholds.lag_outlier_days)
    frame = alert_frame(late_days, pending_limits(_rule(cfg, "pending_aging"))["age_days"], store=s)
    data = RuleInput(frame=frame, min_n=cfg.thresholds.min_sample.alerts,
                     money=cfg.thresholds.money_leak.model_dump())
    alerts, outbox, history = remember(evaluate(data, list(cfg.alerts.rules), week, prev), week,
                                       sink.read_history(), sink.read_state(), cfg.alerts.slack)
    md = render(alerts, week=week, prev=prev, as_of=stamp.isoformat(sep=" "), frame=data.frame,
                wow=week_over_week(store=s), weekly_usd=data.money["weekly_usd"])
    jsonl, _ = sink.write(out_dir or paths.reports_dir(), alerts, md, outbox)
    sink.write_history(history)
    log.get("alerts").info(log.kv(step="alerts", period=week, rows=len(alerts),
                                  fired=sum(a["status"] in ("NEW", "ONGOING") for a in alerts),
                                  outbox=len(outbox), out=jsonl))
    text = routing.slack_text(outbox)
    if cfg.alerts.slack.get("enabled") and text:
        (notify or deps.get_notifier())(text)
    return alerts
