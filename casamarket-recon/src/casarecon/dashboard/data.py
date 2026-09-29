"""UI adapter: the ONLY dashboard module that calls `casarecon.core`.

Every DB-reading call is cached with `st.cache_data`, keyed on its args + `core.db_version()`
(named `version`, no leading underscore, so Streamlit hashes it; a rebuild refreshes the cache).
Report loaders are not cached. Errors (DbMissing, DbBusy, NotImplementedError) propagate to
`states.guarded` / `states.section`, which turn them into friendly messages.
Tests monkeypatch the public functions here, so pages must call them as `data.<name>(...)`.
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from casarecon import core
from casarecon.core import filters as core_filters

Filters = core.Filters
DbMissing, DbBusy, BadFilter = core.DbMissing, core.DbBusy, core.BadFilter
TXN_COLUMNS = core.TXN_COLUMNS
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


@st.cache_data(show_spinner="Loading…")
def _status(version: float) -> dict:
    return core.status()


@st.cache_data(show_spinner="Loading…")
def _options(version: float) -> dict:
    return core.filter_options()


@st.cache_data(show_spinner="Loading…")
def _worst_week(month: str, version: float) -> pd.DataFrame:
    return core.worst_week(month)


@st.cache_data(show_spinner="Loading…")
def _kpis(f: Filters, week: str, version: float) -> dict:
    return core.kpis(f, week)


@st.cache_data(show_spinner="Loading…")
def _weekly_trend(f: Filters, by: str, version: float) -> pd.DataFrame:
    return core.weekly_trend(f, by)


@st.cache_data(show_spinner="Loading…")
def _week_over_week(f: Filters, version: float) -> pd.DataFrame:
    return core.week_over_week(f)


@st.cache_data(show_spinner="Loading…")
def _transactions(f: Filters, min_usd: float | None, limit: int | None, version: float) -> pd.DataFrame:
    return core.query_transactions(f, min_usd, limit)


@st.cache_data(show_spinner="Loading…")
def _outlier_summary(f: Filters, min_usd: float, version: float) -> dict:
    return core.outlier_summary(f, min_usd)


def status() -> dict:
    return _status(version())


def options() -> dict:
    """filter_options() with a safe fallback (fixed lists, no dates) so the sidebar always renders."""
    try:
        return {**FALLBACK_OPTIONS, **_options(version())}
    except Exception:  # noqa: BLE001 - not built yet / no DB: fixed lists are fine
        return dict(FALLBACK_OPTIONS)


def worst_week(month: str = "last") -> pd.DataFrame:
    return _worst_week(month, version())


def kpis(f: Filters, week: str = "last_closed") -> dict:
    return _kpis(f, week, version())


def weekly_trend(f: Filters, by: str = "portfolio") -> pd.DataFrame:
    return _weekly_trend(f, by, version())


def week_over_week(f: Filters) -> pd.DataFrame:
    return _week_over_week(f, version())


def transactions(f: Filters, min_usd: float | None = None, limit: int | None = None) -> pd.DataFrame:
    return _transactions(f, min_usd, limit, version())


def transactions_csv(f: Filters, min_usd: float | None = None) -> bytes:
    """All matching rows (no limit), TXN_COLUMNS, masked customer, numbers unformatted."""
    return transactions(f, min_usd, None).to_csv(index=False).encode("utf-8")


def outlier_summary(f: Filters, min_usd: float) -> dict:
    return _outlier_summary(f, min_usd, version())


def alerts() -> pd.DataFrame | None:
    """Uncached: small report file, read on each run. None when the file is missing."""
    return core.load_alerts()


def to_date(value: str | date | None) -> date | None:
    """ISO string / datetime / pandas Timestamp -> date (widgets and comparisons need plain dates)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def months() -> list[str]:
    """Full calendar months for the worst-week picker; [] when not available yet."""
    found = options().get("months") or []
    if found:
        return list(found)
    try:
        return list(status().get("months") or [])
    except Exception:  # noqa: BLE001 - picker falls back to 'last'
        return []
