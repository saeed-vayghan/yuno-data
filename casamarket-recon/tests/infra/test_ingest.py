"""recon ingest: land -> load round trip, quarantine of a bad file, schema drift + freshness in check."""

import json

import duckdb
import pytest

from casarecon.core.config import load_config
from casarecon.core.errors import DataQualityError
from casarecon.generate import dataset, writer
from casarecon.ingest import check, land, load, settings

RAW_TYPES = ("{'transaction_id': 'VARCHAR', 'customer_id': 'VARCHAR', 'product_category': 'VARCHAR', "
             "'country': 'VARCHAR', 'currency': 'VARCHAR', 'payer_currency': 'VARCHAR', 'is_cross_border': 'BOOLEAN', "
             "'psp': 'VARCHAR', 'status': 'VARCHAR', 'auth_ts': 'TIMESTAMP', 'settle_ts': 'TIMESTAMP', "
             "'authorized_amount': 'BIGINT', 'settled_amount': 'BIGINT', 'item_count': 'BIGINT', "
             "'risk_score': 'DOUBLE', 'card_bin_country': 'VARCHAR', 'merchant_id': 'VARCHAR'}")


@pytest.fixture
def lake(tmp_path, monkeypatch):
    """2000 generated rows in tmp raw/, landed into tmp lake/. Returns the lake root."""
    for var, sub in (("RAW_DIR", "raw"), ("LAKE_DIR", "lake"), ("REPORTS_DIR", "reports")):
        monkeypatch.setenv(f"CASARECON_{var}", str(tmp_path / sub))
    cfg = load_config()
    ds = dataset.build({**cfg.generator.model_dump(), "rows": 2000, "seed": 42}, cfg.thresholds.model_dump())
    writer.write_all(ds, tmp_path / "raw", tmp_path / "truth")
    land.main()
    return tmp_path / "lake"


def _file(lake_root, psp: str):
    return next(k for k in sorted((lake_root / "landing").glob(f"psp={psp}/date=*/settlements.csv")))


def test_land_load_round_trip_equals_generated_rows(lake):
    assert load.main()["rows"] == 2000
    raw = lake.parent / "raw"
    with duckdb.connect() as con:
        con.sql(f"create view r as from read_csv('{raw}/transactions.csv', header=true, columns={RAW_TYPES})")
        con.sql(f"create view s as from read_parquet('{lake}/staged/transactions/settle_month=*/part-*.parquet', hive_partitioning=false)")
        assert con.sql("select count(*) from s").fetchone()[0] == 2000
        assert con.sql("select count(*) from (from r except from s)").fetchone()[0] == 0
        assert con.sql(f"select count(*) from read_parquet('{lake}/staged/fx_rates_daily/*.parquet')"
                       ).fetchone()[0] == len((raw / "fx_rates_daily.csv").read_text().splitlines()) - 1
    n_files = len(list((lake / "landing").rglob("*.csv")))
    assert load.main() == {"loaded": 0, "quarantined": 0, "skipped": n_files, "rows": 0}  # idempotent


def test_bad_file_goes_to_quarantine(lake):
    bad_enum, banned = _file(lake, "PSP_A"), _file(lake, "PSP_B")
    good = bad_enum.read_bytes()
    bad_enum.write_text(bad_enum.read_text().replace(",MX,", ",BR,", 1).replace(",CO,", ",BR,", 1)
                        .replace(",AR,", ",BR,", 1).replace(",CL,", ",BR,", 1))
    lines = banned.read_text().splitlines()
    banned.write_text("\n".join([lines[0] + ",email"] + [ln + ",x@y.z" for ln in lines[1:]]) + "\n")
    out = load.main()
    assert out["quarantined"] == 2
    for f, problem in ((bad_enum, "enum"), (banned, "banned_field")):
        psp, day = settings.parse_landing_key(f.relative_to(lake).as_posix())
        qdir = lake / "quarantine" / f"psp={psp}" / f"date={day}"
        reason = json.loads((qdir / "reason.json").read_text())
        assert problem in {p["problem"] for p in reason["problems"]}
        assert not (lake / settings.staged_key(psp, day)).exists()
    assert "email" not in (lake / "quarantine").joinpath(
        banned.relative_to(lake / "landing")).read_text().splitlines()[0]  # banned column not kept
    assert load.main()["quarantined"] == 0  # same bytes are not processed twice
    day = settings.parse_landing_key(banned.relative_to(lake).as_posix())[1]
    assert load.main(date_from=day, date_to=day)["quarantined"] == 1  # --from/--to forces a replay
    bad_enum.write_bytes(good)  # fixed re-delivery: loaded, leaves quarantine
    assert load.main()["loaded"] == 1 and len(list((lake / "quarantine").rglob("reason.json"))) == 1


def test_check_flags_schema_drift_and_stale_psp(lake):
    legacy = _file(lake, "PSP_D")
    lines = legacy.read_text().splitlines()
    legacy.write_text("\n".join([lines[0].replace("txn_ref", "txn_id") + ";channel"]
                                + [ln + ";web" for ln in lines[1:]]) + "\n")
    assert check.main() == "WARN"
    rows = {(r["check"], r["psp"]): r for r in json.loads((lake.parent / "reports/ingest_dq.json").read_text())["checks"]}
    drift = rows[("schema_drift", "PSP_D")]
    assert drift["status"] == "WARN" and "new: channel, txn_id" in drift["detail"] and "transaction_id" in drift["detail"]
    assert rows[("schema_drift", "PSP_A")]["status"] == "PASS"
    for f in sorted((lake / "landing").glob("psp=PSP_E/date=2026-06-*/settlements.csv")):
        f.unlink()
    with pytest.raises(DataQualityError, match="freshness:PSP_E"):
        check.main()
