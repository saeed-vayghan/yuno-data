"""Base rows: who, where, when, how much, how long to settle. No discrepancies yet."""

from datetime import datetime

import numpy as np
import pandas as pd

from casarecon.generate import draw


def amounts_usd(rng: np.random.Generator, g: dict, n: int) -> np.ndarray:
    """Tier first, then an amount inside the tier (log-uniform; 200+ has an exponential tail)."""
    tier = draw.categorical(rng, g["tiers_usd"], n)
    small = np.exp(rng.uniform(np.log(10), np.log(50), n))
    mid = np.exp(rng.uniform(np.log(50), np.log(200), n))
    big = np.minimum(200 * np.exp(rng.exponential(g["amount_usd"]["over_200_scale"], n)), g["amount_usd"]["max"])
    return np.round(np.select([tier == "10-50", tier == "50-200"], [small, mid], big), 2)


def lags_days(rng: np.random.Generator, spec: dict, n: int) -> np.ndarray:
    """Triangular(min, mode, max) days, with a share of outliers drawn from outlier_range."""
    base = rng.triangular(spec["min"], spec["mode"], spec["max"], n)
    outlier = rng.random(n) < spec["outlier_share"]
    return np.where(outlier, rng.uniform(*spec["outlier_range"], n), base)


def auth_times(rng: np.random.Generator, start: datetime, end: datetime, n: int) -> pd.Series:
    """Uniform over the window, whole seconds, merchant local time (naive)."""
    secs = rng.integers(0, int((end - start).total_seconds()) + 1, n)
    return pd.Series(pd.Timestamp(start) + pd.to_timedelta(secs, unit="s"))


def base_rows(rng: np.random.Generator, g: dict, start: datetime, end: datetime) -> pd.DataFrame:
    """One row per transaction with every raw attribute except settlement outcome."""
    n = g["rows"]
    country = draw.categorical(rng, g["countries"], n)
    cross = rng.random(n) < g["cross_border_share"]
    currency = np.array([g["currency"][c] for c in country], dtype=object)
    pool = draw.hex_tokens(rng, "cus_", max(1, int(n * g["customers_per_row"])))
    return pd.DataFrame({
        "transaction_id": draw.hex_tokens(rng, "txn_", n),
        "customer_id": pool[rng.integers(0, len(pool), n)],
        "product_category": draw.categorical(rng, g["product_category"], n),
        "country": country,
        "currency": currency,
        "payer_currency": np.where(cross, "USD", currency),
        "is_cross_border": cross,
        "psp": draw.categorical(rng, g["psps"], n),
        "auth_ts": auth_times(rng, start, end, n),
        "item_count": draw.categorical(rng, g["item_count"], n).astype(int),
        "risk_score": np.round(rng.beta(*g["risk_beta"], n), 3),
        "card_bin_country": np.where(cross, draw.categorical(rng, g["foreign_bin"], n), country),
        "amount_usd_drawn": amounts_usd(rng, g, n),
        "lag_days": lags_days(rng, g["lag_days"], n),
        "is_failed": rng.random(n) < g["status"]["failed"],
    })
