"""Alert record shape (= core.load_alerts() columns) + tiny pure helpers shared by the rules."""

from dataclasses import dataclass, field

import pandas as pd

from casarecon.core.queries.ui_q_base import prev_week

FIRING = "FIRING"  # internal: evaluate.py turns it into NEW / ONGOING
NEW, ONGOING, RESOLVED, INSUFFICIENT = "NEW", "ONGOING", "RESOLVED", "INSUFFICIENT_DATA"
SEVERITY_ORDER = {"SEV2": 0, "SEV3": 1, "INFO": 2}
FIELDS = ("period", "rule_id", "segment", "key", "psp", "country", "severity", "status", "owner",
          "n", "value", "threshold", "message")


@dataclass(frozen=True)
class RuleInput:
    """Everything the rules read. `frame` = core alert_frame; `pending` = core.pending()."""
    frame: pd.DataFrame
    pending: pd.DataFrame
    min_n: int
    money: dict = field(default_factory=dict)  # thresholds.money_leak (warn_pct, crit_pct, weekly_usd)


def record(cfg: dict, week: str, segment: str, *, n: int, value: float, threshold: float,
           message: str, severity: str | None = None, psp: str | None = None,
           country: str | None = None, status: str = FIRING) -> dict:
    rule_id = cfg["id"]
    return {"period": week, "rule_id": rule_id, "segment": segment, "key": f"{rule_id}|{segment}",
            "psp": psp, "country": country, "severity": severity or cfg.get("severity", "SEV3"),
            "status": status, "owner": cfg["owner"], "n": int(n), "value": round(float(value), 4),
            "threshold": round(float(threshold), 4), "message": message}


def insufficient(cfg: dict, week: str, segment: str, n: int, min_n: int, **seg: str | None) -> dict:
    return record(cfg, week, segment, n=n, value=0.0, threshold=min_n, severity="INFO",
                  status=INSUFFICIENT, message=f"Only {n} rows (< {min_n}); not evaluated.", **seg)


def trailing(week: str, k: int) -> list[str]:
    """The k ISO weeks ending at `week`, oldest first."""
    weeks = [week]
    while len(weeks) < k:
        weeks.append(prev_week(weeks[-1]))
    return weeks[::-1]


def seg_of(psp: str | None, country: str | None) -> str:
    return "|".join(x for x in (psp, country) if x) or "ALL"


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def usd(x: float) -> str:
    return f"${x:,.2f}"
