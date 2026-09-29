"""Planted patterns on settled rows, in the file-03 order: P4 first, buckets, causes, sizes."""

from datetime import date

import numpy as np
import pandas as pd

from casarecon.generate import buckets, causes
from casarecon.generate.classify import category


def features(df: pd.DataFrame, g: dict, start: date) -> pd.DataFrame:
    """Helper columns the pattern rules read: weekend, month index, X3 fee and its size."""
    x3 = g["patterns"]["X3"]
    ts = df["auth_ts"]
    month_idx = (ts.dt.year - start.year) * 12 + ts.dt.month - start.month + 1
    fee = df["currency"].map(x3["fee_local"]).fillna(0).astype(np.int64).to_numpy()
    expected = df["expected"].to_numpy()
    return df.assign(
        is_weekend=(ts.dt.dayofweek >= 5).to_numpy(),
        x3_active=((df["psp"] == x3["psp"]) & month_idx.isin(x3["months"])).to_numpy(),
        fee_minor=fee,
        fee_pct=np.where(expected > 0, 100.0 * fee / np.maximum(expected, 1), np.inf),
    )


def p4_mask(df: pd.DataFrame, g: dict) -> np.ndarray:
    p4 = g["patterns"]["P4"]
    return ((df["status"] == "settled") & (df["psp"] == p4["psp"]) & df["currency"].isin(p4["currencies"])
            & (df["is_cross_border"] if p4["cross_border_only"] else True)).to_numpy()


def p4_settled(df: pd.DataFrame, g: dict) -> np.ndarray:
    """settled = floor(expected / step) × step, step = step_major × 10^exp minor units."""
    step = g["patterns"]["P4"]["step_major"] * 10 ** df["exponent"].to_numpy()
    return (df["expected"].to_numpy() // step) * step


def _classify(s: pd.DataFrame, settled: np.ndarray, t: dict) -> np.ndarray:
    return category(s["authorized_amount"].to_numpy(), settled, s["expected"].to_numpy(),
                    s["exponent"].to_numpy(), s["fx_auth"].to_numpy(), t)


def plant(rng: np.random.Generator, df: pd.DataFrame, g: dict, t: dict) -> pd.DataFrame:
    """Adds settled_amount, planned_bucket, cause, bucket (= dbt category) on settled rows."""
    settled_rows = (df["status"] == "settled").to_numpy()
    is_p4 = p4_mask(df, g)
    p4 = df[is_p4]
    p4_amount = p4_settled(p4, g)
    p4_bucket = _classify(p4, p4_amount, t)

    rest = df[settled_rows & ~is_p4]
    already = pd.Series(p4_bucket).value_counts().to_dict()
    target = buckets.targets(int(settled_rows.sum()), g["buckets"], already)
    planned = buckets.allocate(rng, rest, g, t, target)
    cause = causes.pick(rng, rest, planned, g, t)
    amount = causes.settled_amounts(rng, rest, planned, cause, g, t)

    n = len(df)
    amount_all, planned_all = np.zeros(n, dtype=np.int64), np.full(n, None, dtype=object)
    cause_all, bucket_all = planned_all.copy(), planned_all.copy()
    for pos, a, p, c, b in ((np.flatnonzero(is_p4), p4_amount, p4_bucket, "P4", p4_bucket),
                            (np.flatnonzero(settled_rows & ~is_p4), amount, planned, cause,
                             _classify(rest, amount, t))):
        amount_all[pos], planned_all[pos], cause_all[pos], bucket_all[pos] = a, p, c, b
    settled_amount = pd.Series(amount_all, dtype="Int64").where(settled_rows)
    return df.assign(settled_amount=settled_amount, planned_bucket=planned_all, cause=cause_all,
                     bucket=bucket_all, is_p4=is_p4)
