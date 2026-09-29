"""Alerts: what needs attention this week, and who owns it (reads `recon alerts` output only)."""

import pandas as pd
import streamlit as st

from casarecon.dashboard import alerts_view as av
from casarecon.dashboard import data, filters, layout, states, theme
from casarecon.dashboard import format as fmt

MIN_ROWS = 50


def _badge_style(text: str) -> str:
    """Optional light tint on the Severity cell; the icon + word always carry the meaning."""
    if text.startswith("✓"):
        color = theme.RESOLVED[0]
    else:
        color = next((c for c, label in theme.SEVERITY.values() if label == text), None)
    return f"background-color: {theme.tint(color)}; color: {theme.TEXT}" if color else ""


def counts_row(alerts: pd.DataFrame) -> None:
    c = av.counts(alerts)
    cols = st.columns(4)
    labels = [theme.SEVERITY["SEV2"][1], theme.SEVERITY["SEV3"][1], theme.SEVERITY["INFO"][1],
              theme.RESOLVED[1]]
    helps = ["Open (NEW or ONGOING) alerts to act on today.", "Open alerts for the weekly review.",
             "Report-only rows, incl. segments with too little data.",
             "Fired last week, not this week."]
    for col, label, key, help_text in zip(cols, labels, ["SEV2", "SEV3", "INFO", "RESOLVED"], helps):
        col.metric(label, c[key], help=help_text, border=True)


def active_table(active: pd.DataFrame) -> None:
    c1, c2, c3 = st.columns(3)
    sev = c1.multiselect("Severity", list(av.SEV_ORDER), placeholder="All", key="al_sev")
    status = c2.multiselect("Status", ["NEW", "ONGOING", "RESOLVED"], placeholder="All",
                            key="al_status")
    rules = c3.multiselect("Rule", list(av.RULES), format_func=av.rule_name, placeholder="All",
                           key="al_rule")
    shown = av.pick(active, severity=sev, status=status, rule_id=rules)
    if shown.empty:
        states.empty("No alerts match these filters.")
        return
    styled = (av.table(shown).style.map(_badge_style, subset=["Severity"])
              .map(lambda s: "font-weight: 700" if s == "NEW" else "", subset=["Status"]))
    st.dataframe(styled, hide_index=True, column_config={
        "Message": st.column_config.TextColumn(width="large"),
        "n": st.column_config.NumberColumn("n", format="%d", help="Rows behind the alert.")})
    segment_link(shown)


def segment_link(shown: pd.DataFrame) -> None:
    linkable = shown[[bool(av.handoff(r)) for _, r in shown.iterrows()]]
    if linkable.empty:
        return
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    i = c1.selectbox("View segment", list(linkable.index), key="al_segment",
                     format_func=lambda i: f"{av.rule_name(shown.at[i, 'rule_id'])} · "
                                           f"{av.segment_text(shown.at[i, 'segment'])}")
    if i is not None and c2.button("Open in Drill-down →", key="al_open"):
        filters.set_handoff(**av.handoff(shown.loc[i]))
        st.switch_page(layout.pages()["drill_down"])


def insufficient(rows: pd.DataFrame) -> None:
    with st.expander(f"Insufficient data ({len(rows)})"):
        if rows.empty:
            st.caption("Every rule had enough rows.")
            return
        st.dataframe(pd.DataFrame({"Rule": rows["rule_id"].map(av.rule_name),
                                   "Segment": rows["segment"].map(av.segment_text), "n": rows["n"],
                                   "Needs": f"{MIN_ROWS} rows per week"}), hide_index=True)


def rule_help() -> None:
    with st.expander("What each rule means"):
        for name, question, trigger in av.RULES.values():
            st.markdown(fmt.md(f"**{name}**: {question} {trigger}"))
        st.caption("Status compares the last closed week with the one before: NEW = fires now, "
                   "not before · ONGOING = both · RESOLVED = before, not now.")


def render() -> None:
    week = layout.closed_week_label()
    layout.page_header(f"Alerts · last closed week {week}" if week else "Alerts", set())
    alerts = data.alerts()
    if alerts is None:
        st.info("No alerts file yet. Run `recon alerts` or `make all` first.", icon="ℹ️")
        rule_help()
        return
    active, thin = av.split(alerts)
    counts_row(alerts)
    if active.empty and not thin.empty:
        st.info(f"Not enough data for alerts (each needs {MIN_ROWS} rows per week). "
                "Run the full dataset with `make all`.", icon="ℹ️")
    elif not (active["status"].isin(av.OPEN)).any():
        st.success(f"No open alerts{' for ' + week if week else ''}. All rules checked.", icon="✅")
    if not active.empty:
        active_table(active)
    insufficient(thin)
    rule_help()


states.guarded(render, "Alerts")
