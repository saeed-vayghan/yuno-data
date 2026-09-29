"""Core contract rows 1-10 (Core tier). Owner: INFRA. M1: rows 1-6; M2: rows 7-10.

Every function: get the store (arg or deps.get_store()), run one parameterized SQL on a mart,
return a DataFrame / dict. Never string-format user values into SQL.
"""

from contextlib import AbstractContextManager
from typing import Any, Literal

import pandas as pd

from casarecon.core import weeks
from casarecon.core.config import load_config
from casarecon.core.deps import get_store
from casarecon.core.errors import BadFilter
from casarecon.core.filters import Filters
from casarecon.core.privacy import mask_id
from casarecon.ports import Store

FCT = "marts.fct_transaction_discrepancy"
PSP_WEEKLY = "marts.mart_psp_weekly"

TXN_COLUMNS: tuple[str, ...] = (
    "transaction_id", "auth_date", "psp", "country", "currency", "exponent", "customer",
    "amount_tier", "is_cross_border", "category", "likely_cause", "why_flagged",
    "authorized_amount", "expected_settled", "settled_amount", "diff_local", "residual_usd",
    "abs_residual_usd", "residual_pct", "direction", "settle_lag_days",
)
_TXN_SELECT = ", ".join("customer_id" if c == "customer" else c for c in TXN_COLUMNS)

SegmentDim = Literal["country", "currency", "psp", "psp_country", "amount_tier", "country_tier",
                     "weekday", "is_weekend", "lag_bucket", "cross_border"]


def connect(*, store: Store | None = None) -> AbstractContextManager[Any]:
    """#1 Read-only connection context manager. Raises DbMissing, DbBusy."""
    return (store or get_store()).connect()


def db_version(*, store: Store | None = None) -> float:
    """#2 DB file mtime (0.0 if missing); dashboard cache key."""
    return (store or get_store()).version()


def status(*, store: Store | None = None) -> dict:
    """#3 keys: as_of: datetime, last_closed_week: str, last_closed_start: date,
    last_closed_end: date, open_weeks: list[str], last_full_month: str, months: list[str], n_rows: int."""
    s = store or get_store()
    row = s.query(f"""
        select max(greatest(auth_ts, coalesce(settle_ts, auth_ts))) as as_of,
               min(auth_date) as first_day, count(*) as n_rows,
               list(distinct auth_month order by auth_month) as months,
               list(distinct auth_week order by auth_week) as weeks
        from {FCT}""").iloc[0]
    as_of = pd.Timestamp(row["as_of"]).to_pydatetime()
    closed_end = weeks.last_closed_end(as_of)
    closed_start, _ = weeks.week_bounds(closed_end)
    closed = weeks.iso_week(closed_end)
    return {
        "as_of": as_of,
        "last_closed_week": closed,
        "last_closed_start": closed_start,
        "last_closed_end": closed_end,
        "open_weeks": [w for w in row["weeks"] if w > closed],
        "last_full_month": weeks.last_full_month(as_of, row["first_day"]),
        "months": list(row["months"]),
        "n_rows": int(row["n_rows"]),
    }


def psp_weekly(filters: Filters | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """#4 cols: psp, country, auth_week, week_start, week_end, week_month, n, n_flagged, rate,
    n_large, gross_under_usd, gross_over_usd, net_usd, low_sample."""
    f = filters or Filters()
    where, params = Filters(psp=f.psp, country=f.country, week=f.week).where_sql()
    return (store or get_store()).query(f"""
        select psp, country, auth_week, week_start, week_end, week_month, n, n_flagged, rate,
               n_large, gross_under_usd, gross_over_usd, net_usd, low_sample
        from {PSP_WEEKLY} where true{where}
        order by psp, country, auth_week""", params)


def worst_week(month: str = "last", *, store: Store | None = None) -> pd.DataFrame:
    """#5 ranked cols: rank, psp, auth_week, week_start, week_end, n, n_flagged, rate, n_large,
    net_usd, gross_under_usd, low_sample. Sort: low_sample asc, net_usd desc, psp asc, auth_week asc."""
    s = store or get_store()
    month = status(store=s)["last_full_month"] if month == "last" else weeks.check_month(month)
    if month is None:
        raise BadFilter("no full calendar month in the data yet")
    min_n = load_config().thresholds.min_sample.worst_week
    df = s.query(f"""
        select psp, auth_week, min(week_start) as week_start, min(week_end) as week_end,
               sum(n)::bigint as n, sum(n_flagged)::bigint as n_flagged,
               sum(n_flagged) / sum(n) as rate, sum(n_large)::bigint as n_large,
               round(sum(net_usd), 2) as net_usd, round(sum(gross_under_usd), 2) as gross_under_usd,
               sum(n) < ? as low_sample
        from {PSP_WEEKLY} where week_month = ?
        group by psp, auth_week
        order by low_sample, net_usd desc, psp, auth_week""", [min_n, month])
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def query_transactions(filters: Filters | None = None, min_usd: float | None = None,
                       limit: int | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """#6 settled fct rows, cols = TXN_COLUMNS; strict abs_residual_usd > min_usd;
    sorted abs_residual_usd desc, transaction_id asc. `customer` is masked."""
    if limit is not None and limit < 1:
        raise BadFilter(f"bad limit: {limit} (must be >= 1)")
    where, params = (filters or Filters()).where_sql()
    if min_usd is not None:
        where += " and abs_residual_usd > ?"
        params.append(float(min_usd))
    sql = f"""select {_TXN_SELECT} from {FCT} where status = 'settled'{where}
              order by abs_residual_usd desc, transaction_id"""
    if limit is not None:
        sql += " limit ?"
        params.append(int(limit))
    df = (store or get_store()).query(sql, params)
    df.insert(df.columns.get_loc("customer_id"), "customer", df.pop("customer_id").map(mask_id))
    return df[list(TXN_COLUMNS)]


def segment_rates(dim: SegmentDim, filters: Filters | None = None, *,
                  store: Store | None = None) -> pd.DataFrame:
    """#7 cols: segment_type, segment_value, n, n_flagged, rate, ci_low, ci_high, peer_rate, lift,
    n_large, gross_under_usd, gross_over_usd, net_usd, mean_loss_usd, median_loss_usd, low_sample."""
    raise NotImplementedError("M2")


def cause_summary(filters: Filters | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """#8 cols: likely_cause, n, n_flagged, gross_under_usd, gross_over_usd, net_usd, share_of_loss.
    Sorted gross_under_usd desc; one row per cause label (0 rows = ruled out)."""
    raise NotImplementedError("M2")


def excess_loss(top: int | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """#9 cols: psp, country, n, rate, peer_rate, lift, excess_usd, mean_loss_usd, median_loss_usd.
    Sorted excess_usd desc; peer = other PSPs in the same country."""
    raise NotImplementedError("M2")


def lag_by_country_tier(*, store: Store | None = None) -> pd.DataFrame:
    """#10 cols: country, amount_tier, is_over_300, n, median_lag_days, p90_lag_days, late_share."""
    raise NotImplementedError("M2")
