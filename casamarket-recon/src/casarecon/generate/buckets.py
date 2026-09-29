"""Bucket allocation for settled non-P4 rows: hit the target counts, respecting what each row can be."""

import numpy as np
import pandas as pd

from casarecon.generate import draw

MARGIN_PCT = 0.1   # keep drawn percentages this far inside the bucket limits
MARGIN_USD = 0.5   # and dollar amounts this far from large_usd


def pct_bounds(g: dict) -> tuple[float, float]:
    lo, hi = g["patterns"]["X6"]["pct_range"]
    return lo + MARGIN_PCT, hi - MARGIN_PCT


def eligible(s: pd.DataFrame, g: dict, t: dict) -> dict[str, np.ndarray]:
    """Which buckets each row can land in, given the causes that fit it (file 03 step 4)."""
    lo, hi = pct_bounds(g)
    usd = s["expected_usd"].to_numpy()
    domestic = ~s["is_cross_border"].to_numpy()
    x3, fee_pct = s["x3_active"].to_numpy(), s["fee_pct"].to_numpy()
    x4 = domestic & s["country"].isin(g["patterns"]["X4"]["countries"]).to_numpy()
    x5 = (s["risk_score"].to_numpy() >= g["patterns"]["X5"]["min_risk"]) & (s["item_count"].to_numpy() == 1)
    return {
        "exact": domestic,
        "rounding": domestic,
        "fx_tolerance": ~domestic | x4 | fx_fee_fits(s, t),
        "meaningful": (usd * lo / 100 < t["large_usd"] - MARGIN_USD) | (x3 & (fee_pct >= lo) & (fee_pct <= hi)),
        "large": (s["item_count"].to_numpy() >= 2) | x5 | (usd * hi / 100 >= t["large_usd"] + MARGIN_USD),
    }


def fx_fee_fits(s: pd.DataFrame, t: dict) -> np.ndarray:
    """X3 fee small enough to stay inside fx_tolerance (and > 1 minor unit, trivially)."""
    return s["x3_active"].to_numpy() & (s["fee_pct"].to_numpy() <= t["fx_tolerance_pct"] - MARGIN_PCT)


def weekend_weights(s: pd.DataFrame, g: dict) -> np.ndarray:
    """P3: weekend rows weigh × ratio (on meaningful and large, so the flag-rate ratio shows it)."""
    return np.where(s["is_weekend"].to_numpy(), g["patterns"]["P3"]["weekend_meaningful_ratio"], 1.0)


def large_weights(s: pd.DataFrame, g: dict) -> np.ndarray:
    """P3 × X5 weight: high-risk single-item orders are the likely fraud holds."""
    x5 = g["patterns"]["X5"]
    risky = (s["risk_score"].to_numpy() >= x5["min_risk"]) & (s["item_count"].to_numpy() == 1)
    return weekend_weights(s, g) * np.where(risky, x5["large_weight"], 1.0)


def boosts(s: pd.DataFrame, g: dict) -> list[tuple[np.ndarray, float]]:
    """(segment mask, extra meaningful points): P1 PSP_B × AR, and the X3 drift (PSP_C in month 3)."""
    pat = g["patterns"]
    p1 = (s["psp"] == pat["P1"]["psp"]).to_numpy() & (s["country"] == pat["P1"]["country"]).to_numpy()
    return [(p1, pat["P1"]["meaningful_boost_pts"]), (s["x3_active"].to_numpy(), pat["X3"]["meaningful_boost_pts"])]


def allocate(rng: np.random.Generator, s: pd.DataFrame, g: dict, t: dict, target: dict) -> np.ndarray:
    """large → meaningful → rounding → fx_tolerance (all leftover cross-border first) → exact."""
    ok = eligible(s, g, t)
    out = np.full(len(s), "", dtype=object)
    free = np.ones(len(s), dtype=bool)

    def take(bucket: str, weights: np.ndarray, k: int) -> None:
        idx = draw.weighted_pick(rng, np.where(free & ok[bucket], weights, 0.0), k)
        out[idx], free[idx] = bucket, False

    ones = np.ones(len(s))
    take("large", large_weights(s, g), target["large"])
    week, extra = weekend_weights(s, g), 0
    for mask, pts in boosts(s, g):  # boosted segments first get pts% of their rows as meaningful
        k = round(pts / 100 * (mask & free & ok["meaningful"]).sum())
        take("meaningful", week * mask, k)
        extra += k
    take("meaningful", week, target["meaningful"] - extra)
    take("rounding", ones, target["rounding"])
    cross = s["is_cross_border"].to_numpy()
    n_cross = int((free & cross).sum())
    take("fx_tolerance", np.where(cross, 1.0, 0.0), n_cross)
    x3_weight = np.where(fx_fee_fits(s, t), 10.0, 1.0)  # the PSP_C fee shows up as a cluster
    take("fx_tolerance", x3_weight, target["fx_tolerance"] - n_cross)
    out[free] = "exact"
    return out


def targets(n_settled: int, shares: dict, already: dict) -> dict[str, int]:
    """Counts per bucket so the TOTAL (incl. P4 rows already placed) hits the shares."""
    return {b: max(0, round(shares[b] * n_settled) - already.get(b, 0)) for b in shares}
