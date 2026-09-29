"""Colours in one place (Okabe-Ito) + the shared Plotly template.

Colour is never the only signal: always pair it with a word, icon or sign.
Category colours and PSP colours never appear in the same chart.
"""

import plotly.graph_objects as go

CATEGORY_COLORS = {"exact": "#8C8C8C", "rounding": "#56B4E9", "fx_tolerance": "#0072B2",
                   "meaningful": "#E69F00", "large": "#D55E00"}
CATEGORY_LABELS = {"exact": "Exact", "rounding": "Rounding", "fx_tolerance": "FX noise",
                   "meaningful": "Meaningful", "large": "Large"}
CATEGORY_ORDER = ["exact", "rounding", "fx_tolerance", "meaningful", "large"]
PSP_COLORS = {"PSP_A": "#0072B2", "PSP_B": "#E69F00", "PSP_C": "#009E73",
              "PSP_D": "#CC79A7", "PSP_E": "#56B4E9"}
PORTFOLIO_COLOR = "#0072B2"
SEVERITY = {"SEV2": ("#D55E00", "▲ SEV2 · same day"), "SEV3": ("#E69F00", "● SEV3 · weekly"),
            "INFO": ("#0072B2", "ℹ Info")}
RESOLVED = ("#009E73", "✓ Resolved")
UNDER, OVER = "#D55E00", "#0072B2"
LOW_SAMPLE_OPACITY = 0.4
TEXT = "#1F2328"
MUTED = "#57606A"
GRID = "#E6E8EB"
CHART_HEIGHT = 360


def plotly_template() -> go.layout.Template:
    """Light, recessive grid; sentence-case titles; one font."""
    return go.layout.Template(layout=go.Layout(
        font={"family": "sans-serif", "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        xaxis={"gridcolor": GRID, "linecolor": GRID, "zeroline": False},
        yaxis={"gridcolor": GRID, "linecolor": GRID, "zerolinecolor": GRID, "rangemode": "tozero"},
        hoverlabel={"bgcolor": "#FFFFFF", "font": {"color": TEXT}},
        legend={"orientation": "h", "y": -0.18, "x": 0},
        colorway=list(PSP_COLORS.values()),
    ))


def style(fig: go.Figure, title: str, y_title: str) -> go.Figure:
    """Apply the template, a title with units, a fixed height and small margins."""
    fig.update_layout(template=plotly_template(), title={"text": title, "x": 0},
                      height=CHART_HEIGHT, margin={"l": 8, "r": 64, "t": 48, "b": 8},
                      yaxis_title=y_title, xaxis_title=None)
    return fig


PLOTLY_CONFIG = {"displaylogo": False}
