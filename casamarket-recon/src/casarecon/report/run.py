"""Entry point for `recon report`. Owner: BACKEND.

Shell only: read reports/findings.json + reports/analysis/*.csv (+ alerts.jsonl if present),
render, write FINDINGS.md, RECOMMENDATIONS.md and recommendations.json.
"""

from casarecon.core import log, paths
from casarecon.core.deps import get_files
from casarecon.core.errors import CasaReconError
from casarecon.ports import ReportFiles
from casarecon.report.recommend import recommend
from casarecon.report.render import TABLES, render_findings, render_recommendations

REC_KEYS = ("rank", "action", "evidence", "owner", "implementation", "usd_quarter", "reduction_pct",
            "method")


def main(files: ReportFiles | None = None) -> dict:
    """Render both reports; return {'findings': n, 'recommendations': n}."""
    files = files or get_files()
    out = paths.reports_dir()
    doc = files.read_json(out / "findings.json")
    if doc is None:
        raise CasaReconError("reports/findings.json missing; run `recon analyze` first")
    tables = {}
    for name in TABLES:
        df = files.read_csv(out / "analysis" / f"{name}.csv")
        tables[name] = [] if df is None else df.to_dict("records")
    recs = recommend(doc["findings"])
    files.write_text(out / "FINDINGS.md",
                     render_findings(doc, tables, files.read_jsonl(out / "alerts.jsonl"), recs))
    files.write_text(out / "RECOMMENDATIONS.md", render_recommendations(recs, doc))
    files.write_json(out / "recommendations.json", [{k: r[k] for k in REC_KEYS} for r in recs])
    counts = {"findings": len(doc["findings"]), "recommendations": len(recs)}
    log.get("report").info(log.kv(**counts, out=out))
    return counts
