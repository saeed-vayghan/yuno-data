"""Overview: how bad is it, is it getting better, which PSP had the worst week last month?"""

import streamlit as st

from casarecon.dashboard import cards, charts, data, filters, layout, states, theme
from casarecon.dashboard import format as fmt

USES = {"country", "psp"}
HELP = {
    "rate": "Share of settled rows with a meaningful or large discrepancy after FX, last closed week.",
    "net": "Net USD loss (under-settled minus over-settled) in the last closed week.",
    "large": "Rows over 5% or at least $20 off after FX, last closed week.",
    "alerts": "Alerts with status NEW or ONGOING (Info excluded).",
}


def kpi_row() -> None:
    c1, c2, c3, c4 = st.columns(4)

    def core_kpis() -> None:
        k = data.kpis(filters.current(USES), week="last_closed")
        c1.metric("Flag rate", fmt.rate(k["flag_rate"]), delta=fmt.delta_pts(k["delta_rate_pts"]),
                  delta_color="inverse", help=HELP["rate"], border=True)
        c2.metric("Net loss", fmt.usd_compact(k["net_usd"]), delta=fmt.delta_usd(k["delta_net_usd"]),
                  delta_color="inverse", help=HELP["net"], border=True)
        c3.metric("Large rows", fmt.count(k["n_large"]), delta=fmt.delta_int(k["delta_n_large"]),
                  delta_color="inverse", help=HELP["large"], border=True)

    def alerts_kpi() -> None:
        value, note = cards.open_alerts(data.alerts())
        c4.metric("Open alerts", value, help=HELP["alerts"], border=True)
        c4.caption(note)

    with c1:
        states.section("KPIs (last closed week)", core_kpis)
    with c4:
        states.section("Open alerts", alerts_kpi)


def worst_week_card() -> None:
    with st.container(border=True):
        st.subheader("Worst PSP week")
        choices = data.months() or ["last"]
        month = st.selectbox("Month", choices, index=len(choices) - 1, format_func=fmt.month_label,
                             help="A week belongs to the month of its Thursday. Full months only.")
        ranked = data.worst_week(month)
        if ranked.empty:
            states.empty("No PSP-weeks in this month.")
            return
        top = ranked.iloc[0]
        greyed = bool(top["low_sample"])
        st.markdown(f"**{cards.worst_headline(top)}**" if not greyed else
                    f":gray[{cards.worst_headline(top)}]")
        st.markdown(cards.worst_detail(top))
        st.caption(cards.next_line(ranked))
        st.caption("All PSPs and countries (same as `recon worst-week`); sidebar filters not applied.")
        if st.button(cards.link_label(top, "Outliers"), key="ww_open"):
            filters.set_handoff(psp=[top["psp"]], date=(data.to_date(top["week_start"]),
                                                        data.to_date(top["week_end"])))
            st.switch_page(layout.pages()["outliers"])
        with st.expander("All PSP-weeks this month"):
            st.dataframe(ranked, hide_index=True, column_config={
                "rate": st.column_config.NumberColumn("Flag rate", format="percent"),
                "net_usd": st.column_config.NumberColumn("Net loss (USD)", format="dollar"),
                "gross_under_usd": st.column_config.NumberColumn("Gross under (USD)", format="dollar"),
            })


def trends() -> None:
    by = st.segmented_control("Series", ["Portfolio", "By PSP"], default="Portfolio",
                              key="ov_by") or "Portfolio"
    f = filters.current(USES)
    rate_df = data.weekly_trend(f, by="psp" if by == "By PSP" else "portfolio")
    if rate_df.empty:
        states.empty()
        return
    st.plotly_chart(charts.line_weekly(rate_df), config=theme.PLOTLY_CONFIG)
    st.caption(charts.rate_takeaway(rate_df))
    loss_df = rate_df if by == "Portfolio" else data.weekly_trend(f, by="portfolio")
    st.plotly_chart(charts.bar_weekly(loss_df), config=theme.PLOTLY_CONFIG)
    st.caption(charts.loss_takeaway(loss_df))


def week_over_week() -> None:
    st.subheader("Week-over-week (PSP × country)")
    wow = data.week_over_week(filters.current(USES))
    if wow.empty:
        states.empty()
        return
    st.dataframe(wow.assign(change=wow["delta_pts"].map(fmt.delta_pts)), hide_index=True,
                 column_config={
                     "rate_prev": st.column_config.NumberColumn("Rate before", format="percent"),
                     "rate_last": st.column_config.NumberColumn("Rate last", format="percent"),
                     "change": st.column_config.TextColumn("Change"),
                 })


def render() -> None:
    layout.page_header("Overview", USES)
    kpi_row()
    states.section("Worst PSP week", worst_week_card)
    states.section("Weekly trends", trends)
    states.section("Week-over-week", week_over_week)


states.guarded(render, "Overview")
