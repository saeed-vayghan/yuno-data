"""One Plotly chart per finding (pure: builds figures, the files adapter saves them)."""

import plotly.graph_objects as go


def figure_name(item: dict) -> str:
    """Fixed file stem, e.g. 'f1_psp_b_ar_peer'."""
    return f"{item['id'].lower()}_{item['key']}"


def finding_figure(item: dict) -> go.Figure:
    """Segment vs peers bar chart, 95% CI on the segment bar."""
    rate, peer = item["rate"] or 0.0, item["peer_rate"] or 0.0
    lo, hi = (v if v is not None else rate for v in item["ci"])
    fig = go.Figure(go.Bar(
        x=[item["segment"], "peers"], y=[rate * 100, peer * 100],
        marker_color=["#c0392b", "#7f8c8d"],
        error_y={"type": "data", "symmetric": False, "array": [(hi - rate) * 100, 0],
                 "arrayminus": [(rate - lo) * 100, 0]},
    ))
    fig.update_layout(title=f"{item['id']}. {item['headline']}", yaxis_title=f"{item['metric']} (%)",
                      template="plotly_white", width=720, height=420, showlegend=False)
    return fig
