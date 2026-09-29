"""Pure helpers for the Alerts page: badges, rule names, sort order, counts, segment links.

The evaluator (`recon alerts`) decides status and severity; nothing here recomputes them.
"""

import pandas as pd

from casarecon.dashboard import theme

# rule id -> (name, the question it answers in plain English, when it fires)
RULES = {
    "peer": ("Peer", "Is this PSP worse than the other PSPs in the same country?",
             "Flag rate over the last 4 closed weeks is at least 2 pts above peers and the gap is "
             "significant (q < 0.05). SEV2."),
    "change": ("Change", "Is this week worse than usual?",
               "Last closed week is above the normal range of the 8 weeks before it (3 sigma). SEV3."),
    "money_leak": ("Money leak", "Are we losing more money than usual?",
                   "Under-settled USD is more than 1.5% of settled USD (SEV3) or 2.5% (SEV2)."),
    "large_rows": ("Large rows", "How many rows need a closer look?",
                   "Any large rows last closed week: one summary with count, $ and the top 3 "
                   "segments. SEV3."),
    "pending_aging": ("Pending aging", "Is money stuck unsettled?",
                      "Share of pending rows older than 7 days is over 10% (SEV3) or 25% (SEV2)."),
    "settle_lag": ("Settle lag", "Are orders settling late?",
                   "More than 6% of a country × size tier settles after 7 days (last 4 weeks). SEV3."),
}
SEV_ORDER = {"SEV2": 0, "SEV3": 1, "INFO": 2}
STATUS_ORDER = {"NEW": 0, "ONGOING": 1, "RESOLVED": 2, "INSUFFICIENT_DATA": 3}
OPEN = ("NEW", "ONGOING")
TIERS = ("10-50", "50-200", "200+")


def rule_name(rule_id: str) -> str:
    return RULES.get(rule_id, (rule_id,))[0]


def badge(severity: str, status: str) -> str:
    """'▲ SEV2 · same day'; resolved rows read '✓ Resolved · was SEV2' (icon + word)."""
    if status == "RESOLVED":
        return f"{theme.RESOLVED[1]} · was {severity}"
    return theme.SEVERITY.get(severity, ("", severity))[1]


def segment_text(segment: str) -> str:
    """'PSP_B|AR' -> 'PSP_B · AR'; 'ALL' -> 'All'."""
    return "All" if segment == "ALL" else str(segment).replace("|", " · ")


def split(alerts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(active rows sorted SEV2 -> INFO then NEW -> RESOLVED, INSUFFICIENT_DATA rows)."""
    insufficient = alerts["status"] == "INSUFFICIENT_DATA"
    active = alerts[~insufficient].assign(
        _s=alerts["severity"].map(SEV_ORDER), _t=alerts["status"].map(STATUS_ORDER)
    ).sort_values(["_s", "_t", "rule_id", "segment"]).drop(columns=["_s", "_t"])
    return active.reset_index(drop=True), alerts[insufficient].reset_index(drop=True)


def counts(alerts: pd.DataFrame) -> dict[str, int]:
    """Open SEV2, open SEV3, Info (incl. insufficient data), Resolved."""
    is_open = alerts["status"].isin(OPEN)
    return {"SEV2": int((is_open & (alerts["severity"] == "SEV2")).sum()),
            "SEV3": int((is_open & (alerts["severity"] == "SEV3")).sum()),
            "INFO": int((alerts["severity"] == "INFO").sum()),
            "RESOLVED": int((alerts["status"] == "RESOLVED").sum())}


def pick(active: pd.DataFrame, **chosen: list[str]) -> pd.DataFrame:
    """Keep rows whose column value is in the chosen list; an empty list means all."""
    keep = pd.Series(True, index=active.index)
    for column, values in chosen.items():
        if values:
            keep &= active[column].isin(values)
    return active[keep].reset_index(drop=True)


def table(active: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Severity": [badge(s, t) for s, t in zip(active["severity"], active["status"])],
        "Status": active["status"], "Rule": active["rule_id"].map(rule_name),
        "Segment": active["segment"].map(segment_text), "Message": active["message"],
        "Owner": active["owner"], "n": active["n"]})


def handoff(row: pd.Series) -> dict:
    """Drill-down filters for one alert: psp, country, and size tier for settle-lag segments."""
    out: dict = {}
    for name in ("psp", "country"):
        if isinstance(row.get(name), str):
            out[name] = [row[name]]
    tier = [p for p in str(row["segment"]).split("|") if p in TIERS]
    if tier:
        out["tier"] = tier
    return out
