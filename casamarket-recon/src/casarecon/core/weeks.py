"""Calendar rules (pure). ISO weeks by auth date; a week belongs to the month of its Thursday.

"As of" is the latest timestamp in the data, never the wall clock.
"""

import calendar
import re
from datetime import date, datetime, timedelta

from casarecon.core.errors import BadFilter

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
CLOSE_DAYS = 7  # a week is closed once its Sunday is at least 7 days before as_of


def iso_week(d: date) -> str:
    """date(2026, 6, 15) -> '2026-W25'."""
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(d: date) -> tuple[date, date]:
    """(Monday, Sunday) of the ISO week holding `d`."""
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def last_closed_end(as_of: datetime) -> date:
    """Latest Sunday <= as_of - 7 days: the end of the last closed week."""
    d = (as_of - timedelta(days=CLOSE_DAYS)).date()
    return d - timedelta(days=d.isoweekday() % 7)


def last_full_month(as_of: datetime, first_day: date) -> str | None:
    """Latest calendar month fully inside [first_day, as_of] ('2026-06'), or None."""
    y, m = as_of.year, as_of.month
    if as_of.date() < date(y, m, calendar.monthrange(y, m)[1]):
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return f"{y}-{m:02d}" if date(y, m, 1) >= first_day else None


def check_month(month: str) -> str:
    """Validate 'YYYY-MM' or raise BadFilter."""
    if not MONTH_RE.match(month):
        raise BadFilter(f"bad month: {month} (expected 'last' or YYYY-MM)")
    return month
