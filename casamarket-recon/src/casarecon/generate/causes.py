"""Cause per bucket (must fit the row) and the settled amount it produces (file 03 steps 4–6)."""

import numpy as np
import pandas as pd

from casarecon.generate.buckets import MARGIN_PCT, MARGIN_USD, fx_fee_fits, pct_bounds

LABELS = {  # planted cause -> truth label (= dbt likely_cause names)
    "rounding": "psp_rounding", "P4": "psp_rounding", "X1": "fx_timing", "X2": "partial_capture",
    "X3": "psp_fee", "X4": "tax_recalc", "X5": "fraud_hold", "X6": "psp_adjustment",
}
X2_SHARE_OF_LARGE = 0.7  # when a big multi-item row could be X2 or X6


def pick(rng: np.random.Generator, s: pd.DataFrame, bucket: np.ndarray, g: dict, t: dict) -> np.ndarray:
    """One cause code per row ('' for exact)."""
    lo, hi = pct_bounds(g)
    n = len(s)
    cross = s["is_cross_border"].to_numpy()
    x3m = s["x3_active"].to_numpy() & (s["fee_pct"].to_numpy() >= lo) & (s["fee_pct"].to_numpy() <= hi)
    x5 = (s["risk_score"].to_numpy() >= g["patterns"]["X5"]["min_risk"]) & (s["item_count"].to_numpy() == 1)
    x2 = s["item_count"].to_numpy() >= 2
    x6_big = s["expected_usd"].to_numpy() * hi / 100 >= t["large_usd"] + MARGIN_USD
    large = np.select([x5, x2 & (~x6_big | (rng.random(n) < X2_SHARE_OF_LARGE))], ["X5", "X2"], "X6")
    fx = np.select([fx_fee_fits(s, t), cross], ["X3", "X1"], "X4")
    return np.select(
        [bucket == "rounding", bucket == "fx_tolerance", bucket == "meaningful", bucket == "large"],
        ["rounding", fx, np.where(x3m, "X3", "X6"), large],
        "",
    ).astype(object)


def _pct_delta(rng, expected: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """|delta| in minor units for a percentage drawn in [lo, hi] (hi ≥ lo enforced)."""
    pct = rng.uniform(lo, np.maximum(hi, lo))
    return np.floor(expected * pct / 100 + 0.5).astype(np.int64)


def settled_amounts(rng: np.random.Generator, s: pd.DataFrame, bucket: np.ndarray, cause: np.ndarray,
                    g: dict, t: dict) -> np.ndarray:
    """settled = expected + delta; every cause sized inside its bucket limits."""
    n = len(s)
    lo, hi = pct_bounds(g)
    exp_ = s["expected"].to_numpy()
    usd = s["expected_usd"].to_numpy()
    usd_cap = (t["large_usd"] - MARGIN_USD) / usd * 100          # pct that stays < large_usd
    x4_lo, x4_hi = g["patterns"]["X4"]["pct_range"]
    x4 = np.maximum(_pct_delta(rng, exp_, x4_lo, np.minimum(x4_hi, usd_cap)), 2) * rng.choice([-1, 1], n)
    x6_small = -_pct_delta(rng, exp_, lo, np.minimum(hi, usd_cap))
    x6_big = -_pct_delta(rng, exp_, np.maximum(lo, (t["large_usd"] + MARGIN_USD) / usd * 100), hi)
    w_lo, w_hi = g["patterns"]["X5"]["withheld_pct"]
    x5 = -_pct_delta(rng, exp_, w_lo + MARGIN_PCT * 5, w_hi - MARGIN_PCT * 5)
    items = s["item_count"].to_numpy()
    x2 = np.floor(exp_ * (items - 1) / items + 0.5).astype(np.int64) - exp_
    rounding = s["authorized_amount"].to_numpy() + rng.choice([-1, 1], n) - exp_   # domestic: exp = auth
    delta = np.select(
        [cause == "rounding", cause == "X1", cause == "X3", cause == "X4", cause == "X2", cause == "X5",
         (cause == "X6") & (bucket == "large"), cause == "X6"],
        [rounding, 0, -s["fee_minor"].to_numpy(), x4, x2, x5, x6_big, x6_small],
        0,
    )
    return exp_ + delta
