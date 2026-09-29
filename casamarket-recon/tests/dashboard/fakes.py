"""Fake core results shaped exactly like the CORE API CONTRACT (no DB needed)."""

from datetime import date, datetime

import pandas as pd

STATUS = {"as_of": datetime(2026, 6, 30, 23, 0), "last_closed_week": "2026-W25",
          "last_closed_start": date(2026, 6, 15), "last_closed_end": date(2026, 6, 21),
          "open_weeks": ["2026-W26", "2026-W27"], "last_full_month": "2026-06",
          "months": ["2026-04", "2026-05", "2026-06"], "n_rows": 500}

OPTIONS = {"country": ["MX", "CO", "AR", "CL"], "psp": ["PSP_A", "PSP_B", "PSP_C", "PSP_D", "PSP_E"],
           "tier": ["10-50", "50-200", "200+"], "weekday": ["Mon", "Tue"],
           "category": ["exact", "large"], "cause": ["fx_timing", "psp_rounding", "unexplained"],
           "weeks": ["2026-W24", "2026-W25"], "months": ["2026-04", "2026-05", "2026-06"],
           "min_date": "2026-04-01", "max_date": "2026-06-30"}

KPIS = {"n": 120, "n_flagged": 17, "n_large": 9, "flag_rate": 0.142, "net_usd": 9840.0,
        "gross_under_usd": 10100.0, "prev_week": "2026-W24", "delta_rate_pts": 1.1,
        "delta_net_usd": 1200.0, "delta_n_large": -8}


def worst_week(month: str = "last") -> pd.DataFrame:
    return pd.DataFrame({
        "rank": [1, 2, 3], "psp": ["PSP_B", "PSP_C", "PSP_E"],
        "auth_week": ["2026-W24", "2026-W25", "2026-W26"],
        "week_start": [date(2026, 6, 8), date(2026, 6, 15), date(2026, 6, 22)],
        "week_end": [date(2026, 6, 14), date(2026, 6, 21), date(2026, 6, 28)],
        "n": [812, 640, 12], "n_flagged": [173, 90, 2], "rate": [0.213, 0.141, 0.167],
        "n_large": [40, 22, 1], "net_usd": [4210.0, 3050.0, 900.0],
        "gross_under_usd": [4900.0, 3300.0, 950.0], "low_sample": [False, False, True]})


def weekly_trend(f=None, by: str = "portfolio") -> pd.DataFrame:
    weeks = pd.date_range("2026-05-04", periods=6, freq="7D").date
    series = ["ALL"] if by == "portfolio" else ["PSP_A", "PSP_B"]
    rows = [{"auth_week": f"2026-W{19 + i}", "week_start": w, "series": s, "n": 100 + i,
             "n_flagged": 10 + i, "rate": 0.10 + i / 100, "net_usd": 1000.0 + 100 * i,
             "gross_under_usd": 1200.0, "is_closed": i < 4, "low_sample": False}
            for s in series for i, w in enumerate(weeks)]
    return pd.DataFrame(rows)


def transactions(f=None, min_usd=None, limit=None) -> pd.DataFrame:
    df = pd.DataFrame({
        "transaction_id": ["txn_a", "txn_b", "txn_c"], "auth_date": [date(2026, 6, 14)] * 3,
        "psp": ["PSP_D", "PSP_B", "PSP_A"], "country": ["CL", "MX", "CO"],
        "currency": ["CLP", "MXN", "COP"], "exponent": [0, 2, 2],
        "customer": ["cus_••••7f3a", "cus_••••1b2c", "cus_••••9d8e"],
        "amount_tier": ["200+", "200+", "50-200"], "is_cross_border": [False, True, False],
        "category": ["large"] * 3, "likely_cause": ["psp_rounding", "fx_timing", "unexplained"],
        "why_flagged": ["> 5% and ≥ $20"] * 3, "authorized_amount": [1058000, 250000, 30000000],
        "expected_settled": [1058000, 249000, 30000000], "settled_amount": [1000000, 240000, 29800000],
        "diff_local": [-58000, -10000, -200000], "residual_usd": [-62.10, -55.0, 49.0],
        "abs_residual_usd": [62.10, 55.0, 49.0], "residual_pct": [-5.5, -3.6, -0.7],
        "direction": ["under", "under", "over"], "settle_lag_days": [3, 2, 5]})
    if min_usd is not None:
        df = df[df["abs_residual_usd"] > min_usd]
    return df.head(limit) if limit else df


def outlier_summary(f=None, min_usd=50) -> dict:
    rows = transactions(f, min_usd)
    under = float(-rows.loc[rows["residual_usd"] < 0, "residual_usd"].sum())
    return {"n": len(rows), "gross_under_usd": under, "gross_over_usd": 0.0}


def not_built(*args, **kwargs):
    raise NotImplementedError("M2")
