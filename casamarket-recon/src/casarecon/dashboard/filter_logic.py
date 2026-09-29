"""Pure filter helpers (no Streamlit): URL parsing, scoping, the 'Active: …' text. Unit-tested."""

from dataclasses import replace
from datetime import date

from casarecon.dashboard import data
from casarecon.dashboard import format as fmt

GLOBAL = ("date", "country", "psp")
PAGE_FIELDS = ("tier", "xb", "weekday", "category", "cause")  # widgets.py keeps them in f_<name>
LABELS = {"date": "Auth dates", "country": "Country", "psp": "PSP", "tier": "Size tier",
          "xb": "Cross-border", "cause": "Cause"}


def parse_params(params: dict[str, list[str]], opts: dict) -> tuple[dict, list[str]]:
    """URL values -> widget values; unknown ones are dropped and reported (for a toast)."""
    values, ignored = {}, []
    for name in ("country", "psp"):
        raw = [v for item in params.get(name, []) for v in item.split(",") if v]
        good = [v for v in raw if v in opts.get(name, [])]
        ignored += [f"Ignored unknown {LABELS[name]} '{v}'" for v in raw if v not in good]
        if good:
            values[name] = good
    try:
        dates = [date.fromisoformat(params[k][0]) for k in ("from", "to") if params.get(k)]
        if len(dates) == 2 and dates[0] <= dates[1]:
            values["date"] = tuple(dates)
    except ValueError:
        ignored.append("Ignored a bad date in the URL")
    return values, ignored


def to_params(f: data.Filters, bounds: tuple[date | None, date | None]) -> dict[str, list[str]]:
    """Only non-default values go to the URL, so links stay short."""
    out: dict[str, list[str]] = {}
    if f.country:
        out["country"] = list(f.country)
    if f.psp:
        out["psp"] = list(f.psp)
    if (f.date_from, f.date_to) != bounds and f.date_from and f.date_to:
        out["from"], out["to"] = [f.date_from.isoformat()], [f.date_to.isoformat()]
    return out


def scoped(f: data.Filters, uses: set[str]) -> data.Filters:
    """Drop the global filters a page does not use (e.g. Overview ignores dates)."""
    keep = {"country": f.country if "country" in uses else (), "psp": f.psp if "psp" in uses else ()}
    if "date" not in uses:
        keep |= {"date_from": None, "date_to": None}
    return replace(f, **keep)


def describe(f: data.Filters, uses: set[str]) -> str:
    """'Active: PSP_B · AR · Jun 15–21. Auth dates not used here.'"""
    if not uses:
        return "Sidebar filters not used here (this page covers all segments)."
    parts = [", ".join(f.psp) or "all PSPs", ", ".join(f.country) or "all countries"]
    if "date" in uses and f.date_from and f.date_to:
        parts.append(date_text(f.date_from, f.date_to))
    unused = [LABELS[g] for g in GLOBAL if g not in uses]
    tail = f" {' and '.join(unused)} not used here." if unused else ""
    return f"Active: {' · '.join(parts)}.{tail}"


def date_text(start: date, end: date) -> str:
    """A range that is exactly one ISO week reads 'W24 (Jun 8–14)', else 'Jun 8–20'."""
    year, week, day = start.isocalendar()
    if day == 1 and (end - start).days == 6:
        return fmt.week_label(f"{year}-W{week:02d}", start, end)
    return fmt.day_range(start, end)


def handoff_text(values: dict) -> str:
    """{'psp': ['PSP_B'], 'cause': ['fraud_hold']} -> 'PSP_B · fraud_hold' (for the arrival toast)."""
    parts = [date_text(*v) if k == "date" else ", ".join(map(str, v)) for k, v in values.items()]
    return " · ".join(p for p in parts if p)


def clip(dates: tuple[date, date], bounds: tuple[date | None, date | None]) -> tuple[date, date]:
    """Keep a handed-off date range inside the data range (a week may start before the data)."""
    lo, hi = bounds
    start, end = dates
    return (max(start, lo) if lo else start, min(end, hi) if hi else end)
