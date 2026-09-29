"""`Filters`: the one filter object shared by CLI, core queries and dashboard.

Frozen + tuples -> hashable -> works with st.cache_data. Values are never
string-formatted into SQL; `where_sql` returns `?` placeholders + params.
"""

import re
from dataclasses import dataclass, fields
from datetime import date
from typing import Literal

from casarecon.core.errors import BadFilter

COUNTRIES = ("MX", "CO", "AR", "CL")
PSPS = ("PSP_A", "PSP_B", "PSP_C", "PSP_D", "PSP_E")
TIERS = ("10-50", "50-200", "200+")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
CATEGORIES = ("exact", "rounding", "fx_tolerance", "meaningful", "large")
CAUSES = ("fx_timing", "psp_rounding", "partial_capture", "psp_fee", "tax_recalc",
          "fraud_hold", "psp_adjustment", "tip", "unexplained")
XB = ("all", "cross", "domestic")
WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")

# field -> (allowed values, fct column)
_IN_FIELDS: dict[str, tuple[tuple[str, ...], str]] = {
    "country": (COUNTRIES, "country"),
    "psp": (PSPS, "psp"),
    "tier": (TIERS, "amount_tier"),
    "weekday": (WEEKDAYS, "auth_weekday"),
    "category": (CATEGORIES, "category"),
    "cause": (CAUSES, "likely_cause"),
}


@dataclass(frozen=True)
class Filters:
    country: tuple[str, ...] = ()
    psp: tuple[str, ...] = ()
    tier: tuple[str, ...] = ()
    xb: Literal["all", "cross", "domestic"] = "all"
    weekday: tuple[str, ...] = ()
    category: tuple[str, ...] = ()
    cause: tuple[str, ...] = ()
    week: str | None = None
    date_from: date | None = None
    date_to: date | None = None

    def validate(self) -> None:
        """Raise BadFilter on the first unknown value."""
        for name, (allowed, _) in _IN_FIELDS.items():
            bad = [v for v in getattr(self, name) if v not in allowed]
            if bad:
                raise BadFilter(f"unknown {name}: {', '.join(bad)} (allowed: {', '.join(allowed)})")
        if self.xb not in XB:
            raise BadFilter(f"unknown xb: {self.xb}")
        if self.week is not None and not WEEK_RE.match(self.week):
            raise BadFilter(f"bad week: {self.week} (expected YYYY-Www)")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise BadFilter("date_from is after date_to")

    def where_sql(self) -> tuple[str, list]:
        """(' and country in (?, ?) ...', params). Empty filters -> ('', [])."""
        self.validate()
        return where_sql(self)


def where_sql(f: Filters) -> tuple[str, list]:
    """Pure SQL fragment builder for a validated Filters."""
    parts: list[str] = []
    params: list = []
    for name, (_, column) in _IN_FIELDS.items():
        values = getattr(f, name)
        if values:
            parts.append(f"{column} in ({', '.join('?' for _ in values)})")
            params.extend(values)
    if f.xb != "all":
        parts.append("is_cross_border = ?")
        params.append(f.xb == "cross")
    if f.week:
        parts.append("auth_week = ?")
        params.append(f.week)
    if f.date_from:
        parts.append("auth_date >= ?")
        params.append(f.date_from)
    if f.date_to:
        parts.append("auth_date <= ?")
        params.append(f.date_to)
    return "".join(f" and {p}" for p in parts), params


def filters_or_empty(f: "Filters | None") -> Filters:
    return f if f is not None else Filters()


FILTER_FIELDS: tuple[str, ...] = tuple(fl.name for fl in fields(Filters))
