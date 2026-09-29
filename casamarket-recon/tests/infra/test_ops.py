"""`recon ops`: PII scan (CLI, exit codes) and the pure planners (lineage summary, backfill steps)."""

from datetime import date

import pytest
from typer.testing import CliRunner

from casarecon.cli import app
from casarecon.core.errors import DataQualityError, InputMissing
from casarecon.ops import backfill, lineage

runner = CliRunner()


def test_pii_scan_catches_banned_field_and_full_customer_id(tmp_env):
    raw, reports = tmp_env / "raw", tmp_env / "reports"
    raw.mkdir(), reports.mkdir()
    (raw / "transactions.csv").write_text("transaction_id,customer_id\ntxn_1,cus_390659ee14b5\n")
    (reports / "alerts.md").write_text("customer cus_••••14b5\n")  # masked: fine
    res = runner.invoke(app, ["ops", "pii-scan"])
    assert res.exit_code == 0, res.output  # full IDs are allowed in raw (token)

    (raw / "settlements.csv").write_text("transaction_id,Email\ntxn_1,a@b.c\n")
    (reports / "top.csv").write_text("transaction_id,customer\ntxn_1,cus_390659ee14b5\n")
    res = runner.invoke(app, ["ops", "pii-scan"])
    assert res.exit_code == 5
    assert "banned field 'Email'" in res.output and "unmasked customer id" in res.output
    assert "cus_390659ee14b5" not in res.output  # the scan never prints the full ID


def test_lineage_summary_and_backfill_plan(tmp_env):
    manifest = {"nodes": {
        "seed.p.fees": {"resource_type": "seed", "name": "fees", "schema": "ref"},
        "model.p.stg": {"resource_type": "model", "name": "stg", "schema": "staging",
                        "depends_on": {"nodes": ["source.p.raw.txn"]}},
        "model.p.fct": {"resource_type": "model", "name": "fct", "schema": "marts",
                        "depends_on": {"nodes": ["model.p.stg", "seed.p.fees"]}},
        "test.p.t1": {"resource_type": "test", "name": "t1", "schema": "marts"}}}
    rows = lineage.summarize(manifest)
    assert [(r["model"], r["parents"], r["sources"]) for r in rows] == [
        ("fct", ["fees", "stg"], ["fees", "raw.txn"]), ("stg", ["raw.txn"], ["raw.txn"])]

    steps = backfill.plan(date(2026, 6, 1), date(2026, 6, 2), as_of=date(2026, 6, 30))
    assert steps == [(["ingest", "load"], {}), (["ingest", "check", "--as-of", "2026-06-02"], {}),
                     (["build", "--incremental", "--lookback-days", "30"], {"CASARECON_SOURCE": "lake"})]

    calls, run = [], {"start": date(2026, 6, 1), "end": date(2026, 6, 1), "as_of": date(2026, 6, 1)}
    with pytest.raises(InputMissing):  # no landing files for the range yet
        backfill.main(**run, runner=lambda args, env: 0)
    day = tmp_env / "lake" / "landing" / "psp=PSP_A" / "date=2026-06-01"
    day.mkdir(parents=True), (day / "settlements.csv").write_text("transaction_id\n")
    with pytest.raises(DataQualityError):  # a failed DQ step (exit 5) stops the replay
        backfill.main(**run, runner=lambda args, env: calls.append(args) or (5 if args[1] == "check" else 0))
    assert calls == [["ingest", "load"], ["ingest", "check", "--as-of", "2026-06-01"]]
