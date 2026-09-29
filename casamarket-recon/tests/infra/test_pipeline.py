"""Integration tests on the 500-row fixture DB: build outputs, core rows 1-6, DQ gate."""

import duckdb
import pytest

from casarecon import core
from casarecon.pipeline import build


def test_build_and_core_queries(fixture_db):
    with duckdb.connect(str(fixture_db), read_only=True) as con:
        assert con.sql("select count(*), count(distinct transaction_id) "
                       "from marts.fct_transaction_discrepancy").fetchall() == [(500, 500)]
        cats = {c for (c,) in con.sql("select distinct category from marts.fct_transaction_discrepancy").fetchall()}
    assert cats == {None, "exact", "rounding", "fx_tolerance", "meaningful", "large"}
    st = core.status()
    assert (st["n_rows"], st["last_full_month"], st["last_closed_week"]) == (500, "2026-06", "2026-W25")
    ww = core.worst_week("last")
    key = ww.assign(neg=-ww.net_usd)[["low_sample", "neg", "psp", "auth_week"]]
    assert key.equals(key.sort_values(["low_sample", "neg", "psp", "auth_week"]))
    assert core.psp_weekly().n.sum() == core.query_transactions().shape[0]
    df = core.query_transactions(min_usd=20)
    assert tuple(df.columns) == core.TXN_COLUMNS and len(df) > 0
    assert (df.abs_residual_usd > 20).all() and df.customer.str.startswith("cus_••••").all()


def test_failed_dbt_test_exits_dq_and_keeps_last_good_db(fixture_db, tmp_env):
    src, raw = fixture_db.parent / "raw", tmp_env / "raw"
    raw.mkdir()
    (raw / "fx_rates_daily.csv").write_text((src / "fx_rates_daily.csv").read_text())
    lines = (src / "transactions.csv").read_text().splitlines()
    i = next(i for i, ln in enumerate(lines) if ",settled," in ln)
    cols = lines[i].split(",")
    cols[10] = "2020-01-01 00:00:00"  # settle_ts before auth_ts
    lines[i] = ",".join(cols)
    (raw / "transactions.csv").write_text("\n".join(lines) + "\n")
    good = tmp_env / "casarecon.duckdb"
    good.write_bytes(fixture_db.read_bytes())
    with pytest.raises(core.DataQualityError):
        build.main()
    assert good.read_bytes() == fixture_db.read_bytes()
