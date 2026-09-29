"""Daily FX table (local per USD): capped random walk per currency, every calendar day."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

MIN_DAILY_STEP = 0.0002  # every day moves, so cross-border rows are almost never `exact`


def _walk(rng: np.random.Generator, base: float, days: int, max_step: float, drift: float) -> list[float]:
    """Log random walk; |daily step| ≤ max_step, so any 15-day move < 15 · max_step."""
    sign = rng.choice([-1.0, 1.0], size=days - 1)
    steps = np.clip(drift + sign * rng.uniform(MIN_DAILY_STEP, max_step, size=days - 1), -max_step, max_step)
    levels = base * np.exp(np.concatenate([[0.0], np.cumsum(steps)]))
    return [float(f"{v:.6f}") for v in levels]  # 6 dp, parsed exactly like DuckDB will


def fx_rates_daily(rng: np.random.Generator, g: dict, start: date, days: int) -> pd.DataFrame:
    """`rate_date, currency, local_per_usd` for `days` days from `start`, sorted by date, currency."""
    dates = [start + timedelta(days=i) for i in range(days)]
    drift = g.get("fx_drift_daily", {})
    frames = [
        pd.DataFrame({
            "rate_date": dates,
            "currency": cur,
            "local_per_usd": _walk(rng, base, days, g["fx_max_daily_step"], drift.get(cur, 0.0)),
        })
        for cur, base in g["fx_base"].items()
    ]
    return pd.concat(frames).sort_values(["rate_date", "currency"], kind="stable").reset_index(drop=True)


def lookup(fx: pd.DataFrame, currency: np.ndarray, ts: pd.Series) -> np.ndarray:
    """Rate for each (currency, ts.date); NaN where ts is missing."""
    table = fx.set_index(["currency", "rate_date"])["local_per_usd"]
    keys = pd.MultiIndex.from_arrays([currency, ts.dt.date])
    return table.reindex(keys).to_numpy(dtype=float)


def max_move_pct(fx: pd.DataFrame, horizon_days: int = 15) -> float:
    """Largest |rate(d + k) / rate(d) − 1| · 100 over k ≤ horizon_days (for tests)."""
    worst = 0.0
    for _, grp in fx.groupby("currency"):
        r = grp["local_per_usd"].to_numpy()
        for k in range(1, horizon_days + 1):
            worst = max(worst, float(np.abs(r[k:] / r[:-k] - 1).max()) * 100)
    return worst
