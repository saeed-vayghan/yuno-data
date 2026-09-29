"""Root causes & actions: what drives the loss (FR2 evidence) and what to do about it (FR4)."""

import streamlit as st

from casarecon.dashboard import cards, charts_causes, data, filters, layout, states, theme
from casarecon.dashboard import format as fmt

USES = {"country", "psp"}


def causes() -> None:
    cs = data.cause_summary(filters.current(USES))
    if cs.empty:
        states.empty()
        return
    st.plotly_chart(charts_causes.cause_bars(cs), config=theme.PLOTLY_CONFIG)
    ruled_out = charts_causes.cause_rows(cs)[1]
    note = "".join(f" {theme.cause_label(c)}: ruled out (0 rows)." for c in ruled_out)
    st.caption(charts_causes.cause_takeaway(cs) + note)
    layout.chart_data(cs, {"likely_cause": "Cause", "n": "n", "net_usd": "Net loss (USD)",
                           "share_of_loss": "Share of loss"})
    codes = charts_causes.cause_rows(cs)[0]["likely_cause"].tolist()
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    code = c1.selectbox("Drill into cause", codes, format_func=theme.cause_label, key="rc_cause",
                        help="Opens Drill-down with this cause selected.")
    if code and c2.button("Go →", key="rc_go"):
        filters.set_handoff(cause=[code])
        st.switch_page(layout.pages()["drill_down"])
    with st.expander("What each cause means"):
        for label, meaning in theme.CAUSES.values():
            st.markdown(f"**{label}**: {meaning}")


def key_findings() -> None:
    st.subheader("Key findings")
    doc = data.findings()
    if doc is None:
        st.info("Findings are not built yet. Run `make all`.", icon="ℹ️")
        return
    items = sorted(doc["items"], key=lambda i: -(i.get("usd_quarter") or 0))
    for item in items:
        st.markdown(fmt.md(cards.finding_line(item)))
    if not items:
        st.caption("No finding passed q < 0.05.")


def heatmap() -> None:
    seg = data.segment_rates("psp_country", None)
    st.plotly_chart(charts_causes.heatmap(seg), config=theme.PLOTLY_CONFIG)
    st.caption(charts_causes.heatmap_takeaway(seg))
    layout.chart_data(seg, {"segment_value": "PSP|country", "n": "n", "rate": "Flag rate",
                            "low_sample": "Low sample"})


def excess() -> None:
    st.subheader("Excess loss vs peers (top 5)")
    ex = data.excess_loss(5)
    view = ex.assign(segment=ex["psp"] + " · " + ex["country"])
    col = st.column_config
    st.dataframe(view[["segment", "n", "rate", "peer_rate", "lift", "excess_usd", "median_loss_usd"]],
                 hide_index=True, column_config={
                     "segment": col.TextColumn("Segment"), "n": col.NumberColumn("n", format="%d"),
                     "rate": col.NumberColumn("Rate", format="percent"),
                     "peer_rate": col.NumberColumn("Peer rate", format="percent"),
                     "lift": col.NumberColumn("Lift", format="%.2f×"),
                     "excess_usd": col.NumberColumn("Excess loss (USD)", format="dollar"),
                     "median_loss_usd": col.NumberColumn("Median loss (USD)", format="dollar")})
    st.caption("Excess loss = (segment rate − peer rate) × volume × mean loss. An estimate. "
               "Peers = other PSPs in the same country.")


def recommendations() -> None:
    st.subheader("Recommendations (ranked by $ impact)")
    recs = data.recommendations()
    if recs is None:
        st.info("Recommendations are not built yet. Run `make all`.", icon="ℹ️")
        return
    if not recs:
        st.caption("No recommendation yet: no finding passed the significance bar.")
    for r in sorted(recs, key=lambda r: r["rank"]):
        st.markdown(fmt.md(cards.recommendation_line(r)))
        with st.expander("How to implement"):
            st.markdown(fmt.md(r["implementation"]))


def full_findings() -> None:
    doc = data.findings()
    if doc and doc.get("markdown"):
        with st.expander("Full findings (FINDINGS.md)"):
            st.markdown(fmt.md(doc["markdown"]))


def render() -> None:
    layout.page_header("Root causes & actions", USES)
    states.section("Loss by likely cause", causes)
    states.section("Key findings", key_findings)
    left, right = st.columns(2)
    with left:
        states.section("PSP × country heatmap", heatmap)
    with right:
        states.section("Excess loss vs peers", excess)
    states.section("Recommendations", recommendations)
    states.section("Full findings", full_findings)


states.guarded(render, "Root causes & actions")
