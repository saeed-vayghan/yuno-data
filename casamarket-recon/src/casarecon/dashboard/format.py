"""Pure display formatters. Numbers stay numeric in tables; these are for text only.

Minus sign is U+2212. Local money always carries its ISO code, never a bare "$".
"""

from datetime import date

MINUS = "−"


def _signed(text: str, x: float) -> str:
    return f"{MINUS}{text}" if x < 0 else f"+{text}"


def usd(x: float) -> str:
    """1234.564 -> '$1,234.56'; -62.1 -> '−$62.10'."""
    return f"{MINUS if x < 0 else ''}${abs(x):,.2f}"


def usd_compact(x: float) -> str:
    """127400 -> '$127.4k'; 2.5e6 -> '$2.5M'; 980 -> '$980'."""
    a, sign = abs(x), MINUS if x < 0 else ""
    if a >= 1e6:
        return f"{sign}${a / 1e6:,.1f}M"
    if a >= 1e3:
        return f"{sign}${a / 1e3:,.1f}k"
    return f"{sign}${a:,.0f}"


def usd_signed(x: float) -> str:
    """-62.1 -> '−$62.10 under'; 4 -> '+$4.00 over'; 0 -> '$0.00'."""
    if x == 0:
        return "$0.00"
    return _signed(f"${abs(x):,.2f}", x) + (" under" if x < 0 else " over")


def local(minor: int, currency: str, exponent: int) -> str:
    """(1234567, 'MXN', 2) -> 'MXN 12,345.67'; (-58000, 'CLP', 0) -> 'CLP −58,000'."""
    major = abs(int(minor)) / 10**exponent
    sign = MINUS if minor < 0 else ""
    return f"{currency} {sign}{major:,.{exponent}f}"


def rate(p: float) -> str:
    """0.142 -> '14.2%' (rates are fractions 0-1)."""
    return f"{p * 100:.1f}%"


def delta_pts(d: float) -> str:
    """1.1 -> '▲ +1.1 pts' (worse); -0.4 -> '▼ −0.4 pts' (better); 0 -> '■ 0.0 pts'."""
    if round(d, 1) == 0:
        return "■ 0.0 pts"
    return ("▲ " if d > 0 else "▼ ") + _signed(f"{abs(d):.1f}", d) + " pts"


def delta_usd(d: float) -> str:
    """1200 -> '▲ +$1,200'; -300 -> '▼ −$300'."""
    if round(d) == 0:
        return "■ $0"
    return ("▲ " if d > 0 else "▼ ") + _signed(f"${abs(d):,.0f}", d)


def delta_int(d: int) -> str:
    """-8 -> '▼ −8'; 3 -> '▲ +3'."""
    if d == 0:
        return "■ 0"
    return ("▲ " if d > 0 else "▼ ") + _signed(f"{abs(int(d)):,}", d)


def count(n: int) -> str:
    return f"{int(n):,}"


def pct_signed(x: float) -> str:
    """-5.46 -> '−5.5%' (x already in percent, like residual_pct)."""
    return _signed(f"{abs(x):.1f}%", x)


def rate_range(p: float, lo: float, hi: float) -> str:
    """(0.213, 0.198, 0.229) -> '21.3% [19.8–22.9]'."""
    return f"{rate(p)} [{lo * 100:.1f}–{hi * 100:.1f}]"


def short_day(d: date) -> str:
    return f"{d:%b} {d.day}"


def day_range(start: date, end: date) -> str:
    """Jun 15 – Jun 21 -> 'Jun 15–21'; May 29 – Jun 4 -> 'May 29–Jun 4'."""
    if start.month == end.month:
        return f"{short_day(start)}–{end.day}"
    return f"{short_day(start)}–{short_day(end)}"


def week_label(iso: str, start: date, end: date) -> str:
    """('2026-W25', Jun 15, Jun 21) -> 'W25 (Jun 15–21)'."""
    return f"{iso.split('-')[-1]} ({day_range(start, end)})"


def month_label(month: str) -> str:
    """'2026-06' -> 'Jun 2026'; 'last' -> 'Last full month'."""
    if month == "last":
        return "Last full month"
    y, m = month.split("-")
    return f"{date(int(y), int(m), 1):%b} {y}"
