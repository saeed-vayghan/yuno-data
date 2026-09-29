"""Validation checks (pure): metrics dict -> list[Check]. Brief ranges from the scenario's test-data spec."""

import math
from dataclasses import asdict, dataclass
from typing import Literal

Status = Literal["PASS", "WARN", "FAIL"]
COUNTRIES, CURRENCIES = ["AR", "CL", "CO", "MX"], ["ARS", "CLP", "COP", "MXN"]
# brief tier -> (metric key, low, high) as shares
BUCKETS = {"match exactly (exact+rounding)": ("k_match", 0.60, 0.70),
           "small 0.1-2% (fx_tolerance)": ("k_small", 0.15, 0.20),
           "meaningful > 2% (meaningful+large)": ("k_meaningful", 0.10, 0.18),
           "large > 5% or >= $20": ("k_large", 0.03, 0.05)}


@dataclass(frozen=True)
class Check:
    name: str
    target: str
    realized: float
    low: float
    high: float
    status: Status


def _check(name: str, target: str, value: float, low: float, high: float, soft: bool = False) -> Check:
    ok = value is not None and not math.isnan(value) and low <= value <= high
    return Check(name, target, round(float(value if value is not None else math.nan), 4), low, high,
                 "PASS" if ok else ("WARN" if soft else "FAIL"))


def bucket_checks(m: dict) -> list[Check]:
    """Brief bucket shares on settled and on all rows, bounds widened by 3 standard errors."""
    out = []
    for denom in ("settled", "rows"):
        n = m[denom]
        for name, (key, lo, hi) in BUCKETS.items():
            p = m[key] / n if n else math.nan
            se = math.sqrt(p * (1 - p) / n) if n else 0.0
            out.append(_check(f"{name} / {denom}", f"{lo:.0%}-{hi:.0%}", p,
                              round(lo - 3 * se, 4), round(hi + 3 * se, 4)))
    return out


def evaluate(m: dict, full: bool) -> list[Check]:
    """Brief spec + bucket shares are hard. Pattern bands are hard on a full run, WARN on a smoke run."""
    soft = not full
    return [
        _check("rows", ">= 500", m["rows"], 500, math.inf),
        _check("months", "3-4", m["months"], 3, 4),
        _check("countries", "MX CO AR CL", float(m["countries"] == COUNTRIES), 1, 1),
        _check("currencies", "MXN COP ARS CLP", float(m["currencies"] == CURRENCIES), 1, 1),
        _check("psps", "3-5", m["psps"], 3, 5),
        _check("failed rows", "> 0", m["failed"], 1, math.inf),
        _check("pending rows", "> 0", m["pending"], 1, math.inf),
        _check("settled share", "> 50%", m["settled"] / m["rows"], 0.5, 1),
        _check("median settle lag (days)", "1-7", m["median_lag"], 1, 7),
        _check("lag outliers (> 7 d)", "> 0", m["lag_outliers"], 1, math.inf),
        _check("null metadata rows", "0", m["null_metadata"], 0, 0),
        *bucket_checks(m),
        _check("P1 PSP_B x AR flag-rate gap (pts)", ">= 2.5", 100 * m["p1_gap"], 2.5, math.inf, soft),
        _check("P2 CO > $300 median lag gap (days)", ">= 2", m["p2_gap_days"], 2, math.inf, soft),
        _check("P3 weekend / weekday flag rate", ">= 1.2", m["p3_ratio"], 1.2, math.inf, soft),
        _check("P4 PSP_D x-border CLP/COP rounding share", ">= 90%", m["p4_share"], 0.9, 1, soft),
    ]


def overall(checks: list[Check]) -> Status:
    statuses = {c.status for c in checks}
    return "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"


def as_rows(checks: list[Check]) -> list[dict]:
    return [asdict(c) for c in checks]
