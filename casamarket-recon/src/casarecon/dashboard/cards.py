"""Pure text for the Overview cards (worst-week card, KPI values). No Streamlit here."""

import pandas as pd

from casarecon.dashboard import data
from casarecon.dashboard import format as fmt

LOW = "low sample (n<30)"


def _week(row: pd.Series) -> str:
    start, end = data.to_date(row["week_start"]), data.to_date(row["week_end"])
    return fmt.week_label(row["auth_week"], start, end)


def worst_headline(row: pd.Series) -> str:
    """'PSP_B · W24 (Jun 8–14) · Net loss $4,210.00 · Gross under $4,900.00'."""
    return (f"{row['psp']} · {_week(row)} · Net loss {fmt.usd(row['net_usd'])} · "
            f"Gross under {fmt.usd(row['gross_under_usd'])}")


def worst_detail(row: pd.Series) -> str:
    """'Flag rate 21.3% · n = 812' (+ ' · low sample (n<30)')."""
    low = f" · {LOW}" if bool(row["low_sample"]) else ""
    return f"Flag rate {fmt.rate(row['rate'])} · n = {fmt.count(row['n'])}{low}"


def next_line(ranked: pd.DataFrame, k: int = 3) -> str:
    """'Next: PSP_C W25 $3,050 · PSP_E W26 $900 (low sample)' from ranks 2..k+1."""
    items = [f"{r['psp']} {r['auth_week'].split('-')[-1]} {fmt.usd_compact(r['net_usd'])}"
             + (" (low sample)" if bool(r["low_sample"]) else "")
             for _, r in ranked.iloc[1:k + 1].iterrows()]
    return "Next: " + " · ".join(items) if items else "No other PSP-weeks this month."


def link_label(row: pd.Series, page: str) -> str:
    return f"Open {row['psp']} · {row['auth_week'].split('-')[-1]} in {page} →"


def open_alerts(alerts: pd.DataFrame | None) -> tuple[str, str]:
    """(value, caption) for the Open alerts KPI: NEW/ONGOING, not INFO. Missing file -> '—'."""
    if alerts is None:
        return "—", "Run `recon alerts`"
    live = alerts[alerts["status"].isin(["NEW", "ONGOING"]) & (alerts["severity"] != "INFO")]
    sev2 = int((live["severity"] == "SEV2").sum())
    return (f"{len(live)} ({sev2} SEV2)" if sev2 else str(len(live))), "NEW or ONGOING"
