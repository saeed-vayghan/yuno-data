"""Money and timing of each row: authorized amount, P2 lag, as-of status, expected settled."""

from datetime import datetime

import numpy as np
import pandas as pd

from casarecon.core import money
from casarecon.generate import fx as fxmod


def exponents(currency: np.ndarray) -> np.ndarray:
    return np.array([money.exponent(c) for c in currency], dtype=np.int64)


def add_authorized(df: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """authorized = round_half_up(amount_usd × fx_auth × 10^exp); amount_usd recomputed like dbt."""
    exp = exponents(df["currency"].to_numpy())
    fx_auth = fxmod.lookup(fx, df["currency"].to_numpy(), df["auth_ts"])
    auth = np.floor(df["amount_usd_drawn"].to_numpy() * fx_auth * 10.0**exp + 0.5).astype(np.int64)
    return df.assign(exponent=exp, fx_auth=fx_auth, authorized_amount=auth,
                     amount_usd=auth / 10.0**exp / fx_auth)


def apply_p2(rng: np.random.Generator, df: pd.DataFrame, g: dict) -> pd.DataFrame:
    """P2: CO orders over min_usd settle later (+U(extra) days) and have more lag outliers."""
    p2 = g["patterns"]["P2"]
    hit = (df["country"] == p2["country"]).to_numpy() & (df["amount_usd"].to_numpy() > p2["min_usd"])
    n = len(df)
    outlier = hit & (rng.random(n) < p2["outlier_share"])
    lag = np.where(outlier, rng.uniform(*g["lag_days"]["outlier_range"], n), df["lag_days"].to_numpy())
    lag = np.where(hit, lag + rng.uniform(*p2["extra_lag_days"], n), lag)
    return df.assign(lag_days=np.minimum(lag, g["lag_cap_days"]), is_p2=hit)


def apply_status(df: pd.DataFrame, end: datetime) -> pd.DataFrame:
    """Failed: no settlement. As-of rule: settle after window end → pending. Else settled."""
    settle = df["auth_ts"] + pd.to_timedelta(np.round(df["lag_days"].to_numpy() * 86400), unit="s")
    late = (settle > pd.Timestamp(end)).to_numpy()
    failed = df["is_failed"].to_numpy()
    status = np.select([failed, late], ["failed", "pending"], "settled").astype(object)
    return df.assign(status=status, settle_ts=settle.where(status == "settled"))


def add_expected(df: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """fx_settle + expected_settled (core.money, same formula as dbt); 0 / NaN on unsettled rows."""
    fx_settle = fxmod.lookup(fx, df["currency"].to_numpy(), df["settle_ts"])
    settled = (df["status"] == "settled").to_numpy()
    expected = [
        money.expected_settled(a, fa, fs, xb) if ok else 0
        for a, fa, fs, xb, ok in zip(df["authorized_amount"], df["fx_auth"], fx_settle,
                                     df["is_cross_border"], settled)
    ]
    exp_minor = np.array(expected, dtype=np.int64)
    return df.assign(fx_settle=fx_settle, expected=exp_minor,
                     expected_usd=exp_minor / 10.0 ** df["exponent"].to_numpy() / df["fx_auth"].to_numpy())
