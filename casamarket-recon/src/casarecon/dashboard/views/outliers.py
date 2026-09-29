"""Outliers: 'Show me all transactions with discrepancies over $50' (strict > min, USD after FX)."""

import pandas as pd
import streamlit as st

from casarecon.dashboard import data, filters, layout, states, tables, widgets

USES = {"date", "country", "psp", "tier", "xb", "cause"}
LIMIT = 1000
DEFINITION = ("ⓘ Discrepancy = settled minus expected settle (FX move removed), "
              "in USD at the auth-day rate.")


def summary(f: data.Filters, min_usd: float, shown: int) -> int:
    """Summary line from core; falls back to the shown row count while outlier_summary is not built."""
    try:
        s = data.outlier_summary(f, min_usd)
    except NotImplementedError:
        st.caption(f"{shown:,} transactions shown (totals not available yet).")
        return shown
    st.markdown(tables.summary_line(s["n"], s["gross_under_usd"], s["gross_over_usd"]))
    return int(s["n"])


def file_name(min_usd: float) -> str:
    try:
        tag = f"{data.status()['as_of']:%Y-%m-%d}"
    except Exception:  # noqa: BLE001 - name only; status may not be built yet
        tag = "latest"
    return f"casamarket_outliers_min{min_usd:g}usd_{tag}.csv"


def detail(rows: pd.DataFrame, selected: list[int]) -> None:
    if not selected:
        st.caption("Select a row to see why it was flagged.")
        return
    row = rows.iloc[selected[0]]  # same frame as displayed: no re-query between display and lookup
    with st.container(border=True):
        st.markdown(f"**Selected:** `{row['transaction_id']}`")
        for line in tables.detail_lines(row):
            st.markdown(line)
        st.code(row["transaction_id"], language=None)
        st.caption("Full FX detail and 'similar rows' arrive with the Drill-down page (M2).")


def render() -> None:
    layout.page_header("Outliers", USES)
    min_usd = widgets.min_usd()
    f = filters.current(USES, category=("large",), **widgets.segment_filters(data.options()))
    st.caption(DEFINITION)
    rows = data.transactions(f, min_usd=min_usd, limit=LIMIT)
    total = summary(f, min_usd, len(rows))
    if rows.empty:
        states.empty(f"No transactions over ${min_usd:,.0f}. Try a lower minimum or clear filters.")
        return
    note = tables.cap_note(len(rows), total)
    if note:
        st.caption(note)
    st.download_button("Download CSV", data=data.transactions_csv(f, min_usd), mime="text/csv",
                       file_name=file_name(min_usd), key="out_csv")
    view = tables.outlier_view(rows)
    event = st.dataframe(view, hide_index=True, column_config=tables.outlier_columns(),
                         on_select="rerun", selection_mode="single-row", key="out_tbl")
    detail(rows.reset_index(drop=True), list(event.selection.rows) if event else [])


states.guarded(render, "Outliers")
