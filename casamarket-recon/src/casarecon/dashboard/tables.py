"""Pure table views: TXN_COLUMNS frame -> display frame + column config. No queries here.

Numeric columns stay numeric (sort works); text columns are added beside them.
"""

import re

import pandas as pd
import streamlit as st

from casarecon.dashboard import format as fmt
from casarecon.dashboard import theme

MASKED = re.compile(r"^.*••••.{0,4}$")
OUTLIER_COLUMNS = ["transaction_id", "auth_date", "psp_country", "residual_usd", "direction",
                   "raw_diff", "customer", "why_flagged", "cause", "settle_lag_days"]
DRILL_COLUMNS = ["transaction_id", "auth_date", "psp_country", "category_label", "cause",
                 "residual_usd", "raw_diff", "settle_lag_days"]


def ensure_masked(customer: object) -> object:
    """Defence in depth: core masks; if a raw ID ever slips through, keep only the last 4."""
    if not isinstance(customer, str) or MASKED.match(customer):
        return customer
    prefix, _, token = customer.rpartition("_")
    return f"{prefix + '_' if prefix else ''}••••{token[-4:]}"


def txn_view(rows: pd.DataFrame, columns: list[str] = OUTLIER_COLUMNS) -> pd.DataFrame:
    """Display frame for a TXN_COLUMNS frame (same row order as core: largest first)."""
    v = rows.copy()
    v["psp_country"] = v["psp"] + " · " + v["country"]
    v["raw_diff"] = [fmt.local(d, c, e)
                     for d, c, e in zip(v["diff_local"], v["currency"], v["exponent"])]
    v["customer"] = v["customer"].map(ensure_masked)
    v["cause"] = v["likely_cause"].map(theme.cause_label)
    v["category_label"] = v["category"].map(lambda c: theme.CATEGORY_LABELS.get(c, c))
    return v[columns].reset_index(drop=True)


def txn_columns() -> dict:
    col = st.column_config
    return {
        "transaction_id": col.TextColumn("Transaction"),
        "auth_date": col.DateColumn("Auth date", format="YYYY-MM-DD"),
        "psp_country": col.TextColumn("PSP · Country"),
        "residual_usd": col.NumberColumn("Discrepancy after FX (USD)", format="dollar",
                                         help="Settled minus expected settle, FX move removed, in USD."),
        "direction": col.TextColumn("Under / over"),
        "raw_diff": col.TextColumn("Raw difference (local)",
                                   help="Raw difference in local currency (FX move not removed)."),
        "customer": col.TextColumn("Customer", help="Masked: only the last 4 characters."),
        "why_flagged": col.TextColumn("Why flagged"),
        "cause": col.TextColumn("Likely cause"),
        "category_label": col.TextColumn("Category"),
        "settle_lag_days": col.NumberColumn("Lag (days)", format="%.1f"),
    }


def summary_line(n: int, under: float, over: float) -> str:
    """'1,284 transactions · $148,210.00 under · $3,020.00 over'."""
    return f"{fmt.count(n)} transactions · {fmt.usd(under)} under · {fmt.usd(over)} over"


def cap_note(shown: int, total: int, csv: bool = True) -> str | None:
    if total <= shown:
        return None
    tail = " Download CSV for all." if csv else ""
    return f"Showing {fmt.count(shown)} of {fmt.count(total)}, largest first.{tail}"


def _money(d: dict, col: str, usd_col: str | None = None) -> str:
    text = fmt.local(d[col], d["currency"], d["exponent"])
    return f"{text} ({fmt.usd(d[usd_col])})" if usd_col and d.get(usd_col) is not None else text


def detail_lines(d: dict) -> list[str]:
    """Why-flagged panel. `d` = core transaction_detail (or a TXN row: extras are optional)."""
    xb = "cross-border" if bool(d["is_cross_border"]) else "domestic"
    fx = d.get("fx_move_pct")
    fx_text = f"FX move {fmt.pct_signed(fx)} ({xb})" if fx is not None else xb.capitalize()
    extras = [f"{label} {fmt_fn(d[key])}" for key, label, fmt_fn in (
        ("is_weekend", "Weekend:", lambda v: "yes" if v else "no"),
        ("item_count", "Items", str), ("risk_score", "Risk score", lambda v: f"{v:.2f}"))
        if d.get(key) is not None]
    cause = d.get("likely_cause")
    cause_line = theme.CAUSES.get(cause, ("", ""))[1] if isinstance(cause, str) else ""
    return [
        f"**Authorized** {_money(d, 'authorized_amount', 'amount_usd')} · "
        f"**Expected settle** {_money(d, 'expected_settled')}",
        f"**Settled** {_money(d, 'settled_amount', 'settled_usd')} · {fx_text}",
        " · ".join([f"Lag {d['settle_lag_days']:.1f} days", *extras]),
        f"**Why flagged:** {fmt.usd_signed(d['residual_usd'])} after FX "
        f"({fmt.pct_signed(d['residual_pct'])}) · {d['why_flagged']}",
        f"**Likely cause:** {theme.cause_label(cause)}" + (f" ({cause_line})" if cause_line else ""),
    ]
