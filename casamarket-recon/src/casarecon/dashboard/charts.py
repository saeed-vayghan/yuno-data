"""Pure chart builders: DataFrame in, styled Plotly figure out. No Streamlit here.

Input frames follow core `weekly_trend` columns: auth_week, week_start, series, n, rate,
net_usd, is_closed, low_sample. Open (not closed) weeks are dashed / lighter + labelled.
"""

import pandas as pd
import plotly.graph_objects as go

from casarecon.dashboard import format as fmt
from casarecon.dashboard import theme

OPEN_NOTE = "not closed yet"


def _color(series: str) -> str:
    return theme.PSP_COLORS.get(series, theme.PORTFOLIO_COLOR)


def _mark_open(fig: go.Figure, df: pd.DataFrame) -> None:
    open_weeks = df.loc[~df["is_closed"].astype(bool), "week_start"]
    if not open_weeks.empty:
        fig.add_vrect(x0=open_weeks.min(), x1=open_weeks.max(), fillcolor=theme.GRID, opacity=0.4,
                      line_width=0, annotation_text=OPEN_NOTE, annotation_position="top left")


def line_weekly(df: pd.DataFrame, y: str = "rate") -> go.Figure:
    """Weekly flag rate (%), one line per `series`; open weeks dashed; direct end labels."""
    fig = go.Figure()
    for name, g in df.sort_values("week_start").groupby("series", sort=True):
        closed = g[g["is_closed"].astype(bool)]
        tail = pd.concat([closed.tail(1), g[~g["is_closed"].astype(bool)]])
        label = "Portfolio" if name == "ALL" else str(name)
        hover = f"{label} · %{{x|%b %d}}<br>%{{y:.1f}}%<br>n = %{{customdata:,}}<extra></extra>"
        fig.add_scatter(x=closed["week_start"], y=closed[y] * 100, mode="lines+markers", name=label,
                        line={"color": _color(name), "width": 2}, marker={"size": 8},
                        customdata=closed["n"], hovertemplate=hover)
        if len(tail) > 1:
            fig.add_scatter(x=tail["week_start"], y=tail[y] * 100, mode="lines+markers",
                            name=f"{label} ({OPEN_NOTE})", showlegend=False, opacity=0.6,
                            line={"color": _color(name), "width": 2, "dash": "dash"},
                            marker={"size": 8}, customdata=tail["n"], hovertemplate=hover)
        if name != "ALL" and not closed.empty:
            fig.add_annotation(x=closed["week_start"].iloc[-1], y=closed[y].iloc[-1] * 100,
                               text=label, showarrow=False, xanchor="left", xshift=6,
                               font={"color": theme.TEXT, "size": 12})
    _mark_open(fig, df)
    fig.update_layout(showlegend=df["series"].nunique() > 1)
    return theme.style(fig, "Weekly flag rate (%)", "Flag rate (%)")


def bar_weekly(df: pd.DataFrame, y: str = "net_usd") -> go.Figure:
    """Weekly net loss (USD): vermilion = loss (under), blue = gain (over); open weeks lighter."""
    d = df.sort_values("week_start")
    closed = d["is_closed"].astype(bool)
    fig = go.Figure(go.Bar(
        x=d["week_start"], y=d[y], customdata=d[["n"]].to_numpy(),
        marker={"color": [theme.UNDER if v >= 0 else theme.OVER for v in d[y]],
                "opacity": [1.0 if c else theme.LOW_SAMPLE_OPACITY for c in closed]},
        hovertemplate="%{x|%b %d}<br>Net loss $%{y:,.0f}<br>n = %{customdata[0]:,}<extra></extra>",
    ))
    _mark_open(fig, d)
    fig.update_layout(bargap=0.25)
    return theme.style(fig, "Weekly net loss (USD)", "Net loss (USD)")


def rate_takeaway(df: pd.DataFrame) -> str:
    """One-line caption built from data: the highest closed week (portfolio or series)."""
    closed = df[df["is_closed"].astype(bool)]
    if closed.empty:
        return "No closed weeks yet."
    top = closed.loc[closed["rate"].idxmax()]
    who = "" if top["series"] == "ALL" else f"{top['series']} · "
    return f"Highest closed week: {who}{top['auth_week'].split('-')[-1]} at {fmt.rate(top['rate'])}."


def loss_takeaway(df: pd.DataFrame) -> str:
    closed = df[df["is_closed"].astype(bool)]
    if closed.empty:
        return "No closed weeks yet."
    top = closed.loc[closed["net_usd"].idxmax()]
    total = fmt.usd_compact(closed["net_usd"].sum())
    return (f"Biggest closed-week loss: {top['auth_week'].split('-')[-1]} at "
            f"{fmt.usd_compact(top['net_usd'])}. Closed weeks total {total}.")
