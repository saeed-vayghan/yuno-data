"""Shared bits for ui_q_* (BACKEND): table names, SQL fragments, week rules, small pure helpers."""

from datetime import date, datetime, timedelta
from functools import lru_cache

import pandas as pd

from casarecon.core.config import load_config
from casarecon.core.deps import get_store
from casarecon.core.filters import Filters, filters_or_empty
from casarecon.ports import Store

FCT = "marts.fct_transaction_discrepancy"
SETTLED = "status = 'settled'"
CATEGORY_ORDER = ("exact", "rounding", "fx_tolerance", "meaningful", "large")

# One aggregate block reused by kpis / trend / week-over-week. Loss sign per contract.
AGG = """count(*) as n,
  count(*) filter (where category in ('meaningful', 'large')) as n_flagged,
  count(*) filter (where category = 'large') as n_large,
  round(coalesce(sum(greatest(-residual_usd, 0)), 0), 2) as gross_under_usd,
  round(coalesce(sum(greatest(residual_usd, 0)), 0), 2) as gross_over_usd"""

# as_of = latest timestamp in the data (never wall-clock).
AS_OF = f"select max(greatest(auth_ts, coalesce(settle_ts, auth_ts))) as as_of from {FCT}"


def store_of(store: Store | None) -> Store:
    return store or get_store()


def where(filters: Filters | None) -> tuple[str, list]:
    """Validated ' and ...' fragment + params (never string-formats values)."""
    return filters_or_empty(filters).where_sql()


@lru_cache(maxsize=1)
def min_sample() -> int:
    """Weekly low-sample cut-off (thresholds.yaml min_sample.worst_week)."""
    return load_config().thresholds.min_sample.worst_week


def with_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Add rate (NaN when n = 0) and net_usd = under - over to an AGG frame."""
    n = df["n"].astype(float)
    return df.assign(rate=(df["n_flagged"] / n.where(n > 0)).astype(float),
                     net_usd=(df["gross_under_usd"] - df["gross_over_usd"]).round(2))


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_monday(week: str) -> date:
    return date.fromisocalendar(int(week[:4]), int(week[6:]), 1)


def prev_week(week: str) -> str:
    return iso_week(week_monday(week) - timedelta(days=7))


def closed_cutoff(as_of: datetime | date) -> date:
    """A week is closed when its Sunday <= as_of - 7 days."""
    d = as_of.date() if isinstance(as_of, datetime) else as_of
    return d - timedelta(days=7)


def is_closed(week_start: date, as_of: datetime | date) -> bool:
    return week_start + timedelta(days=6) <= closed_cutoff(as_of)


def last_closed_week(as_of: datetime | date) -> str:
    cut = closed_cutoff(as_of)
    return iso_week(cut - timedelta(days=cut.isoweekday() % 7))


def as_of(store: Store) -> datetime | None:
    value = store.query(AS_OF)["as_of"].iloc[0]
    return None if pd.isna(value) else pd.Timestamp(value).to_pydatetime()


def full_months(min_date: date, max_date: date) -> list[str]:
    """Calendar months fully inside [min_date, max_date], as 'YYYY-MM'."""
    months, first = [], date(min_date.year, min_date.month, 1)
    if first < min_date:
        first = _next_month(first)
    while _next_month(first) - timedelta(days=1) <= max_date:
        months.append(first.strftime("%Y-%m"))
        first = _next_month(first)
    return months


def _next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)
