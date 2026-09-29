"""Cause-level tests (pure): which PSP carries each cause, fee drift, partial captures, fraud holds."""

import pandas as pd

from casarecon.analysis.segments import two_group

NOT_A_CAUSE = {"tip", "unexplained"}


def cause_key(psp: str, cause: str) -> str:
    """('PSP_D', 'psp_rounding') -> 'psp_d_rounding'."""
    return f"{psp}_{cause.removeprefix('psp_')}".lower()


def q5_cause_psp(fct: pd.DataFrame) -> pd.DataFrame:
    """Q5 systematic vs random: share of rows with each cause, one PSP vs all other PSPs."""
    rows = []
    for cause in sorted(set(fct["likely_cause"].dropna()) - NOT_A_CAUSE):
        flag = fct["likely_cause"].eq(cause)
        for psp, a in fct.groupby("psp", sort=True):
            rows.append(two_group(a, fct[fct["psp"] != psp], flag, segment_type="cause_psp",
                                  segment_value=f"{psp}|{cause}", key=cause_key(psp, cause),
                                  kind="cause_psp", psp=psp, likely_cause=cause,
                                  metric=f"{cause} share"))
    return pd.DataFrame(rows)


def fee_drift(fct: pd.DataFrame) -> pd.DataFrame:
    """psp_fee share in the last month vs the earlier months, per PSP."""
    last = fct["auth_month"].max()
    flag = fct["likely_cause"].eq("psp_fee")
    rows = []
    for psp, d in fct.groupby("psp", sort=True):
        recent = d["auth_month"] == last
        if recent.all() or not recent.any():
            continue
        rows.append(two_group(d[recent], d[~recent], flag, segment_type="fee_drift",
                              segment_value=f"{psp}|{last}", key=f"{psp.lower()}_fee_drift",
                              kind="fee_drift", psp=psp, likely_cause="psp_fee",
                              metric="psp_fee share, last month vs earlier"))
    return pd.DataFrame(rows)


def other_tests(fct: pd.DataFrame, high_risk: float) -> pd.DataFrame:
    """Flag rate for multi-item orders (partial capture) and high-risk orders (fraud hold)."""
    multi = fct["item_count"] >= 2
    risky = fct["risk_score"] >= high_risk
    rows = [
        two_group(fct[multi], fct[~multi], segment_type="item_count", segment_value="2+",
                  key="partial_capture", kind="partial_capture", likely_cause="partial_capture",
                  metric="flag rate"),
        two_group(fct[risky], fct[~risky], segment_type="risk_score", segment_value="high",
                  key="fraud_hold", kind="fraud_hold", likely_cause="fraud_hold", metric="flag rate"),
    ]
    return pd.concat([pd.DataFrame(rows), fee_drift(fct)], ignore_index=True)
