"""CLI smoke on the fixture DB (Typer CliRunner): both brief questions + exit codes."""

import csv
import io
import json

from typer.testing import CliRunner

from casarecon import core
from casarecon.cli import app

runner = CliRunner()


def test_cli_smoke(fixture_db, tmp_path, monkeypatch):
    res = runner.invoke(app, ["worst-week", "--month", "last", "--format", "json"])
    assert res.exit_code == 0, res.output
    top, out = core.worst_week("last").iloc[0], json.loads(res.stdout)
    assert (out["month"], out["worst"]["psp"], out["worst"]["net_usd"]) == ("2026-06", top.psp, top.net_usd)
    res = runner.invoke(app, ["query", "--min-usd", "20", "--format", "csv"])
    rows = list(csv.DictReader(io.StringIO(res.stdout)))
    assert tuple(rows[0]) == core.TXN_COLUMNS and all(float(r["abs_residual_usd"]) > 20 for r in rows)
    assert runner.invoke(app, ["query", "--psp", "PSP_Z"]).exit_code == 2
    monkeypatch.setenv("CASARECON_DB", str(tmp_path / "none.duckdb"))
    res = runner.invoke(app, ["worst-week"])
    assert res.exit_code == 1 and "Run `make all` first" in res.output
