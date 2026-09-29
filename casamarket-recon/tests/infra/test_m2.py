"""M2 on the fixture DB: core rows 7-10 + settled_facts, and the validation gate."""

import pytest

from casarecon import core
from casarecon.core.filters import CAUSES
from casarecon.validate import checks, run
from casarecon.validate.metrics import read_metrics
from casarecon.core.deps import get_store


def test_core_rows_7_to_10(fixture_db):
    facts = core.settled_facts()
    seg = core.segment_rates("psp_country")
    assert seg.n.sum() == len(facts) and seg.segment_value.str.match(r"^PSP_[A-E]\|(MX|CO|AR|CL)$").all()
    assert set(core.segment_rates("is_weekend").segment_value) == {"true", "false"}
    assert (seg.ci_low <= seg.rate).all() and (seg.rate <= seg.ci_high).all()
    co = core.segment_rates("country", core.Filters(country=("CO",)))
    assert list(co.segment_value) == ["CO"]
    cs = core.cause_summary()
    assert sorted(cs.likely_cause) == sorted(CAUSES)
    non_exact = facts[facts.category != "exact"]
    assert cs.net_usd.sum() == pytest.approx(-non_exact.residual_usd.sum(), abs=0.05)
    ex = core.excess_loss(top=3)
    assert len(ex) == 3 and (ex.excess_usd >= 0).all() and ex.excess_usd.is_monotonic_decreasing
    assert {"median_lag_days", "p90_lag_days", "late_share"} <= set(core.lag_by_country_tier().columns)


def test_validate_gate(fixture_db, capsys):
    assert run.main() in ("PASS", "WARN")  # smoke run: pattern bands may only warn
    assert "P4" in capsys.readouterr().out
    doctored = read_metrics(get_store()) | {"k_large": 0.30 * 500, "k_meaningful": 0.35 * 500}
    assert checks.overall(checks.evaluate(doctored, full=False)) == "FAIL"
