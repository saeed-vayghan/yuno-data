"""Generator: determinism, contract shape, bucket/pattern sanity (file 03 step 8)."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from casarecon.core.config import load_config
from casarecon.generate import dataset, fx, writer


def _build(rows: int, seed: int = 42) -> dataset.Dataset:
    cfg = load_config()
    g = {**cfg.generator.model_dump(), "rows": rows, "seed": seed}
    return dataset.build(g, cfg.thresholds.model_dump())


@pytest.fixture(scope="module")
def ds5k() -> dataset.Dataset:
    return _build(5000)


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_same_seed_same_bytes(tmp_path):
    a = writer.write_all(_build(800), tmp_path / "a", tmp_path / "ta")
    b = writer.write_all(_build(800), tmp_path / "b", tmp_path / "tb")
    c = writer.write_all(_build(800, seed=7), tmp_path / "c", tmp_path / "tc")
    for name in ("transactions", "fx_rates_daily", "manifest"):
        assert _sha(a[name]) == _sha(b[name])
    assert _sha(a["transactions"]) != _sha(c["transactions"])


def test_csv_matches_contract(tmp_path, ds5k):
    out = writer.write_all(ds5k, tmp_path / "raw", tmp_path / "truth")
    cols = writer.contract_columns()
    raw = pd.read_csv(out["transactions"], dtype=str, keep_default_na=False)
    assert list(raw.columns) == cols and not {"pan", "card_number", "cvv", "email", "name"} & set(cols)
    assert raw["transaction_id"].str.fullmatch(r"txn_[0-9a-f]{12}").all() and raw["transaction_id"].is_unique
    assert raw["customer_id"].str.fullmatch(r"cus_[0-9a-f]{12}").all()
    assert raw["authorized_amount"].str.fullmatch(r"\d+").all()
    settled = raw["status"] == "settled"
    assert raw.loc[settled, "settled_amount"].str.fullmatch(r"\d+").all()
    assert (raw.loc[~settled, ["settled_amount", "settle_ts"]] == "").all().all()
    assert (raw.loc[settled, "settle_ts"] <= "2026-06-30 23:59:59").all()
    assert (raw.loc[settled, "settle_ts"] > raw.loc[settled, "auth_ts"]).all()
    assert set(raw["status"]) == {"settled", "pending", "failed"}
    assert set(raw["country"]) == {"MX", "CO", "AR", "CL"} and raw["psp"].nunique() == 5
    labels = pd.read_parquet(out["labels"])
    assert list(labels.columns) == ["transaction_id", "true_bucket", "true_cause", "pattern_ids"]


def test_buckets_and_patterns(ds5k):
    s = ds5k.transactions[ds5k.transactions["status"] == "settled"]
    shares = s["bucket"].value_counts(normalize=True)
    for bucket, target in load_config().generator.model_dump()["buckets"].items():
        assert abs(shares.get(bucket, 0) - target) < 0.02, bucket
    assert s.loc[s["is_cross_border"], "bucket"].eq("exact").mean() <= 0.01
    residual = s["settled_amount"].astype("int64") - s["expected"]
    usd = residual.abs() / 10.0 ** s["exponent"] / s["fx_auth"]
    pct = 100 * residual.abs() / s["expected"]
    m = s["bucket"] == "meaningful"
    assert (usd[m] < 20).all() and pct[m].between(2, 5).all()
    p4 = s[s["is_p4"]]
    step = 1000 * 10 ** p4["exponent"]
    assert len(p4) > 0 and (p4["settled_amount"].astype("int64") % step == 0).all()
    assert (p4["settled_amount"].astype("int64") <= p4["expected"]).all()
    assert fx.max_move_pct(ds5k.fx_rates) < 2
    assert np.isin(s.loc[s["cause"] == "X3", "psp"], ["PSP_C"]).all()
    assert (s.loc[s["cause"] == "X3", "auth_ts"].dt.month == 6).all()
