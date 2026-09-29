"""Run every rule for W and W-1 and derive NEW / ONGOING / RESOLVED without a state file. Pure."""

from collections.abc import Callable

from casarecon.alerts.group import group_peers
from casarecon.alerts.record import (
    FIRING,
    INSUFFICIENT,
    NEW,
    ONGOING,
    RESOLVED,
    RULE_FIELDS,
    SEVERITY_ORDER,
    RuleInput,
)
from casarecon.alerts.rules_money import large_rows, money_leak, pending_aging
from casarecon.alerts.rules_rate import change, peer, settle_lag

Rule = Callable[[RuleInput, dict, str], list[dict]]
RULES: dict[str, Rule] = {"peer": peer, "change": change, "money_leak": money_leak,
                          "large_rows": large_rows, "pending_aging": pending_aging,
                          "settle_lag": settle_lag}
AS_OF_ONLY = {"pending_aging"}  # measured at as_of: no previous week, always NEW
POST = {"peer": group_peers}  # optional clean-up per rule: (rows, cfg, week) -> rows


def _psp_wide(r: dict) -> str:
    """Key of the grouped PSP-wide alert that would cover `r` (see group.py)."""
    return f"{r['rule_id']}|{r['psp']}|ALL"


def with_status(now: list[dict], before: list[dict], week: str) -> list[dict]:
    """Fires now: NEW / ONGOING (fired in W-1 too). Fired only in W-1: RESOLVED (period = W).
    A PSP-wide alert continues any W-1 alert of the same PSP, so neither side flips."""
    fired_before = {r["key"]: r for r in before if r["status"] == FIRING}
    wide_before = {_psp_wide(r) for r in fired_before.values() if r["psp"]}
    seen = {r["key"] for r in now}
    ongoing = set(fired_before) | wide_before
    out = [r if r["status"] == INSUFFICIENT else
           {**r, "status": ONGOING if r["key"] in ongoing else NEW} for r in now]
    out += [{**r, "period": week, "status": RESOLVED, "message": f"Resolved: {r['message']}"}
            for key, r in fired_before.items()
            if key not in seen and not (r["psp"] and _psp_wide(r) in seen)]
    return out


def sort_alerts(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), r["rule_id"],
                                          r["segment"]))
    return [{f: r[f] for f in RULE_FIELDS} for r in ordered]


def run_rule(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    rows = RULES[cfg["id"]](data, cfg, week)
    post = POST.get(cfg["id"])
    return post(rows, cfg, week) if post else rows


def evaluate(data: RuleInput, rules: list[dict], week: str, prev: str) -> list[dict]:
    """All rules in alerts.yaml order -> sorted alert records for `week` (last closed)."""
    out: list[dict] = []
    for cfg in rules:
        before = [] if cfg["id"] in AS_OF_ONLY else run_rule(data, cfg, prev)
        out += with_status(run_rule(data, cfg, week), before, week)
    return sort_alerts(out)
