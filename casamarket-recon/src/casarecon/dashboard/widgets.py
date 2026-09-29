"""Page-only filter widgets (shared by Outliers and Drill-down).

Values are kept in plain keys (f_*), because Streamlit deletes a widget's key when the
widget is not drawn on the current page. Cross-page links write f_* (see filters.set_handoff).
"""

import streamlit as st

from casarecon.dashboard import theme

XB_LABELS = {"all": "All", "cross": "Cross-border", "domestic": "Domestic"}


def _keep(name: str, default: object) -> object:
    return st.session_state.get(f"f_{name}", default)


def _save(name: str) -> None:
    st.session_state[f"f_{name}"] = st.session_state[f"w_{name}"]


def _multi(col, label: str, name: str, options: list[str], placeholder: str, fmt=str) -> tuple:
    kept = [v for v in _keep(name, []) if v in options]
    return tuple(col.multiselect(label, options, default=kept, key=f"w_{name}", on_change=_save,
                                 args=(name,), placeholder=placeholder, format_func=fmt))


def segment_filters(opts: dict, more: bool = False) -> dict:
    """Size tier, cross-border, cause (+ weekday, category when `more`) -> Filters fields."""
    c1, c2, c3 = st.columns(3)
    out = {"tier": _multi(c1, "Size tier (USD)", "tier", opts["tier"], "All tiers")}
    xb_keys = list(XB_LABELS)
    out["xb"] = c2.radio("Cross-border", xb_keys, index=xb_keys.index(_keep("xb", "all")),
                         format_func=XB_LABELS.get, horizontal=True, key="w_xb", on_change=_save,
                         args=("xb",))
    out["cause"] = _multi(c3, "Likely cause", "cause", opts["cause"], "All causes", theme.cause_label)
    if more:
        c4, c5, _ = st.columns(3)
        out["weekday"] = _multi(c4, "Weekday (auth)", "weekday", opts["weekday"], "All days")
        out["category"] = _multi(c5, "Category", "category", opts["category"], "All categories",
                                 lambda c: theme.CATEGORY_LABELS.get(c, c))
    return out


def min_usd(default: float = 50) -> float:
    value = st.number_input(
        "Min discrepancy after FX (USD)", min_value=0.0, value=float(_keep("min_usd", default)),
        step=10.0, format="%.0f", key="w_min_usd", on_change=_save, args=("min_usd",),
        help="Shows rows where |settled − expected settle| in USD is greater than this (strict >).")
    return float(value)
