"""Page-only filter widgets (shared by Outliers and, later, Drill-down).

Values are kept in plain keys (f_*), because Streamlit deletes a widget's key when the
widget is not drawn on the current page.
"""

import streamlit as st

XB_LABELS = {"all": "All", "cross": "Cross-border", "domestic": "Domestic"}


def _keep(name: str, default: object) -> object:
    return st.session_state.get(f"f_{name}", default)


def _save(name: str) -> None:
    st.session_state[f"f_{name}"] = st.session_state[f"w_{name}"]


def segment_filters(opts: dict) -> dict:
    """Size tier, cross-border and cause -> Filters fields {tier, xb, cause}."""
    c1, c2, c3 = st.columns(3)
    tier = c1.multiselect("Size tier (USD)", opts["tier"], default=_keep("tier", []), key="w_tier",
                          on_change=_save, args=("tier",), placeholder="All tiers")
    xb = c2.radio("Cross-border", list(XB_LABELS), index=list(XB_LABELS).index(_keep("xb", "all")),
                  format_func=XB_LABELS.get, horizontal=True, key="w_xb", on_change=_save,
                  args=("xb",))
    cause = c3.multiselect("Likely cause", opts["cause"], default=_keep("cause", []), key="w_cause",
                           on_change=_save, args=("cause",), placeholder="All causes")
    return {"tier": tuple(tier), "xb": xb, "cause": tuple(cause)}


def min_usd(default: float = 50) -> float:
    value = st.number_input(
        "Min discrepancy after FX (USD)", min_value=0.0, value=float(_keep("min_usd", default)),
        step=10.0, key="w_min_usd", on_change=_save, args=("min_usd",),
        help="Shows rows where |settled − expected settle| in USD is greater than this (strict >).")
    return float(value)
