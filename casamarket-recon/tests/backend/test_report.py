"""Reports: templates carry no hand-typed numbers; rendered output has the required shape."""

import re

import pytest

from casarecon import core
from casarecon.adapters import files
from casarecon.core import paths
from casarecon.report import run as report_run
from casarecon.report.render import TEMPLATES
from tests.backend.test_analysis import make_fct, run_analysis

JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
ALLOWED = re.compile(r"\b[FR]\d+\b|95%|\$127k")


def test_templates_have_no_hand_typed_numbers():
    for tpl in TEMPLATES.glob("*.j2"):
        text = ALLOWED.sub("", JINJA.sub("", tpl.read_text()))
        assert not re.search(r"\d", text), f"{tpl.name}: {re.findall(r'.{0,20}\d.{0,20}', text)}"


def test_report_renders_findings_and_recommendations(tmp_env):
    with pytest.raises(core.CasaReconError):  # analyze has not run yet
        report_run.main()
    doc, tables = run_analysis(make_fct())
    out = paths.reports_dir()
    for name, df in tables.items():
        files.write_csv(out / "analysis" / f"{name}.csv", df)
    files.write_json(out / "findings.json", doc)
    assert core.load_findings() == {"markdown": "", "items": doc["findings"]}
    assert core.load_recommendations() is None and core.load_alerts() is None

    counts = report_run.main()

    md = (out / "FINDINGS.md").read_text()
    lines = [ln for ln in md.splitlines() if re.match(r"^\*\*F\d", ln)]
    assert len(lines) >= 4 and all(re.search(r"n = .*CI.*lift.*q.*\$", ln) for ln in lines)
    assert "tip: ruled out" in md
    recs = core.load_recommendations()
    assert 3 <= len(recs) == counts["recommendations"] <= 5
    assert set(recs[0]) >= {"rank", "action", "evidence", "owner", "implementation", "usd_quarter"}
    rec_md = (out / "RECOMMENDATIONS.md").read_text()
    assert len(re.findall(r"^\| R\d", rec_md, re.M)) == len(recs)
    cited = set(re.findall(r"F\d+", " ".join(r["evidence"] for r in recs)))
    assert cited <= {f["id"] for f in doc["findings"]}
    assert core.load_findings()["markdown"] == md
