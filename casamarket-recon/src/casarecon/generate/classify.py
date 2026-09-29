"""The dbt category rule (file 04, fct_transaction_discrepancy) in numpy, so truth = what SQL sees."""

import numpy as np

from casarecon.generate.draw import half_away

BUCKETS = ("exact", "rounding", "fx_tolerance", "meaningful", "large")


def category(auth, settled, expected, exponent, fx_auth, t: dict) -> np.ndarray:
    """First match wins: exact, rounding, fx_tolerance, meaningful, else large (settled rows only).

    `t` = thresholds (rounding_minor_units, fx_tolerance_pct, large_pct, large_usd).
    """
    diff_local = settled - auth
    residual = settled - expected
    pct = np.abs(half_away(100.0 * residual / expected, 4))
    usd = np.abs(half_away(residual / 10.0**exponent / fx_auth, 2))
    small_usd = usd < t["large_usd"]
    return np.select(
        [
            diff_local == 0,
            np.abs(diff_local) <= t["rounding_minor_units"],
            (pct <= t["fx_tolerance_pct"]) & small_usd,
            (pct <= t["large_pct"]) & small_usd,
        ],
        list(BUCKETS[:4]),
        BUCKETS[4],
    ).astype(object)
