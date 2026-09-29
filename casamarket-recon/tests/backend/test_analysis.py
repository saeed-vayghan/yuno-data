"""Analysis on small hand-made DataFrames (no DB)."""

import json

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from casarecon.analysis import checks, segments, stats
from casarecon.analysis.analyze import analyze
from casarecon.analysis.signatures import signature_table

MONTHS = ["2026-04", "2026-05", "2026-06"]


def make_fct(n: int = 8000, seed: int = 7) -> pd.DataFrame:
    """Settled fct rows with planted P1 (PSP_B x AR), P2 (CO > $300 lag), P3 (weekend),
    P4 (PSP_D cross-border CL/CO rounding) and a PSP_C fee in the last month."""
    rng = np.random.default_rng(seed)
    psp = rng.choice(["PSP_A", "PSP_B", "PSP_C", "PSP_D"], n)
    country = rng.choice(["MX", "CO", "AR", "CL"], n)
    weekend, xb = rng.random(n) < 2 / 7, rng.random(n) < 0.25
    amount, month = rng.uniform(10, 500, n), rng.choice(MONTHS, n)
    flag = rng.random(n) < 0.08 + 0.10 * ((psp == "PSP_B") & (country == "AR")) + 0.05 * weekend
    cause = np.where(flag, rng.choice(["psp_adjustment", "partial_capture"], n), None)
    rounding = (psp == "PSP_D") & xb & np.isin(country, ["CL", "CO"]) & (rng.random(n) < 0.6)
    fee = (psp == "PSP_C") & (month == MONTHS[-1]) & ~flag & (rng.random(n) < 0.4)
    flag, cause = flag | rounding, np.where(rounding, "psp_rounding", np.where(fee, "psp_fee", cause))
    loss = np.where(flag, rng.uniform(5, 40, n), np.where(fee, 1.5, 0.0))
    lag = rng.uniform(1, 6, n) + 5 * ((country == "CO") & (amount > 300))
    return pd.DataFrame({
        "transaction_id": [f"txn_{i:06d}" for i in range(n)], "psp": psp, "country": country,
        "amount_usd": amount, "is_over_300": amount > 300, "is_cross_border": xb,
        "amount_tier": np.where(amount < 50, "10-50", np.where(amount < 200, "50-200", "200+")),
        "is_weekend": weekend, "lag_bucket": np.where(lag <= 3, "2-3", np.where(lag <= 7, "6-7", "8+")),
        "currency": pd.Series(country).map({"MX": "MXN", "CO": "COP", "AR": "ARS", "CL": "CLP"}),
        "settle_lag_days": lag, "auth_month": month, "item_count": rng.integers(1, 4, n),
        "risk_score": rng.random(n), "is_meaningful": flag,
        "category": np.where(flag, "meaningful", np.where(fee, "fx_tolerance", "exact")),
        "likely_cause": cause, "direction": np.where(loss > 0, "under", "none"),
        "rounding_flag": rounding, "residual_usd": -loss, "abs_residual_usd": loss,
        "residual_pct": np.where(flag, -3.0, np.where(fee, -1.0, 0.0)),
    })


def run_analysis(fct: pd.DataFrame, truth: pd.DataFrame | None = None) -> tuple[dict, dict]:
    pareto = pd.DataFrame({"likely_cause": ["psp_adjustment"], "n": [10], "gross_under_usd": [99.0]})
    return analyze(fct, segments.segments_from_fct(fct), pareto=pareto, worst=None, truth=truth,
                   as_of="2026-06-30T23:59:59", late_days=7, high_risk=0.8,
                   sensitivity_pcts=[1, 2, 3], large_usd=20)


def test_stats_and_peer_rule():
    lo, hi = stats.wilson(10, 100)
    assert round(lo, 3) == 0.055 and round(hi, 3) == 0.174
    assert np.allclose(stats.bh([0.01, 0.04, 0.03, 0.5]), [0.04, 0.16 / 3, 0.16 / 3, 0.5])
    assert stats.rate_test(3, 10, 0, 10) == fisher_exact([[3, 7], [0, 10]])[1]  # small cell -> Fisher
    assert stats.excess_loss(0.05, 0.10, 1000, 12.0) == 0.0  # never negative
    # PSP x country is compared only with other PSPs in the same country
    fct = pd.DataFrame({"psp": ["A"] * 10 + ["B"] * 10 + ["A"] * 10,
                        "country": ["AR"] * 20 + ["MX"] * 10,
                        "is_meaningful": [True] * 5 + [False] * 5 + [True] + [False] * 9 + [True] * 10,
                        "residual_usd": [-10.0] * 30})
    seg = segments.rate_frame(fct, ["psp", "country"], segment_type="psp_country")
    t = segments.compare_to_peers(seg, group=lambda v: v.split("|")[1]).set_index("segment_value")
    assert (t.loc["A|AR", "rate"], t.loc["A|AR", "peer_rate"]) == (0.5, 0.1)
    assert t.loc["A|AR", "excess_usd"] == (0.5 - 0.1) * 10 * 10.0
    assert np.isnan(t.loc["A|MX", "peer_rate"])


def test_analyze_finds_planted_patterns():
    fct = make_fct()
    truth = fct[["transaction_id"]].assign(true_cause=fct["likely_cause"])
    doc, tables = run_analysis(fct, truth)
    keys = [f["key"] for f in doc["findings"]]
    planted = {"psp_b_ar_peer", "weekend", "psp_d_rounding", "psp_c_fee_drift", "co_over_300_lag"}
    assert planted <= set(keys)
    assert all(f["q"] < 0.05 for f in doc["findings"])
    usd = [f["usd_quarter"] for f in doc["findings"]]
    assert usd == sorted(usd, reverse=True)
    required = ["n", "rate", "ci", "peer_rate", "lift", "q", "usd_quarter"]
    complete = [f for f in doc["findings"] if all(f[k] is not None for k in required)]
    assert len(complete) >= 4
    assert json.dumps(doc, sort_keys=True) == json.dumps(run_analysis(fct, truth)[0], sort_keys=True)
    assert doc["summary"]["truth_min"] == 1.0 and doc["summary"]["tip_rows"] == 0
    sig = signature_table(fct)
    systematic = sig[sig["label"] == "systematic"]
    assert ((systematic["psp"] == "PSP_D") & (systematic["likely_cause"] == "psp_rounding")).any()
    assert len(tables["glm"]) > 0 and doc["summary"]["glm_dropped"] == []
    sens = checks.sensitivity(fct, [1, 2, 3], large_usd=20)
    assert sens["n_flagged"].is_monotonic_decreasing
