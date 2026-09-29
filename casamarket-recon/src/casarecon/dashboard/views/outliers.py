"""Outliers: 'Show me all transactions with discrepancies over $50' (strict > min, USD after FX)."""

import pandas as pd
import streamlit as st

from casarecon.dashboard import data, filters, layout, states, tables, theme, widgets
from casarecon.dashboard import format as fmt

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
    st.markdown(fmt.md(tables.summary_line(s["n"], s["gross_under_usd"], s["gross_over_usd"])))
    return int(s["n"])


def file_name(min_usd: float) -> str:
    try:
        tag = f"{data.status()['as_of']:%Y-%m-%d}"
    except Exception:  # noqa: BLE001 - name only; status may not be built yet
        tag = "latest"
    return f"casamarket_outliers_min{min_usd:g}usd_{tag}.csv"


def similar(txn_id: str) -> None:
    sim = data.similar_count(txn_id)
    if not sim.get("n"):
        return
    seg = [sim["psp"], sim["country"], theme.cause_label(sim["likely_cause"])]
    st.markdown(f"**Similar rows:** {sim['n']:,} in {' · '.join(map(str, seg))}")
    if st.button("See similar rows in Drill-down →", key="out_similar"):
        handoff = {"psp": [sim["psp"]], "country": [sim["country"]]}
        if sim["likely_cause"]:
            handoff["cause"] = [sim["likely_cause"]]
        filters.set_handoff(**handoff)
        st.switch_page(layout.pages()["drill_down"])


def detail(rows: pd.DataFrame, selected: list[int]) -> None:
    if not selected:
        st.caption("Select a row to see why it was flagged.")
        return
    row = rows.iloc[selected[0]]  # same frame as displayed: no re-query between display and lookup
    txn_id = row["transaction_id"]
    with st.container(border=True):
        st.markdown(f"**Selected:** `{txn_id}` · {row['psp']} · {row['country']}")
        try:
            d = data.transaction_detail(txn_id) or row.to_dict()
        except NotImplementedError:
            d = row.to_dict()  # rich FX detail not built yet: show what the row has
        for line in tables.detail_lines(d):
            st.markdown(fmt.md(line))
        states.section("Similar rows", lambda: similar(txn_id))
        st.code(txn_id, language=None)


def render() -> None:
    layout.page_header("Outliers", USES)
    min_usd = widgets.min_usd()
    f = filters.current(USES, category=("large",), **widgets.segment_filters(data.options()))
    st.caption(DEFINITION)
    rows = data.transactions(f, min_usd=min_usd, limit=LIMIT)
    total = summary(f, min_usd, len(rows))
    if rows.empty:
        states.empty(f"No transactions over ${min_usd:,.0f}. Try a lower minimum or clear filters.")
        st.button("Clear filters", on_click=filters.clear, key="out_clear")
        return
    note = tables.cap_note(len(rows), total)
    if note:
        st.caption(note)
    st.download_button("Download CSV", data=data.transactions_csv(f, min_usd), mime="text/csv",
                       file_name=file_name(min_usd), key="out_csv")
    view = tables.txn_view(rows)
    event = st.dataframe(view, hide_index=True, column_config=tables.txn_columns(),
                         on_select="rerun", selection_mode="single-row", key="out_tbl")
    detail(rows.reset_index(drop=True), list(event.selection.rows) if event else [])


states.guarded(render, "Outliers")
