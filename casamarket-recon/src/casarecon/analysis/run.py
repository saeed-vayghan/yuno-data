"""Entry point for `recon analyze`. Owner: BACKEND.

Shell only: read via core + the ReportFiles port, call the pure `analyze`, write
reports/analysis/*.csv, reports/figures/*, reports/findings.json.
"""

from pathlib import Path

from casarecon import core
from casarecon.analysis.analyze import analyze
from casarecon.analysis.figures import figure_name, finding_figure
from casarecon.analysis.findings import with_figures
from casarecon.core import log, paths
from casarecon.core.config import load_config
from casarecon.core.deps import get_files, get_store
from casarecon.ports import ReportFiles, Store

SEGMENT_DIMS = ("country", "currency", "psp_country", "amount_tier", "is_weekend", "lag_bucket",
                "cross_border")


def _save_figures(doc: dict, out: Path, files: ReportFiles) -> dict:
    targets = {paths.figures_dir() / figure_name(f): finding_figure(f) for f in doc["findings"]}
    written = files.write_figures(targets)
    by_id = {f["id"]: written[paths.figures_dir() / figure_name(f)].relative_to(out).as_posix()
             for f in doc["findings"]}
    return with_figures(doc, by_id)


def main(store: Store | None = None, files: ReportFiles | None = None) -> dict:
    """Run the analysis; return the findings summary. Raises DbMissing / DbBusy from the store."""
    store, files = store or get_store(), files or get_files()
    th = load_config().thresholds
    fct = core.settled_facts(store=store)
    seg = {dim: core.segment_rates(dim, store=store) for dim in SEGMENT_DIMS}
    doc, tables = analyze(
        fct, seg, pareto=core.cause_summary(store=store), worst=core.worst_week("last", store=store),
        truth=files.read_parquet(paths.truth_dir() / "labels.parquet"),
        as_of=core.status(store=store)["as_of"], late_days=th.lag_outlier_days,
        high_risk=th.causes.high_risk_score, sensitivity_pcts=list(th.sensitivity_pcts),
        large_usd=th.large_usd)
    out = paths.reports_dir()
    for name, df in tables.items():
        files.write_csv(out / "analysis" / f"{name}.csv", df)
    doc = _save_figures(doc, out, files)
    files.write_json(out / "findings.json", doc)
    log.get("analyze").info(log.kv(rows=len(fct), findings=len(doc["findings"]),
                                   out=out / "findings.json"))
    return doc["summary"]
