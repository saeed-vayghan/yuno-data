"""UI adapter: the ONLY dashboard module that calls `casarecon.core`.

Every DB-reading call goes through one `st.cache_data` function keyed on (core function name,
args, `core.db_version()`); the version arg has no leading underscore, so Streamlit hashes it and a
rebuild refreshes the cache. Report loaders (`load_*`) are not cached. Errors (DbMissing, DbBusy,
NotImplementedError) propagate to `states.guarded` / `states.section` (friendly messages).
Tests monkeypatch the public functions here, so pages must call them as `data.<name>(...)`.
"""

from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st

from casarecon import core
from casarecon.core import filters as core_filters

Filters = core.Filters
DbMissing, DbBusy, BadFilter = core.DbMissing, core.DbBusy, core.BadFilter
FALLBACK_OPTIONS: dict = {
    "country": list(core_filters.COUNTRIES), "psp": list(core_filters.PSPS),
    "tier": list(core_filters.TIERS), "weekday": list(core_filters.WEEKDAYS),
    "category": list(core_filters.CATEGORIES), "cause": list(core_filters.CAUSES),
    "weeks": [], "months": [], "min_date": None, "max_date": None,
}


def version() -> float:
    """DB file mtime; 0.0 when missing or unknown (never raises)."""
    try:
        return core.db_version()
    except Exception:  # noqa: BLE001 - the cache key must never break a page
        return 0.0


@st.cache_data(show_spinner="Loading…", max_entries=256)
def _cached(name: str, args: tuple, version: float) -> Any:
    return getattr(core, name)(*args)


def _query(name: str, *args: Any) -> Any:
    return _cached(name, args, version())


# --- DB readers (cached) -------------------------------------------------------------------------
def status() -> dict:
    return _query("status")


def worst_week(month: str = "last") -> pd.DataFrame:
    return _query("worst_week", month)


def kpis(f: Filters, week: str = "last_closed") -> dict:
    return _query("kpis", f, week)


def weekly_trend(f: Filters, by: str = "portfolio") -> pd.DataFrame:
    return _query("weekly_trend", f, by)


def week_over_week(f: Filters) -> pd.DataFrame:
    return _query("week_over_week", f)


def transactions(f: Filters, min_usd: float | None = None, limit: int | None = None) -> pd.DataFrame:
    return _query("query_transactions", f, min_usd, limit)


@st.cache_data(show_spinner="Preparing CSV…", max_entries=16)
def _csv(f: Filters, min_usd: float | None, version: float) -> bytes:
    return core.query_transactions(f, min_usd, None).to_csv(index=False).encode("utf-8")


def transactions_csv(f: Filters, min_usd: float | None = None) -> bytes:
    """All matching rows (no limit), TXN_COLUMNS, masked customer, numbers unformatted."""
    return _csv(f, min_usd, version())


def outlier_summary(f: Filters, min_usd: float | None) -> dict:
    return _query("outlier_summary", f, min_usd)


def transaction_detail(transaction_id: str) -> dict | None:
    return _query("transaction_detail", transaction_id)


def similar_count(transaction_id: str) -> dict:
    return _query("similar_count", transaction_id)


def segment_rates(dim: str, f: Filters | None = None) -> pd.DataFrame:
    return _query("segment_rates", dim, f)


def category_mix(f: Filters) -> pd.DataFrame:
    return _query("category_mix", f)


def cause_summary(f: Filters | None = None) -> pd.DataFrame:
    return _query("cause_summary", f)


def excess_loss(top: int | None = 5) -> pd.DataFrame:
    return _query("excess_loss", top)


def options() -> dict:
    """filter_options() with a safe fallback (fixed lists, no dates) so the sidebar always renders."""
    try:
        return {**FALLBACK_OPTIONS, **_query("filter_options")}
    except Exception:  # noqa: BLE001 - not built yet / no DB: fixed lists are fine
        return dict(FALLBACK_OPTIONS)


def months() -> list[str]:
    """Full calendar months for the worst-week picker; [] when not available yet."""
    return list(options().get("months") or [])


# --- report files (uncached: small, read on each run; None when missing) -------------------------
def alerts() -> pd.DataFrame | None:
    return core.load_alerts()


def findings() -> dict | None:
    return core.load_findings()


def recommendations() -> list[dict] | None:
    return core.load_recommendations()


def to_date(value: str | date | None) -> date | None:
    """ISO string / datetime / pandas Timestamp -> date (widgets and comparisons need plain dates)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
