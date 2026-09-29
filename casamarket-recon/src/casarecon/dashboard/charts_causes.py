"""Pure chart builders for Root causes: loss by cause (bars) and PSP × country flag rate (heatmap)."""

import pandas as pd
import plotly.graph_objects as go

from casarecon.dashboard import format as fmt
from casarecon.dashboard import theme


def cause_rows(cs: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """(causes with rows, sorted by net loss desc; codes ruled out with 0 rows)."""
    ruled_out = cs.loc[cs["n"] == 0, "likely_cause"].tolist()
    return cs[cs["n"] > 0].sort_values("net_usd", ascending=False), ruled_out


def cause_bars(cs: pd.DataFrame) -> go.Figure:
    """Net USD loss by likely cause, one hue (vermilion), '$41,200 · 32%' on each bar."""
    d = cause_rows(cs)[0].iloc[::-1]  # largest at the top
    labels = [f"{fmt.usd_compact(r['net_usd'])} · {r['share_of_loss'] * 100:.0f}%"
              for _, r in d.iterrows()]
    fig = go.Figure(go.Bar(
        x=d["net_usd"], y=d["likely_cause"].map(theme.cause_label), orientation="h",
        marker={"color": theme.UNDER}, text=labels, textposition="outside", cliponaxis=False,
        customdata=d[["n"]].to_numpy(),
        hovertemplate="%{y}<br>Net loss $%{x:,.0f}<br>n = %{customdata[0]:,}<extra></extra>",
    ))
    fig.update_xaxes(rangemode="tozero", tickprefix="$")
    theme.style(fig, "Net loss by likely cause (USD, full data period)", "")
    return fig.update_layout(height=max(260, 40 * len(d) + 90), margin={"r": 120})


def cause_takeaway(cs: pd.DataFrame) -> str:
    d = cause_rows(cs)[0]
    if d.empty:
        return "No discrepancies with a cause label."
    top = d.iloc[0]
    share = top["share_of_loss"] * 100
    return f"Top cause: {theme.cause_label(top['likely_cause'])}, {share:.0f}% of the loss."


def split_segment(value: str) -> tuple[str, str]:
    """'PSP_B|AR' -> ('PSP_B', 'AR')."""
    psp, _, country = str(value).partition("|")
    return psp, country


def heatmap(seg: pd.DataFrame) -> go.Figure:
    """Flag rate (%) by PSP × country; value in every cell, n<30 cells blank with 'n<30'."""
    d = seg.assign(psp=[split_segment(v)[0] for v in seg["segment_value"]],
                   country=[split_segment(v)[1] for v in seg["segment_value"]])
    d["z"] = (d["rate"] * 100).where(~d["low_sample"].astype(bool))
    d["label"] = [("n<30" if pd.isna(z) else f"{z:.1f}") for z in d["z"]]
    z = d.pivot(index="psp", columns="country", values="z").sort_index(ascending=False)
    text = d.pivot(index="psp", columns="country", values="label").reindex_like(z).fillna("—")
    fig = go.Figure(go.Heatmap(
        z=z.to_numpy(), x=list(z.columns), y=list(z.index), text=text.to_numpy(),
        texttemplate="%{text}", colorscale="Oranges", colorbar={"title": "%"},
        hovertemplate="%{y} · %{x}<br>Flag rate %{text}%<extra></extra>", xgap=2, ygap=2,
    ))
    return theme.style(fig, "Flag rate by PSP and country (%)", "")


def heatmap_takeaway(seg: pd.DataFrame) -> str:
    ok = seg[~seg["low_sample"].astype(bool)]
    if ok.empty:
        return "Every cell is low sample (n<30)."
    top = ok.loc[ok["rate"].idxmax()]
    psp, country = split_segment(top["segment_value"])
    return f"Highest cell: {psp} in {country} at {fmt.rate(top['rate'])} (n {fmt.count(top['n'])})."
