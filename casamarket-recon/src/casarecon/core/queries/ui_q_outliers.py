"""Outliers rows #17 outlier_summary, #18 transaction_detail, #19 similar_count (BACKEND)."""

import pandas as pd

from casarecon.core.filters import Filters
from casarecon.core.privacy import mask_id
from casarecon.core.queries.pipeline_q import TXN_COLUMNS
from casarecon.core.queries.ui_q_base import FCT, SETTLED, store_of, where
from casarecon.ports import Store

DETAIL_EXTRA = ("fx_auth", "fx_settle", "fx_move_pct", "amount_usd", "settled_usd", "item_count",
                "risk_score", "is_weekend", "is_lag_outlier", "rounding_flag")
# customer_id is read only to be masked here; the full ID never leaves core.
_DETAIL_SELECT = ", ".join("customer_id as customer" if c == "customer" else c
                           for c in (*TXN_COLUMNS, *DETAIL_EXTRA))


def outlier_summary(filters: Filters | None = None, min_usd: float | None = 50, *,
                    store: Store | None = None) -> dict:
    """Same rows as query_transactions(filters, min_usd): settled, strict abs_residual_usd > min_usd."""
    cond, params = where(filters)
    if min_usd is not None:
        cond, params = f"{cond} and abs_residual_usd > ?", [*params, float(min_usd)]
    row = store_of(store).query(
        f"select count(*) as n, "
        f"round(coalesce(sum(greatest(-residual_usd, 0)), 0), 2) as gross_under_usd, "
        f"round(coalesce(sum(greatest(residual_usd, 0)), 0), 2) as gross_over_usd "
        f"from {FCT} where {SETTLED}{cond}", params).iloc[0]
    return {"n": int(row["n"]), "gross_under_usd": float(row["gross_under_usd"]),
            "gross_over_usd": float(row["gross_over_usd"])}


def _plain(value: object) -> object:
    """numpy/pandas scalar -> plain Python value; NaN/NaT -> None."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def transaction_detail(transaction_id: str, *, store: Store | None = None) -> dict | None:
    df = store_of(store).query(
        f"select {_DETAIL_SELECT} from {FCT} where transaction_id = ?", [transaction_id])
    if df.empty:
        return None
    row = {k: _plain(v) for k, v in df.iloc[0].to_dict().items()}
    return {**row, "customer": mask_id(row["customer"]),
            "auth_date": pd.Timestamp(row["auth_date"]).date()}


def similar_count(transaction_id: str, *, store: Store | None = None) -> dict:
    """Settled rows with the same psp, country and likely_cause as this transaction."""
    df = store_of(store).query(
        f"with t as (select psp, country, likely_cause from {FCT} where transaction_id = ?) "
        f"select t.psp, t.country, t.likely_cause, count(f.transaction_id) as n from t "
        f"left join {FCT} f on f.{SETTLED} and f.psp = t.psp and f.country = t.country "
        "and f.likely_cause is not distinct from t.likely_cause group by all", [transaction_id])
    if df.empty:
        return {"psp": None, "country": None, "likely_cause": None, "n": 0}
    row = {k: _plain(v) for k, v in df.iloc[0].to_dict().items()}
    return {**row, "n": int(row["n"])}
