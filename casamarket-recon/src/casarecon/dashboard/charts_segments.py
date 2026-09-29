"""Pure chart builders for Drill-down and Root causes. DataFrame in, styled Plotly figure out.

Rules: ranking = horizontal bars sorted, value label on each bar, axis from 0; 95% ranges hidden
when n < 30 (greyed, 'low sample'); mix = 100% stacked, order exact -> large; heatmap = one hue
with the value in every cell. Category colours and PSP colours never share a chart.
"""

import pandas as pd
import plotly.graph_objects as go

from casarecon.dashboard import format as fmt
from casarecon.dashboard import theme

LOW = "low sample (n<30)"
LOW_GREY = "#8C8C8C"
VALUE_LABELS = {"true": "Cross-border", "false": "Domestic"}  # boolean segments read as words


def rate_label(r: pd.Series) -> str:
    """'21.3% [19.8–22.9] · n 3,020' or '9.0% · low sample (n<30)'."""
    if bool(r["low_sample"]):
        return f"{fmt.rate(r['rate'])} · {LOW}"
    return f"{fmt.rate_range(r['rate'], r['ci_low'], r['ci_high'])} · n {fmt.count(r['n'])}"


def rate_bars(seg: pd.DataFrame, group: str) -> go.Figure:
    """Flag rate by segment with Wilson 95% ranges; low-sample bars grey, no range, sorted last."""
    # plotly draws the first row at the bottom: low sample first, then reliable by rate ascending
    d = seg.assign(_low=seg["low_sample"].astype(bool)).sort_values(
        ["_low", "rate"], ascending=[False, True])
    ok = ~d["_low"]
    err_plus = ((d["ci_high"] - d["rate"]) * 100).where(ok, 0)
    err_minus = ((d["rate"] - d["ci_low"]) * 100).where(ok, 0)
    fig = go.Figure(go.Bar(
        x=d["rate"] * 100, y=d["segment_value"].astype(str).replace(VALUE_LABELS), orientation="h",
        marker={"color": [theme.PORTFOLIO_COLOR if o else LOW_GREY for o in ok],
                "opacity": [1.0 if o else theme.LOW_SAMPLE_OPACITY for o in ok]},
        error_x={"type": "data", "array": err_plus, "arrayminus": err_minus, "color": theme.TEXT,
                 "thickness": 1.5, "width": 4},
        text=[rate_label(r) for _, r in d.iterrows()], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{text}<extra></extra>",
    ))
    fig.update_xaxes(rangemode="tozero", ticksuffix="%")
    theme.style(fig, f"Flag rate by {group.lower()} (%), with 95% range", "")
    return fig.update_layout(height=max(260, 44 * len(d) + 90), margin={"r": 190})


def rate_takeaway(seg: pd.DataFrame) -> str:
    ok = seg[~seg["low_sample"].astype(bool)]
    if ok.empty:
        return "Every group is low sample (n<30); no reliable ranking."
    top = ok.loc[ok["rate"].idxmax()]
    name = VALUE_LABELS.get(str(top["segment_value"]), top["segment_value"])
    return (f"Highest: {name} at {fmt.rate(top['rate'])}, range "
            f"{top['ci_low'] * 100:.1f}–{top['ci_high'] * 100:.1f}%.")


def category_mix(mix: pd.DataFrame) -> go.Figure:
    """100% stacked bars per week, categories exact -> large, labels as words."""
    fig = go.Figure()
    for cat in theme.CATEGORY_ORDER:
        c = mix[mix["category"] == cat]
        if c.empty:
            continue
        label = theme.CATEGORY_LABELS[cat]
        fig.add_bar(x=c["auth_week"].str.split("-").str[-1], y=c["share"] * 100, name=label,
                    marker={"color": theme.CATEGORY_COLORS[cat]}, customdata=c[["n"]].to_numpy(),
                    hovertemplate=f"{label} · %{{x}}<br>%{{y:.1f}}%<br>n = %{{customdata[0]:,}}"
                                  "<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.2, showlegend=True)
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return theme.style(fig, "Category mix by week (% of settled rows)", "Share (%)")


def mix_takeaway(mix: pd.DataFrame, week: str | None) -> str:
    if mix.empty:
        return "No rows."
    week = week if week in set(mix["auth_week"]) else mix["auth_week"].max()
    large = mix[(mix["auth_week"] == week) & (mix["category"] == "large")]["share"].sum()
    return f"Large discrepancies were {fmt.rate(large)} of settled rows in {week.split('-')[-1]}."
