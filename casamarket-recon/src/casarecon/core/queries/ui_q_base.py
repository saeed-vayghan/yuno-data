"""Shared bits for ui_q_* (BACKEND): table name, SQL fragments, small pure helpers.

Week rules (as_of, last closed week, full months) come only from pipeline_q.status() / core.weeks."""

from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from casarecon.core import weeks
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

# as_of in SQL (same expression as pipeline_q.status) for in-query ages (pending, late share).
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


def prev_week(week: str) -> str:
    """'2026-W25' -> '2026-W24' (core.weeks has no week arithmetic)."""
    monday = date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    return weeks.iso_week(monday - timedelta(days=7))

