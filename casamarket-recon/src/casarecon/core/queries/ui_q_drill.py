"""Drill-down + alerts rows #16 category_mix, #20 filter_options, #21 pending (BACKEND)."""

from datetime import date

import pandas as pd

from casarecon.core.filters import CAUSES, COUNTRIES, PSPS, TIERS, WEEKDAYS, Filters
from casarecon.core.queries.pipeline_q import status
from casarecon.core.queries.ui_q_base import AS_OF, CATEGORY_ORDER, FCT, SETTLED, store_of, where
from casarecon.ports import Store

PENDING_COLS = ["psp", "country", "n", "amount_usd", "oldest_age_days"]

# filter key -> (fct column, canonical order)
_OPTIONS = {"country": ("country", COUNTRIES), "psp": ("psp", PSPS), "tier": ("amount_tier", TIERS),
            "weekday": ("auth_weekday", WEEKDAYS), "category": ("category", CATEGORY_ORDER),
            "cause": ("likely_cause", CAUSES)}


def category_mix(filters: Filters | None = None, *, store: Store | None = None) -> pd.DataFrame:
    """auth_week, category, n, share (of settled rows in that week); category order exact -> large."""
    cond, params = where(filters)
    df = store_of(store).query(
        f"select auth_week, category, count(*) as n, "
        f"count(*) / sum(count(*)) over (partition by auth_week) as share "
        f"from {FCT} where {SETTLED}{cond} group by auth_week, category", params)
    rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    df = df.sort_values(["auth_week", "category"], key=lambda s: s.map(rank) if s.name == "category"
                        else s)
    return df[["auth_week", "category", "n", "share"]].reset_index(drop=True)


def filter_options(*, store: Store | None = None) -> dict[str, list[str]]:
    """Values present in the data, in canonical order; months = full calendar months only."""
    lists = ", ".join(f"list(distinct {col}) filter (where {col} is not null) as {key}"
                      for key, (col, _) in _OPTIONS.items())
    s = store_of(store)
    row = s.query(
        f"select {lists}, list(distinct auth_week) as weeks, "
        f"min(auth_ts)::date as min_date, max(auth_ts)::date as max_date from {FCT}").iloc[0]
    if pd.isna(row["min_date"]):
        return {**{k: [] for k in _OPTIONS}, "weeks": [], "months": [], "min_date": None,
                "max_date": None}
    lo, hi = pd.Timestamp(row["min_date"]).date(), pd.Timestamp(row["max_date"]).date()
    opts = {k: [v for v in order if v in set(row[k])] for k, (_, order) in _OPTIONS.items()}
    st = status(store=s)  # core.weeks rule: a month is full if it starts >= min date, <= last_full
    last_full = st["last_full_month"]
    months = [m for m in st["months"]
              if last_full and m <= last_full and date.fromisoformat(f"{m}-01") >= lo]
    return {**opts, "weeks": sorted(row["weeks"]), "months": months,
            "min_date": lo.isoformat(), "max_date": hi.isoformat()}


def pending(*, store: Store | None = None) -> pd.DataFrame:
    """Pending rows by psp x country; oldest age in days vs as_of (data time)."""
    df = store_of(store).query(
        f"with a as ({AS_OF}) select psp, country, count(*) as n, "
        f"round(sum(amount_usd), 2) as amount_usd, "
        f"round(date_diff('second', min(auth_ts), any_value(a.as_of)) / 86400.0, 2) as oldest_age_days "
        f"from {FCT}, a where status = 'pending' group by psp, country "
        f"order by oldest_age_days desc, psp, country")
    return df[PENDING_COLS].reset_index(drop=True)
