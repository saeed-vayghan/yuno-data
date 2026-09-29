"""Money helpers shared by generator, analysis and UI formatters. Pure functions.

Local amounts are int minor units; never hard-code /100 (CLP has 0 decimals).
"""

import csv
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path

from casarecon.core import paths


@cache
def _exponents(seed_file: Path) -> dict[str, int]:
    with seed_file.open(newline="") as f:
        return {row["currency"]: int(row["exponent"]) for row in csv.DictReader(f)}


def exponent(currency: str) -> int:
    """Minor-unit exponent from dbt/seeds/currency_exponents.csv (CLP 0, others 2)."""
    table = _exponents(paths.SEEDS_DIR / "currency_exponents.csv")
    if currency not in table:
        raise ValueError(f"unknown currency: {currency}")
    return table[currency]


def to_major(amount_minor: int, currency: str) -> Decimal:
    """12345 MXN -> Decimal('123.45'); 12345 CLP -> Decimal('12345')."""
    return Decimal(int(amount_minor)).scaleb(-exponent(currency))


def to_minor(amount_major: float, currency: str) -> int:
    """Major units -> int minor units, rounded half away from zero."""
    return round_half_up(amount_major * 10 ** exponent(currency))


def round_half_up(x: float) -> int:
    """Round half away from zero (matches DuckDB round()); Python round() is banker's."""
    return int(Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def expected_settled(auth_minor: int, fx_auth: float, fx_settle: float, cross_border: bool) -> int:
    """Expected settled minor units. Cross-border: auth * fx_settle / fx_auth; domestic: auth."""
    if not cross_border:
        return int(auth_minor)
    return round_half_up(auth_minor * fx_settle / fx_auth)


def to_usd(amount_minor: int, currency: str, local_per_usd: float) -> float:
    """Local minor units -> USD (float, 2 dp) at a local-per-USD rate."""
    return round(float(to_major(amount_minor, currency)) / local_per_usd, 2)
