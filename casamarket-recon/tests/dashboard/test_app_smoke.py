"""Streamlit AppTest smoke tests with a fake data module (no DB needed)."""

import re

from casarecon.dashboard import data

MASK = re.compile(r"^cus_••••.{4}$")


def _text(at) -> str:
    kinds = ("markdown", "caption", "info", "title", "subheader")
    return "\n".join(str(e.value) for kind in kinds for e in getattr(at, kind))


def test_overview_card_kpis_trend_and_placeholders(app, fake_data):
    at = app.run()
    assert not at.exception
    text = _text(at)
    assert "PSP_B · W24 (Jun 8–14) · Net loss $4,210.00" in text
    assert "Data as of 2026-06-30 · Last closed week W25 (Jun 15–21)" in text
    assert [m.value for m in at.metric][:3] == ["14.2%", "$9.8k", "9"]
    assert "not available yet" in text  # week_over_week is a stub: only that block greys out
    for page in ("drill_down", "root_causes", "alerts"):
        at.switch_page(f"views/{page}.py").run()
        assert not at.exception and any("Coming in" in i.value for i in at.info)


def test_outliers_filters_carry_over_and_missing_db(app, fake_data, monkeypatch):
    at = app.run()
    at.multiselect(key="w_psp").set_value(["PSP_B"]).run()
    at.switch_page("views/outliers.py").run()
    assert not at.exception and at.multiselect(key="w_psp").value == ["PSP_B"]
    df = at.dataframe[0].value
    assert len(df) == 2 and (df["residual_usd"].abs() > 50).all()
    assert all(MASK.match(c) for c in df["customer"])
    assert "2 transactions · $117.10 under · $0.00 over" in _text(at)

    def missing(*a, **k):
        raise data.DbMissing("data/casarecon.duckdb")

    monkeypatch.setattr(data, "status", missing)
    at.run()
    assert any("Run `make all` first" in i.value for i in at.info)
