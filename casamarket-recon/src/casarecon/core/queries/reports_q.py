"""Core contract rows 22-24: report-file loaders (not cached by the UI). Owner: BACKEND."""

import pandas as pd

from casarecon.core import paths
from casarecon.core.deps import get_files
from casarecon.ports import ReportFiles

ALERT_COLUMNS = ["period", "rule_id", "segment", "key", "severity", "status", "message", "owner",
                 "psp", "country", "n", "value", "threshold"]


def load_alerts(*, files: ReportFiles | None = None) -> pd.DataFrame | None:
    """#22 reports/alerts.jsonl -> cols: period, rule_id, segment, key, severity, status, message, owner,
    psp, country, n, value, threshold. None if the file is missing."""
    rows = (files or get_files()).read_jsonl(paths.reports_dir() / "alerts.jsonl")
    return None if rows is None else pd.DataFrame(rows).reindex(columns=ALERT_COLUMNS)


def load_findings(*, files: ReportFiles | None = None) -> dict | None:
    """#23 {'markdown': FINDINGS.md text, 'items': findings.json['findings']}. None if findings.json
    is missing; markdown is '' until `recon report` has run."""
    f = files or get_files()
    doc = f.read_json(paths.reports_dir() / "findings.json")
    if doc is None:
        return None
    return {"markdown": f.read_text(paths.reports_dir() / "FINDINGS.md") or "",
            "items": doc.get("findings", [])}


def load_recommendations(*, files: ReportFiles | None = None) -> list[dict] | None:
    """#24 reports/recommendations.json -> list of {rank, action, evidence, owner, implementation,
    usd_quarter}. None if missing."""
    return (files or get_files()).read_json(paths.reports_dir() / "recommendations.json")
