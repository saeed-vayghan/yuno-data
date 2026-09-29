"""Drill-down: slice by segment, see flag rates with 95% ranges, and the rows behind them."""

import streamlit as st

from casarecon.dashboard import charts_segments, data, filters, layout, states, tables, theme, widgets
from casarecon.dashboard import format as fmt

USES = {"date", "country", "psp", "tier", "xb", "weekday", "category", "cause"}
LIMIT = 1000
CSV_MAX = 50_000
GROUPS = {"Country": "country", "PSP": "psp", "Size tier": "amount_tier", "Weekday": "weekday",
          "Cross-border": "cross_border", "Settle lag": "lag_bucket"}


def summary(f: data.Filters) -> int:
    """Rows · flag rate · net loss for the whole filtered period; returns n."""
    k = data.kpis(f, week="all")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", fmt.count(k["n"]), help="Settled transactions matching the filters.",
              border=True)
    c2.metric("Flag rate", fmt.rate(k["flag_rate"]), border=True,
              help="Share of settled rows with a meaningful or large discrepancy after FX.")
    c3.metric("Net loss", fmt.usd_compact(k["net_usd"]), border=True,
              help="Net USD loss (under-settled minus over-settled).")
    return int(k["n"])


def group_chart(f: data.Filters) -> None:
    group = st.segmented_control("Group by", list(GROUPS), default="PSP", key="dd_group") or "PSP"
    seg = data.segment_rates(GROUPS[group], f)
    if seg.empty:
        states.empty()
        return
    st.plotly_chart(charts_segments.rate_bars(seg, group), config=theme.PLOTLY_CONFIG)
    st.caption(charts_segments.rate_takeaway(seg))


def mix_chart(f: data.Filters) -> None:
    mix = data.category_mix(f)
    if mix.empty:
        return
    st.plotly_chart(charts_segments.category_mix(mix), config=theme.PLOTLY_CONFIG)
    last_closed = None
    try:
        last_closed = data.status()["last_closed_week"]
    except Exception:  # noqa: BLE001 - caption falls back to the latest week
        pass
    st.caption(charts_segments.mix_takeaway(mix, last_closed))


def table(f: data.Filters, n: int | None) -> None:
    rows = data.transactions(f, None, LIMIT)
    st.subheader("Transactions")
    note = tables.cap_note(len(rows), n or len(rows), csv=(n or 0) <= CSV_MAX)
    if note:
        st.caption(note)
    st.dataframe(tables.txn_view(rows, tables.DRILL_COLUMNS), hide_index=True,
                 column_config=tables.txn_columns(), key="dd_tbl")
    if n is not None and n > CSV_MAX:
        st.caption(f"{fmt.count(n)} rows is too many for a browser download. Narrow the filters, "
                   "or use `uv run recon query --format csv`.")
    else:
        st.download_button("Download CSV", data=data.transactions_csv(f), mime="text/csv",
                           file_name="casamarket_drilldown.csv", key="dd_csv")


def render() -> None:
    layout.page_header("Drill-down", USES)
    f = filters.current(USES, **widgets.segment_filters(data.options(), more=True))
    n = states.section("Summary", lambda: summary(f))
    if n == 0:
        states.empty()
        st.button("Clear filters", on_click=filters.clear, key="dd_clear")
        st.stop()
    states.section("Flag rate by group", lambda: group_chart(f))
    states.section("Category mix", lambda: mix_chart(f))
    states.section("Transactions", lambda: table(f, n))


states.guarded(render, "Drill-down")
