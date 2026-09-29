"""Pure table views: TXN_COLUMNS frame -> display frame + column config. No queries here.

Numeric columns stay numeric (sort works); text columns are added beside them.
"""

import re

import pandas as pd
import streamlit as st

from casarecon.dashboard import format as fmt

MASKED = re.compile(r"^.*••••.{0,4}$")
OUTLIER_COLUMNS = ["transaction_id", "auth_date", "psp_country", "residual_usd", "direction",
                   "raw_diff", "customer", "why_flagged", "likely_cause", "settle_lag_days"]


def ensure_masked(customer: object) -> object:
    """Defence in depth: core masks; if a raw ID ever slips through, keep only the last 4."""
    if not isinstance(customer, str) or MASKED.match(customer):
        return customer
    prefix, _, token = customer.rpartition("_")
    return f"{prefix + '_' if prefix else ''}••••{token[-4:]}"


def outlier_view(rows: pd.DataFrame) -> pd.DataFrame:
    """Display frame for the Outliers table (same row order as core: largest first)."""
    v = rows.copy()
    v["psp_country"] = v["psp"] + " · " + v["country"]
    v["raw_diff"] = [fmt.local(d, c, e)
                     for d, c, e in zip(v["diff_local"], v["currency"], v["exponent"])]
    v["customer"] = v["customer"].map(ensure_masked)
    return v[OUTLIER_COLUMNS].reset_index(drop=True)


def outlier_columns() -> dict:
    col = st.column_config
    return {
        "transaction_id": col.TextColumn("Transaction"),
        "auth_date": col.DateColumn("Auth date", format="YYYY-MM-DD"),
        "psp_country": col.TextColumn("PSP · Country"),
        "residual_usd": col.NumberColumn("Discrepancy after FX (USD)", format="$%.2f",
                                         help="Settled minus expected settle, FX move removed, in USD."),
        "direction": col.TextColumn("Under / over"),
        "raw_diff": col.TextColumn("Raw difference (local)",
                                   help="Raw difference in local currency (FX move not removed)."),
        "customer": col.TextColumn("Customer", help="Masked: only the last 4 characters."),
        "why_flagged": col.TextColumn("Why flagged"),
        "likely_cause": col.TextColumn("Likely cause"),
        "settle_lag_days": col.NumberColumn("Lag (days)", format="%.1f"),
    }


def summary_line(n: int, under: float, over: float) -> str:
    """'1,284 transactions · $148,210.00 under · $3,020.00 over'."""
    return f"{fmt.count(n)} transactions · {fmt.usd(under)} under · {fmt.usd(over)} over"


def cap_note(shown: int, total: int) -> str | None:
    if total <= shown:
        return None
    return f"Showing {fmt.count(shown)} of {fmt.count(total)}, largest first. Download CSV for all."


def detail_lines(row: pd.Series) -> list[str]:
    """Why-flagged panel for one TXN row (rich detail waits on core transaction_detail)."""
    money = [(label, row[col]) for label, col in (("Authorized", "authorized_amount"),
             ("Expected settle", "expected_settled"), ("Settled", "settled_amount"))]
    lines = [f"**{label}** {fmt.local(v, row['currency'], row['exponent'])}" for label, v in money]
    xb = "cross-border" if bool(row["is_cross_border"]) else "domestic"
    lines += [
        f"**Discrepancy after FX** {fmt.usd_signed(row['residual_usd'])} "
        f"({fmt.pct_signed(row['residual_pct'])}) · {xb}",
        f"**Why flagged** {row['why_flagged']} · **Likely cause** {row['likely_cause']}",
        f"**Lag** {row['settle_lag_days']:.1f} days · **Size tier** {row['amount_tier']} · "
        f"**Customer** {ensure_masked(row['customer'])}",
    ]
    return lines
