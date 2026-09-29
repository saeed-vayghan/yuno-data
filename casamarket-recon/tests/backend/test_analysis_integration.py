"""analyze -> report on the 500-row fixture DB (skips until INFRA's `fixture_db` and the M2 marts exist)."""

import pytest

from casarecon import core


def test_analyze_and_report_on_fixture_db(request, tmp_path, monkeypatch):
    try:
        request.getfixturevalue("fixture_db")
    except pytest.FixtureLookupError:
        pytest.skip("fixture_db not available yet (INFRA M1)")
    monkeypatch.setenv("CASARECON_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("CASARECON_FIGURE_FORMAT", "html")
    from casarecon.analysis import run as analysis_run
    from casarecon.report import run as report_run

    try:
        analysis_run.main()
    except NotImplementedError as e:
        pytest.skip(f"core contract function not built yet: {e}")
    report_run.main()  # smoke data: few or no significant findings, but both steps must succeed
    assert core.load_findings()["markdown"].startswith("# Settlement discrepancy findings")
    assert isinstance(core.load_recommendations(), list)
