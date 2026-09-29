"""Global sidebar filters: widgets <-> st.session_state["filters"] (a core Filters) <-> URL.

Order of truth: one-shot handoff > session_state > query params (first load only) > defaults.
Rendered once in app.py, before the page runs, so values survive page switches.
Pure helpers live in filter_logic.py.
"""

from dataclasses import replace
from datetime import date

import streamlit as st

from casarecon.dashboard import data
from casarecon.dashboard.filter_logic import (  # noqa: F401 - re-exported for pages and tests
    GLOBAL, LABELS, PAGE_FIELDS, clip, date_text, describe, handoff_text, parse_params, scoped,
    to_params,
)

KEYS = {"country": "w_country", "psp": "w_psp", "date": "w_dates"}


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
    handoff = st.session_state.pop("handoff", None)
    if handoff:  # a link shows exactly what it names: every other filter goes back to default
        _reset()
        for name, value in handoff.items():
            if name in KEYS:
                st.session_state[KEYS[name]] = clip(value, _bounds(opts)) if name == "date" else value
            else:
                st.session_state[f"f_{name}"] = value
        st.toast(f"Filters set: {handoff_text(handoff)}", icon="🔎")


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
    """Cross-page link: set_handoff(psp=["PSP_B"], date=(start, end)) or (cause=["fraud_hold"]),
    then st.switch_page. Keys: date, country, psp (sidebar) or a PAGE_FIELDS name."""
    st.session_state["handoff"] = values


def _reset() -> None:
    page_keys = [f"{prefix}_{name}" for name in PAGE_FIELDS for prefix in ("w", "f")]
    for key in [*KEYS.values(), *page_keys]:
        st.session_state.pop(key, None)


def clear() -> None:
    """'Clear filters': sidebar and page-only filters back to defaults."""
    _reset()
    st.query_params.clear()
