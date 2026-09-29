"""Formatting for `recon query` / `recon worst-week`: calls core, prints. Owner: INFRA.

No metric logic here: if a number differs from the dashboard, the bug is in core.
"""

import json
import sys

import pandas as pd

from casarecon import core
from casarecon.core.errors import BadFilter

TABLE_ROWS = 50
WORST_KEYS = ("psp", "auth_week", "week_start", "week_end", "n", "rate", "net_usd",
              "gross_under_usd", "low_sample")


def _check(fmt: str, allowed: tuple[str, ...]) -> None:
    if fmt not in allowed:
        raise BadFilter(f"unknown format: {fmt} (allowed: {', '.join(allowed)})")


def _jsonable(v: object) -> object:
    """json.dumps fallback: numpy scalars -> Python, dates -> 'YYYY-MM-DD'."""
    return v.item() if hasattr(v, "item") else v.isoformat() if hasattr(v, "isoformat") else str(v)


def _records(df: pd.DataFrame) -> list[dict]:
    """Plain-Python rows; NaN/NaT -> None."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _print_json(obj: object) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2, default=_jsonable) + "\n")


def query(min_usd: float | None, psp: tuple[str, ...], country: tuple[str, ...],
          limit: int | None, fmt: str) -> None:
    """core.query_transactions(Filters(psp=psp, country=country), min_usd, limit) -> table|csv|json."""
    _check(fmt, ("table", "csv", "json"))
    df = core.query_transactions(core.Filters(psp=psp, country=country), min_usd, limit)
    if fmt == "csv":
        sys.stdout.reconfigure(encoding="utf-8")
        df.to_csv(sys.stdout, index=False, lineterminator="\n")
    elif fmt == "json":
        _print_json(_records(df))
    else:
        cols = ["transaction_id", "auth_date", "psp", "country", "category", "likely_cause",
                "residual_usd", "residual_pct", "customer"]
        print(df[cols].head(TABLE_ROWS).to_string(index=False) if len(df) else "no rows")
        print(f"\n{len(df)} rows over ${min_usd}; use --format csv for all")


def worst_week(month: str, fmt: str) -> None:
    """core.worst_week(month) -> table|json ({'month', 'worst', 'ranking'})."""
    _check(fmt, ("table", "json"))
    resolved = core.status()["last_full_month"] if month == "last" else month
    df = core.worst_week(month)
    if fmt == "json":
        ranking = _records(df)
        worst = {k: ranking[0][k] for k in WORST_KEYS} if ranking else None
        _print_json({"month": resolved, "worst": worst, "ranking": ranking})
        return
    if df.empty:
        print(f"no settled transactions in weeks of {resolved}")
        return
    view = df.assign(
        week=df.auth_week + " (" + df.week_start.astype(str) + ".." + df.week_end.astype(str) + ")",
        net_usd=df.net_usd.map("{:,.2f}".format), gross_under_usd=df.gross_under_usd.map("{:,.2f}".format),
        rate=df.rate.map("{:.1%}".format), note=df.low_sample.map({True: "low sample", False: ""}))
    print(f"Worst PSP week in {resolved} (weeks by auth date, month of the Thursday; net USD loss)\n")
    print(view[["rank", "psp", "week", "net_usd", "gross_under_usd", "rate", "n", "note"]]
          .to_string(index=False))
