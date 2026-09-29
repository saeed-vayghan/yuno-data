"""Truth labels (kept apart from data/raw) and the realized mix for the manifest."""

import numpy as np
import pandas as pd

from casarecon.generate.causes import LABELS
from casarecon.generate.classify import BUCKETS


def pattern_ids(df: pd.DataFrame, g: dict) -> np.ndarray:
    """';'-joined planted pattern ids per row, e.g. 'P1;X6' ('' when none)."""
    pat = g["patterns"]
    meaningful = (df["bucket"] == "meaningful").to_numpy()
    p1 = (df["psp"] == pat["P1"]["psp"]).to_numpy() & (df["country"] == pat["P1"]["country"]).to_numpy()
    tags = {
        "P1": p1 & meaningful,
        "P2": df["is_p2"].to_numpy(),
        "P3": df["is_weekend"].to_numpy() & meaningful,
        "P4": df["is_p4"].to_numpy(),
    }
    cause = df["cause"].fillna("").to_numpy()
    parts = [np.where(mask, name, "") for name, mask in tags.items()]
    parts.append(np.where(np.char.startswith(cause.astype(str), "X"), cause, ""))
    return np.array([";".join(p for p in row if p) for row in zip(*parts)], dtype=object)


def labels(df: pd.DataFrame, g: dict) -> pd.DataFrame:
    """transaction_id, true_bucket, true_cause, pattern_ids — sorted by transaction_id."""
    cause = df["cause"].map(LABELS)  # exact / unsettled rows -> NaN
    out = pd.DataFrame({
        "transaction_id": df["transaction_id"],
        "true_bucket": df["bucket"],
        "true_cause": cause.where(df["bucket"] != "exact"),
        "pattern_ids": pattern_ids(df, g),
    })
    return out.sort_values("transaction_id", kind="stable").reset_index(drop=True)


def mix(df: pd.DataFrame) -> dict:
    """Realized shares (4 dp): status over all rows, buckets and causes over settled rows."""
    settled = df[df["status"] == "settled"]
    buckets = settled["bucket"].value_counts(normalize=True)
    return {
        "status": df["status"].value_counts(normalize=True).round(4).sort_index().to_dict(),
        "buckets": {b: round(float(buckets.get(b, 0.0)), 4) for b in BUCKETS},
        "causes": settled["cause"].replace("", "none").value_counts(normalize=True).round(4)
                                  .sort_index().to_dict(),
        "planned_vs_realized_mismatch": int((settled["planned_bucket"] != settled["bucket"]).sum()),
    }
