"""Recommendations (pure): action catalogue + ranking by estimated saving.

saving = finding usd_quarter (excess loss) x the action's reduction share (an assumption,
always printed next to the number).
"""

MAX_RECS = 5

# (action, owner, implementation, reduction share); {psp} / {country} come from the finding
PEER = ("Escalate {psp} {country} variance; renegotiate settlement terms", "Payments ops",
        "Weekly variance report to {psp}; SLA clause with credit on excess", 0.5)
ROUNDING = ("Get {psp} to stop rounding cross-border settlements", "Eng + {psp}",
            "Ticket with signature evidence; monitor `rounding_flag` share weekly", 0.7)
FEE = ("Dispute the new {psp} per-transaction fee", "Finance",
       "Compare with contract (`psp_fees` = 0); claim back since the drift started", 0.7)
ADJUSTMENT = ("Escalate {psp} settlement adjustments", "Payments ops",
              "Ask {psp} for reason codes on every adjustment; dispute the unexplained ones", 0.5)
LAG = ("Settlement SLA for {country} orders over $300", "PSP ops",
       "Track lag p90; escalate > 7 days", 0.5)
FX_LOCK = ("Lock the FX rate at authorization for cross-border payments", "Finance",
           "Yuno / PSP rate-lock option", 0.5)
RECONCILE = ("Reconcile partial captures and holds to order changes", "Ops",
             "Join order events; auto-close explained rows", 0.3)

BY_KIND = {"peer": PEER, "fee_drift": FEE, "lag": LAG, "cross_border": FX_LOCK,
           "partial_capture": RECONCILE, "fraud_hold": RECONCILE}
BY_CAUSE = {"psp_rounding": ROUNDING, "psp_fee": FEE, "psp_adjustment": ADJUSTMENT}
PEER_BY_CAUSE = {"psp_rounding": ROUNDING, "psp_fee": FEE}  # a PSP habit beats a generic escalation


def _entry(f: dict) -> tuple[str, str, str, float] | None:
    cause = f.get("likely_cause")
    if f["kind"] == "cause_psp":
        return BY_CAUSE.get(cause)
    if f["kind"] == "peer":
        return PEER_BY_CAUSE.get(cause, PEER)
    return BY_KIND.get(f["kind"])


def catalogue_entry(f: dict) -> tuple[str, str, str, float] | None:
    """Catalogue row for a finding, or None when there is no action for it."""
    entry = _entry(f)
    if entry is None:
        return None
    action, owner, impl, reduction = entry
    names = {"psp": f.get("psp") or "the PSP", "country": f.get("country") or ""}
    return action.format(**names), owner.format(**names), impl.format(**names), reduction


def recommend(findings: list[dict], max_recs: int = MAX_RECS) -> list[dict]:
    """Top actions by saving. Findings that map to the same action are merged: evidence lists all,
    saving is the largest one (their excess losses overlap, so they are not added)."""
    merged: dict[str, dict] = {}
    for f in findings:
        entry = catalogue_entry(f)
        if entry is None:
            continue
        action, owner, impl, reduction = entry
        row = merged.setdefault(action, {"action": action, "owner": owner, "implementation": impl,
                                         "reduction_pct": round(reduction * 100), "evidence": [],
                                         "usd_quarter": 0.0})
        row["evidence"].append(f["id"])
        row["usd_quarter"] = max(row["usd_quarter"], (f["usd_quarter"] or 0.0) * reduction)
    ranked = sorted(merged.values(), key=lambda r: (-r["usd_quarter"], r["action"]))[:max_recs]
    return [{**r, "rank": i, "id": f"R{i}", "evidence": ", ".join(r["evidence"]),
             "usd_quarter": round(r["usd_quarter"], 2),
             "method": f"excess loss × {r['reduction_pct']}%"} for i, r in enumerate(ranked, 1)]


def rec_refs(recs: list[dict]) -> dict[str, str]:
    """{finding id: 'R2'} for the FINDINGS 'Action' line."""
    return {fid: r["id"] for r in recs for fid in r["evidence"].split(", ")}
