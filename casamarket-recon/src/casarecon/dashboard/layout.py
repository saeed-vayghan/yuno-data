"""Shared page frame: title, as-of banner, active-filter line. Pure text builders are tested."""

import streamlit as st

from casarecon.dashboard import data, filters, states
from casarecon.dashboard import format as fmt


def as_of_text(s: dict) -> str:
    """'Data as of 2026-06-30 · Last closed week W25 (Jun 15–21) · 135,000 rows'."""
    as_of = s["as_of"]
    day = as_of.date() if hasattr(as_of, "date") else as_of
    week = fmt.week_label(s["last_closed_week"], data.to_date(s["last_closed_start"]),
                          data.to_date(s["last_closed_end"]))
    rows = f" · {fmt.count(s['n_rows'])} rows" if s.get("n_rows") is not None else ""
    return f"Data as of {day:%Y-%m-%d} · Last closed week {week}{rows}"


def closed_week_label() -> str | None:
    """'W25 (Jun 15–21)' from core status; None when status is not available."""
    try:
        s = data.status()
    except Exception:  # noqa: BLE001 - a title detail only
        return None
    return fmt.week_label(s["last_closed_week"], data.to_date(s["last_closed_start"]),
                          data.to_date(s["last_closed_end"]))


def as_of_banner() -> None:
    def render() -> None:
        st.caption(as_of_text(data.status()))

    states.section("Data status", render)


def page_header(title: str, uses: set[str]) -> None:
    """Title, as-of banner and the 'Active: …' line; call first in every page body."""
    st.title(title)
    as_of_banner()
    f = st.session_state.get("filters", data.Filters())
    st.caption(filters.describe(f, uses))


def chart_data(df, columns: dict[str, str], label: str = "Chart data (table)") -> None:
    """Every chart's numbers also as a table (screen readers, copy/paste). columns: {col: header}."""
    with st.expander(label):
        st.dataframe(df[list(columns)].rename(columns=columns), hide_index=True)


def pages() -> dict:
    """The st.Page objects registered by app.py (for st.page_link / st.switch_page)."""
    return st.session_state.get("PAGES", {})


def placeholder(title: str, milestone: str, what: str) -> None:
    """Simple 'coming soon' page body for pages planned in a later milestone."""
    page_header(title, uses=set(filters.GLOBAL))
    st.info(f"**Coming in {milestone}.** {what}", icon="🚧")
