"""Entry point for `recon alerts`: read core -> evaluate rules (pure) -> write jsonl/md -> Slack (opt-in).

Exit 0 even when alerts fire (alerts are output, not errors). Owner: BACKEND.
"""

from pathlib import Path

from casarecon.alerts.evaluate import evaluate
from casarecon.alerts.markdown import render
from casarecon.alerts.record import RuleInput
from casarecon.alerts.sink import write
from casarecon.core import deps, log, paths
from casarecon.core.config import Config, load_config
from casarecon.alerts.rules_money import pending_limits
from casarecon.core.queries.pipeline_q import status
from casarecon.core.queries.ui_q import week_over_week
from casarecon.core.queries.ui_q_alerts import alert_frame
from casarecon.core.queries.ui_q_base import prev_week
from casarecon.ports import Notifier, Store


def _rule(cfg: Config, rule_id: str) -> dict:
    return next((r for r in cfg.alerts.rules if r["id"] == rule_id), {})


def main(*, store: Store | None = None, out_dir: Path | None = None,
         notify: Notifier | None = None, cfg: Config | None = None) -> list[dict]:
    """Evaluate the last closed week; write reports/alerts.jsonl + alerts.md; return the records."""
    cfg = cfg or load_config()
    s = store or deps.get_store()
    st = status(store=s)  # the one week rule (core.weeks): as_of + last closed week
    week, stamp = st["last_closed_week"], st["as_of"]
    prev = prev_week(week)
    late_days = _rule(cfg, "settle_lag").get("late_days", cfg.thresholds.lag_outlier_days)
    frame = alert_frame(late_days, pending_limits(_rule(cfg, "pending_aging"))["age_days"], store=s)
    data = RuleInput(frame=frame, min_n=cfg.thresholds.min_sample.alerts,
                     money=cfg.thresholds.money_leak.model_dump())
    alerts = evaluate(data, list(cfg.alerts.rules), week, prev)
    md = render(alerts, week=week, prev=prev, as_of=stamp.isoformat(sep=" "), frame=data.frame,
                wow=week_over_week(store=s), weekly_usd=data.money["weekly_usd"])
    jsonl, _ = write(out_dir or paths.reports_dir(), alerts, md)
    log.get("alerts").info(log.kv(step="alerts", period=week, rows=len(alerts),
                                  fired=sum(a["status"] in ("NEW", "ONGOING") for a in alerts),
                                  out=jsonl))
    if cfg.alerts.slack.get("enabled"):
        (notify or deps.get_notifier())(md)
    return alerts
