"""Pure pipeline: config dicts in, DataFrames out. One RNG, fixed call order → same bytes per seed."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from casarecon.generate import draw, fx, patterns, rows, settle, truth

FX_EXTRA_DAYS = 15


@dataclass(frozen=True)
class Dataset:
    transactions: pd.DataFrame   # all columns (raw contract + helpers); the writer keeps the contract
    fx_rates: pd.DataFrame
    labels: pd.DataFrame
    manifest: dict


def build(g: dict, t: dict) -> Dataset:
    """g = generator.yaml (rows/seed already overridden), t = thresholds.yaml."""
    rng = np.random.default_rng(g["seed"])
    start, end = draw.window(g["start"], g["months"])
    fx_table = fx.fx_rates_daily(rng, g, start.date(), (end - start).days + 1 + FX_EXTRA_DAYS)
    df = rows.base_rows(rng, g, start, end)
    df = settle.add_authorized(df, fx_table)
    df = settle.apply_p2(rng, df, g)
    df = settle.apply_status(df, end)
    df = settle.add_expected(df, fx_table)
    df = patterns.features(df, g, start.date())
    df = patterns.plant(rng, df, g, t)
    df = df.sort_values("transaction_id", kind="stable").reset_index(drop=True)
    manifest = {
        "seed": g["seed"],
        "rows": g["rows"],
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "fx_days": len(fx_table) // len(g["fx_base"]),
        "fx_max_15d_move_pct": round(fx.max_move_pct(fx_table), 4),
        "realized": truth.mix(df),
    }
    return Dataset(df, fx_table, truth.labels(df, g), manifest)

