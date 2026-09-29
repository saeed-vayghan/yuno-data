"""reports/alerts.md as a pure string (no template file needed). Deterministic: no wall-clock."""

from collections import Counter

import pandas as pd

from casarecon.alerts.record import INSUFFICIENT, NEW, ONGOING, usd


def money_lines(frame: pd.DataFrame, week: str) -> dict:
    cur = frame[frame["auth_week"] == week]
    under, over = float(cur["gross_under_usd"].sum()), float(cur["gross_over_usd"].sum())
    return {"under": round(under, 2), "over": round(over, 2), "net": round(under - over, 2)}


def _cell(value: object) -> str:
    """Escape '|' (segments are 'PSP_B|AR') so it does not split a Markdown table cell."""
    return str(value).replace("|", "\\|")


def _arrow(delta: float) -> str:
    if pd.isna(delta):
        return "n/a"
    return f"▲ +{delta:.1f} pts (worse)" if delta > 0 else f"▼ {delta:.1f} pts (better)"


def _wow_rows(wow: pd.DataFrame, top: int) -> list[str]:
    rows = wow if wow.empty else wow[~wow["low_sample"].astype(bool)].head(top)
    lines = [f"| {r.psp} | {r.country} | {r.rate_prev:.1%} | {r.rate_last:.1%} | {_arrow(r.delta_pts)} |"
             for r in rows.itertuples()]
    return lines or ["| - | - | - | - | all segments low sample |"]


def render(alerts: list[dict], *, week: str, prev: str, as_of: str, frame: pd.DataFrame,
           wow: pd.DataFrame, weekly_usd: float, top: int = 10) -> str:
    counts = Counter(a["severity"] for a in alerts if a["status"] in (NEW, ONGOING))
    live = [a for a in alerts if a["status"] != INSUFFICIENT]
    thin = [a for a in alerts if a["status"] == INSUFFICIENT]
    now, before = money_lines(frame, week), money_lines(frame, prev)
    out = [f"# Alerts: {week}", "", f"As of {as_of} (data time). Last closed week {week}, "
           f"compared with {prev}.", "",
           f"**Open SEV2:** {counts['SEV2']} · **Open SEV3:** {counts['SEV3']} · "
           f"**Insufficient data:** {len(thin)}", "", "## Alerts", ""]
    if live:
        out += ["| Severity | Status | Open since | Rule | Segment | Owner | Message |",
                "|---|---|---|---|---|---|---|"]
        out += ["| " + " | ".join(_cell(v) for v in (
            a["severity"], a["status"] + (" (muted)" if a.get("muted") else ""),
            a.get("open_since") or "-", a["rule_id"], a["segment"], a["owner"], a["message"])) + " |"
            for a in live]
    else:
        out.append("No alerts fired.")
    out += ["", "## Money", "", f"| | {prev} | {week} |", "|---|---|---|"]
    out += [f"| {label} | {usd(before[k])} | {usd(now[k])} |"
            for label, k in (("Gross under", "under"), ("Gross over", "over"), ("Net", "net"))]
    out += ["", f"Reference line: {usd(weekly_usd)} a week (the CFO's quarterly loss / 13).", "",
            "## Week over week (flag rate)", "", "| PSP | Country | Prev | Last | Change |",
            "|---|---|---|---|---|", *_wow_rows(wow, top), "", "## Insufficient data", "",
            f"<details><summary>{len(thin)} segments not evaluated</summary>", ""]
    out += [f"- {a['rule_id']} {a['segment']}: {a['message']}" for a in thin] or ["None."]
    out += ["", "</details>"]
    return "\n".join(out) + "\n"
