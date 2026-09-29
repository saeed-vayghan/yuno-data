"""Global sidebar filters: widgets <-> st.session_state["filters"] (a core Filters) <-> URL.

Order of truth: one-shot handoff > session_state > query params (first load only) > defaults.
Rendered once in app.py, before the page runs, so values survive page switches.
Pure helpers (parse_params, to_params, scoped, describe) are unit-tested.
"""

from dataclasses import replace
from datetime import date

import streamlit as st

from casarecon.dashboard import data
from casarecon.dashboard import format as fmt

GLOBAL = ("date", "country", "psp")
KEYS = {"country": "w_country", "psp": "w_psp", "date": "w_dates"}
LABELS = {"date": "Auth dates", "country": "Country", "psp": "PSP", "tier": "Size tier",
          "xb": "Cross-border", "cause": "Cause"}


def parse_params(params: dict[str, list[str]], opts: dict) -> tuple[dict, list[str]]:
    """URL values -> widget values; unknown ones are dropped and reported (for a toast)."""
    values, ignored = {}, []
    for name in ("country", "psp"):
        raw = [v for item in params.get(name, []) for v in item.split(",") if v]
        good = [v for v in raw if v in opts.get(name, [])]
        ignored += [f"Ignored unknown {LABELS[name]} '{v}'" for v in raw if v not in good]
        if good:
            values[name] = good
    try:
        dates = [date.fromisoformat(params[k][0]) for k in ("from", "to") if params.get(k)]
        if len(dates) == 2 and dates[0] <= dates[1]:
            values["date"] = tuple(dates)
    except ValueError:
        ignored.append("Ignored a bad date in the URL")
    return values, ignored


def to_params(f: data.Filters, bounds: tuple[date | None, date | None]) -> dict[str, list[str]]:
    """Only non-default values go to the URL, so links stay short."""
    out: dict[str, list[str]] = {}
    if f.country:
        out["country"] = list(f.country)
    if f.psp:
        out["psp"] = list(f.psp)
    if (f.date_from, f.date_to) != bounds and f.date_from and f.date_to:
        out["from"], out["to"] = [f.date_from.isoformat()], [f.date_to.isoformat()]
    return out


def scoped(f: data.Filters, uses: set[str]) -> data.Filters:
    """Drop the global filters a page does not use (e.g. Overview ignores dates)."""
    keep = {"country": f.country if "country" in uses else (), "psp": f.psp if "psp" in uses else ()}
    if "date" not in uses:
        keep |= {"date_from": None, "date_to": None}
    return replace(f, **keep)


def describe(f: data.Filters, uses: set[str]) -> str:
    """'Active: PSP_B · AR · Jun 15–21. Auth dates not used here.'"""
    parts = [", ".join(f.psp) or "all PSPs", ", ".join(f.country) or "all countries"]
    if "date" in uses and f.date_from and f.date_to:
        parts.append(fmt.day_range(f.date_from, f.date_to))
    unused = [LABELS[g] for g in GLOBAL if g not in uses]
    tail = f" {' and '.join(unused)} not used here." if unused else ""
    return f"Active: {' · '.join(parts)}.{tail}"


def _bounds(opts: dict) -> tuple[date | None, date | None]:
    return data.to_date(opts.get("min_date")), data.to_date(opts.get("max_date"))


def _seed_widgets(opts: dict) -> None:
    """First load: URL -> widget keys. Then apply any one-shot handoff from a cross-page link."""
    if "filters" not in st.session_state:
        values, ignored = parse_params({k: st.query_params.get_all(k) for k in st.query_params}, opts)
        for msg in ignored:
            st.toast(msg, icon="⚠️")
        for name, value in values.items():
            st.session_state[KEYS[name]] = value
    handoff = st.session_state.pop("handoff", None) or {}
    for name, value in handoff.items():
        st.session_state[KEYS[name]] = clip(value, _bounds(opts)) if name == "date" else value


def clip(dates: tuple[date, date], bounds: tuple[date | None, date | None]) -> tuple[date, date]:
    """Keep a handed-off date range inside the data range (a week may start before the data)."""
    lo, hi = bounds
    start, end = dates
    return (max(start, lo) if lo else start, min(end, hi) if hi else end)


def render_global_sidebar() -> data.Filters:
    opts = data.options()
    _seed_widgets(opts)
    lo, hi = _bounds(opts)
    st.sidebar.header("Filters")
    date_from = date_to = None
    if lo and hi:
        st.session_state.setdefault(KEYS["date"], (lo, hi))
        picked = st.sidebar.date_input("Auth dates", key=KEYS["date"], min_value=lo, max_value=hi,
                                       help="Authorization date range (inclusive).")
        if isinstance(picked, tuple) and len(picked) == 2:
            date_from, date_to = picked
    country = st.sidebar.multiselect("Country", opts["country"], key=KEYS["country"],
                                     placeholder="All countries")
    psp = st.sidebar.multiselect("PSP", opts["psp"], key=KEYS["psp"], placeholder="All PSPs")
    st.sidebar.button("Clear filters", on_click=clear, key="clear_filters")
    f = data.Filters(country=tuple(country), psp=tuple(psp), date_from=date_from, date_to=date_to)
    st.session_state["filters"] = f
    params = to_params(f, (lo, hi))
    if params != {k: st.query_params.get_all(k) for k in st.query_params}:
        st.query_params.from_dict(params)
    return f


def current(uses: set[str], **page: object) -> data.Filters:
    """Global filters the page uses + page-only fields (tier, xb, cause, category...)."""
    return replace(scoped(st.session_state.get("filters", data.Filters()), uses), **page)


def set_handoff(**values: object) -> None:
    """Cross-page link: e.g. set_handoff(psp=["PSP_B"], date=(start, end)); then st.switch_page."""
    st.session_state["handoff"] = values


def clear() -> None:
    for key in KEYS.values():
        st.session_state.pop(key, None)
    st.query_params.clear()
