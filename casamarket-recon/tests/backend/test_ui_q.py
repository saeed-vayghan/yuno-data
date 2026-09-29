"""ui_q contract rows 13-21 on the hand-countable mini DB (see test_ui_q_minidb.ROWS)."""

from datetime import date

import pytest

from casarecon.core import BadFilter, Filters
from casarecon.core.queries import ui_q
from casarecon.core.queries.pipeline_q import status
from casarecon.core.queries.ui_q_base import prev_week
from tests.backend.test_ui_q_minidb import minidb  # noqa: F401  (fixture)


def test_one_week_rule_status_kpis_trend(minidb):
    """as_of 2026-06-30 12:00: core.weeks (via status) says W25 closed, W26/W27 open; ui_q agrees."""
    st = status(store=minidb)
    assert st["last_closed_week"] == ui_q.kpis(store=minidb)["week"] == "2026-W25"
    assert ui_q.week_over_week(store=minidb)["week_last"].iloc[0] == st["last_closed_week"]
    assert prev_week("2026-W25") == "2026-W24" and prev_week("2026-W01") == "2025-W52"


def test_overview_kpis_trend_wow(minidb):
    k = ui_q.kpis(store=minidb)  # last closed W25 vs W24
    assert (k["week"], k["prev_week"], k["n"], k["n_flagged"], k["n_large"]) == (
        "2026-W25", "2026-W24", 6, 3, 2)
    assert (k["flag_rate"], k["gross_under_usd"], k["net_usd"]) == (0.5, 35.5, 10.5)
    assert (k["delta_rate_pts"], k["delta_net_usd"], k["delta_n_large"]) == (0.0, -29.5, 1)
    assert ui_q.kpis(week="all", store=minidb)["n"] == 11  # settled rows only, no deltas
    b = ui_q.kpis(Filters(psp=("PSP_B",)), week="2026-W25", store=minidb)
    assert (b["n"], b["n_flagged"], b["net_usd"]) == (2, 0, 0.5)
    with pytest.raises(BadFilter):
        ui_q.kpis(week="June", store=minidb)

    trend = ui_q.weekly_trend(store=minidb)
    closed = dict(zip(trend["auth_week"], trend["is_closed"]))
    assert closed["2026-W25"] and not closed["2026-W26"] and not closed["2026-W27"]
    assert set(trend["series"]) == {"ALL"} and trend["low_sample"].all()
    assert set(ui_q.weekly_trend(by="psp", store=minidb)["series"]) == {"PSP_A", "PSP_B", "PSP_D"}

    wow = ui_q.week_over_week(store=minidb)
    top = wow.iloc[0]
    assert (top["psp"], top["week_prev"], top["week_last"], top["delta_pts"]) == (
        "PSP_A", "2026-W24", "2026-W25", 25.0)
    assert wow.iloc[1]["n_prev"] == 0  # PSP_B AR had no W24 rows -> NaN delta, sorted last


def test_outliers_summary_detail_similar(minidb):
    assert ui_q.outlier_summary(min_usd=25, store=minidb) == {  # strict >: the $25 row is out
        "n": 2, "gross_under_usd": 70.0, "gross_over_usd": 0.0}
    assert ui_q.outlier_summary(Filters(category=("large",)), min_usd=0, store=minidb) == {
        "n": 3, "gross_under_usd": 70.0, "gross_over_usd": 25.0}
    d = ui_q.transaction_detail("t25c", store=minidb)
    assert d["customer"] == "cus_••••t25c" and "customer_id" not in d
    assert (d["auth_date"], d["residual_usd"], d["is_lag_outlier"]) == (date(2026, 6, 17), -30.0, True)
    assert ui_q.transaction_detail("nope", store=minidb) is None
    assert ui_q.similar_count("t25c", store=minidb) == {
        "psp": "PSP_A", "country": "MX", "likely_cause": "psp_fee", "n": 2}


def test_drill_category_mix_options_pending(minidb):
    w25 = ui_q.category_mix(store=minidb).query("auth_week == '2026-W25'")
    assert list(w25["category"]) == ["exact", "fx_tolerance", "meaningful", "large"]
    assert list(w25["n"]) == [2, 1, 1, 2] and w25["share"].sum() == pytest.approx(1.0)
    o = ui_q.filter_options(store=minidb)
    assert o["psp"] == ["PSP_A", "PSP_B", "PSP_C", "PSP_D", "PSP_E"]
    # full months per core.weeks: May starts on the first day; June ends on as_of (Jun 30)
    assert (o["min_date"], o["max_date"], o["months"]) == ("2026-05-01", "2026-06-29", ["2026-05", "2026-06"])
    assert (o["weeks"][0], o["weeks"][-1]) == ("2026-W18", "2026-W27")
    p = ui_q.pending(store=minidb)  # age vs as_of (data time), oldest first
    assert list(p["psp"]) == ["PSP_C", "PSP_A"] and list(p["oldest_age_days"]) == [20.0, 5.0]
