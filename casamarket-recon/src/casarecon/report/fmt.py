"""Jinja filters (pure): every number in the reports goes through one of these."""

import math
from collections.abc import Sequence


def _missing(x: object) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def usd(x: float | None) -> str:
    """18400.12 -> '$18,400'; -5 -> '-$5'."""
    if _missing(x):
        return "n/a"
    return f"{'-' if x < 0 else ''}${abs(x):,.0f}"


def count(x: float | None) -> str:
    """12345 -> '12,345'."""
    return "n/a" if _missing(x) else f"{int(x):,}"


def pct(x: float | None) -> str:
    """Fraction -> '17.1%'."""
    return "n/a" if _missing(x) else f"{x * 100:.1f}%"


def pts(x: float | None) -> str:
    """Fraction difference -> '+3.5 pts'."""
    return "n/a" if _missing(x) else f"{x * 100:+.1f} pts"


def qval(x: float | None) -> str:
    """'q < 0.001' or 'q = 0.012'."""
    if _missing(x):
        return "q n/a"
    return "q < 0.001" if x < 0.001 else f"q = {x:.3f}"


def ci(pair: Sequence[float | None]) -> str:
    """[0.162, 0.181] -> '[16.2–18.1%]'."""
    lo, hi = pair
    return "n/a" if _missing(lo) or _missing(hi) else f"[{lo * 100:.1f}–{hi * 100:.1f}%]"


def ratio(x: float | None) -> str:
    """Lift -> '1.26×' ('n/a, peers at 0' when the peer rate is 0)."""
    return "n/a, peers at 0" if _missing(x) else f"{x:.2f}×"


RATE_COLS = {"rate", "ci_low", "ci_high", "peer_rate", "share_of_loss", "flag_rate", "late_share",
             "precision", "recall", "share_of_cause_in_country", "psp_share_of_country_volume"}


def cell(col: str, v: object) -> str:
    """Format one table cell by column name."""
    if _missing(v):
        return ""
    if isinstance(v, bool) or not isinstance(v, int | float):
        return str(v)
    if col in RATE_COLS:
        return pct(v)
    if col in {"p", "q"}:
        return qval(v).removeprefix("q ").removeprefix("= ")
    if col.endswith("_usd") or col == "usd":
        return usd(v)
    if isinstance(v, int) or float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:.3g}"


def md_table(rows: Sequence[dict], cols: Sequence[str]) -> str:
    """Rows -> a Markdown table with the given columns ('_No rows._' if empty)."""
    if not rows:
        return "_No rows._"
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "\n".join("| " + " | ".join(cell(c, r.get(c)) for c in cols) + " |" for r in rows)


FILTERS = {"count": count, "usd": usd, "pct": pct, "pts": pts, "q": qval, "ci": ci, "ratio": ratio,
           "table": md_table}
