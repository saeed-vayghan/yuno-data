from datetime import date
from decimal import Decimal

import pytest
from typer.testing import CliRunner

from casarecon import core
from casarecon.cli import app
from casarecon.core.config import load_config


def test_mask_id():
    assert core.mask_id("cus_8f2a91c07f3a") == "cus_••••7f3a"
    assert core.mask_id(None) is None


def test_filters_where_sql_uses_params():
    f = core.Filters(psp=("PSP_B",), country=("AR", "MX"), xb="cross", date_from=date(2026, 6, 1))
    sql, params = f.where_sql()
    assert sql == " and country in (?, ?) and psp in (?) and is_cross_border = ? and auth_date >= ?"
    assert params == ["AR", "MX", "PSP_B", True, date(2026, 6, 1)]
    assert core.Filters().where_sql() == ("", [])
    assert hash(f)  # frozen -> cacheable


def test_filters_reject_unknown():
    with pytest.raises(core.BadFilter):
        core.Filters(psp=("PSP_Z",)).validate()


def test_money():
    assert core.exponent("CLP") == 0 and core.exponent("MXN") == 2
    assert core.to_major(12345, "MXN") == Decimal("123.45")
    assert core.round_half_up(2.5) == 3 and core.round_half_up(-2.5) == -3


def test_config_loads():
    assert load_config().thresholds.large_usd == 20


def test_cli_lists_10_commands():
    runner = CliRunner()
    out = runner.invoke(app, ["--help"]).output
    for cmd in ("generate", "build", "validate", "analyze", "alerts", "report", "query",
                "worst-week", "dashboard", "all"):
        assert cmd in out
