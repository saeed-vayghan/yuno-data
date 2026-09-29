"""Core contract rows 7-10 (Core tier, M2). Owner: INFRA. Analysis and alerts depend on these.

Unfiltered calls read the marts; filtered calls aggregate `fct` with `Filters.where_sql()` params.
"""

from typing import Literal, get_args

import pandas as pd

from casarecon.core.config import load_config
from casarecon.core.deps import get_store
from casarecon.core.errors import BadFilter
from casarecon.core.filters import CAUSES, Filters
from casarecon.core.rates import excess_usd, with_peers
from casarecon.ports import Store

FCT = "marts.fct_transaction_discrepancy"
SegmentDim = Literal["country", "currency", "psp", "psp_country", "amount_tier", "country_tier",
                     "weekday", "is_weekend", "lag_bucket", "cross_border"]
# Same labels as dbt/models/marts/mart_segment_rates.sql (fixed SQL, never user input).
SEGMENT_SQL: dict[str, str] = {
    "country": "country", "currency": "currency", "psp": "psp",
    "psp_country": "psp || '|' || country", "amount_tier": "amount_tier",
    "country_tier": "country || '|' || amount_tier", "weekday": "auth_weekday",
    "is_weekend": "is_weekend::varchar", "lag_bucket": "lag_bucket",
    "cross_border": "is_cross_border::varchar",
}
_AGG = """count(*) as n, count_if(is_meaningful)::bigint as n_flagged,
    count_if(is_meaningful) / count(*) as rate, count_if(category = 'large')::bigint as n_large,
    round(sum(greatest(-residual_usd, 0)), 2) as gross_under_usd,
    round(sum(greatest(residual_usd, 0)), 2) as gross_over_usd, round(sum(-residual_usd), 2) as net_usd,
    round(coalesce(avg(-residual_usd) filter (where is_meaningful), 0), 2) as mean_loss_usd,
    round(coalesce(median(-residual_usd) filter (where is_meaningful), 0), 2) as median_loss_usd"""
SEG_COLS = ["segment_type", "segment_value", "n", "n_flagged", "rate", "ci_low", "ci_high", "peer_rate",
            "lift", "n_large", "gross_under_usd", "gross_over_usd", "net_usd", "mean_loss_usd",
            "median_loss_usd", "low_sample"]


def segment_rates(dim: SegmentDim, filters: Filters | None = None, *,
                  store: Store | None = None) -> pd.DataFrame:
    """#7 one row per segment value; peer = other values of the dim (psp_country: other PSPs in the
    same country). low_sample = n < thresholds.min_sample.alerts."""
    if dim not in get_args(SegmentDim):
        raise BadFilter(f"unknown segment dim: {dim} (allowed: {', '.join(get_args(SegmentDim))})")
    s = store or get_store()
    seg = None
    if filters is None:  # the mart is per merchant; > 1 merchant -> aggregate the fct instead
        seg = s.query("select * from marts.mart_segment_rates where segment_type = ?"
                      " order by segment_value", [dim])
    if seg is None or seg.segment_value.duplicated().any():
        where, params = (filters or Filters()).where_sql()
        seg = s.query(f"""select ? as segment_type, {SEGMENT_SQL[dim]} as segment_value, {_AGG}
            from {FCT} where status = 'settled'{where} group by 2 order by 2""", [dim, *params])
    min_n = load_config().thresholds.min_sample.alerts
    return with_peers(seg).assign(low_sample=lambda d: d.n < min_n)[SEG_COLS]


def cause_summary(filters: Filters | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """#8 one row per cause label (0 rows = ruled out), sorted gross_under_usd desc.
    Non-exact settled rows; share_of_loss = gross_under_usd / total gross_under_usd."""
    where, params = (filters or Filters()).where_sql()
    labels = " union all ".join("select ? as likely_cause" for _ in CAUSES)
    df = (store or get_store()).query(f"""
        with rows as (select * from {FCT} where status = 'settled' and category <> 'exact'{where})
        select l.likely_cause, count(r.transaction_id) as n,
               coalesce(count_if(r.is_meaningful), 0)::bigint as n_flagged,
               round(coalesce(sum(greatest(-r.residual_usd, 0)), 0), 2) as gross_under_usd,
               round(coalesce(sum(greatest(r.residual_usd, 0)), 0), 2) as gross_over_usd,
               round(coalesce(sum(-r.residual_usd), 0), 2) as net_usd
        from ({labels}) l left join rows r using (likely_cause)
        group by l.likely_cause
        order by gross_under_usd desc, likely_cause""", [*params, *CAUSES])
    total = df.gross_under_usd.sum()
    return df.assign(share_of_loss=(df.gross_under_usd / total) if total else 0.0)


def excess_loss(top: int | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """#9 PSP x country vs other PSPs in the same country: excess_usd = max(rate - peer, 0) x n x mean loss."""
    seg = segment_rates("psp_country", store=store)
    seg[["psp", "country"]] = seg.segment_value.str.split("|", expand=True)
    seg["excess_usd"] = [excess_usd(r, p, n, m) for r, p, n, m in
                         zip(seg.rate, seg.peer_rate, seg.n, seg.mean_loss_usd, strict=True)]
    out = seg.sort_values(["excess_usd", "psp", "country"], ascending=[False, True, True])
    cols = ["psp", "country", "n", "rate", "peer_rate", "lift", "excess_usd", "mean_loss_usd",
            "median_loss_usd"]
    return out[cols].head(top if top is not None else len(out)).reset_index(drop=True)


def lag_by_country_tier(*, store: Store | None = None) -> pd.DataFrame:
    """#10 settle lag by country x amount tier x over-$300 (settled rows); late = lag > lag_outlier_days."""
    late = load_config().thresholds.lag_outlier_days
    return (store or get_store()).query(f"""
        select country, amount_tier, is_over_300, count(*) as n,
               median(settle_lag_days) as median_lag_days,
               quantile_cont(settle_lag_days, 0.9) as p90_lag_days,
               count_if(settle_lag_days > ?) / count(*) as late_share
        from {FCT} where status = 'settled'
        group by country, amount_tier, is_over_300
        order by country, list_position(['10-50', '50-200', '200+'], amount_tier), is_over_300""", [late])


SETTLED_FACT_COLUMNS: tuple[str, ...] = (
    "transaction_id", "psp", "country", "currency", "amount_usd", "amount_tier", "is_over_300",
    "is_cross_border", "is_weekend", "lag_bucket", "settle_lag_days", "auth_month", "item_count",
    "risk_score", "category", "is_meaningful", "likely_cause", "direction", "rounding_flag",
    "residual_usd", "abs_residual_usd", "residual_pct",
)


def settled_facts(*, store: Store | None = None) -> pd.DataFrame:
    """Settled fct rows for the analysis (no customer_id), ordered by transaction_id. Not a UI row."""
    return (store or get_store()).query(f"select {', '.join(SETTLED_FACT_COLUMNS)} from {FCT} "
                                        "where status = 'settled' order by transaction_id")
