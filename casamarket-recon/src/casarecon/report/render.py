"""Jinja rendering (pure): findings.json + CSV rows -> FINDINGS.md / RECOMMENDATIONS.md text."""

import math
from collections import Counter
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from casarecon.analysis.findings import Q_MAX
from casarecon.report.fmt import FILTERS
from casarecon.report.recommend import rec_refs

TEMPLATES = Path(__file__).parent / "templates"
TOP_N = 10
TEST_COLS = ["segment_type", "segment_value", "n", "rate", "ci_low", "ci_high", "peer_rate", "lift",
             "q", "excess_usd"]
# CSV name -> (columns shown, sort column, ascending, row limit)
TABLES = {
    "q1_country": (TEST_COLS, "segment_type", True, None),
    "q2_psp_country": (TEST_COLS, "excess_usd", False, None),
    "q3_size": (TEST_COLS, "segment_type", True, None),
    "q4_time": (TEST_COLS, "segment_type", True, None),
    "q5_cause_psp": (TEST_COLS, "excess_usd", False, TOP_N),
    "q6_other": (TEST_COLS, "excess_usd", False, None),
    "q5_signatures": (["psp", "country", "likely_cause", "direction", "n", "concentration", "usd",
                       "label"], "usd", False, TOP_N),
    "glm": (["term", "odds_ratio", "or_ci_low", "or_ci_high", "p"], "p", True, TOP_N),
    "truth_check": (["cause", "n_pred", "n_true", "precision", "recall"], "cause", True, None),
    "sensitivity": (["cut_pct", "n", "n_flagged", "rate"], "cut_pct", True, None),
    "cause_pareto": (["likely_cause", "n", "gross_under_usd", "gross_over_usd", "net_usd",
                      "share_of_loss"], "gross_under_usd", False, None),
}


def environment() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    env.filters.update(FILTERS)
    return env


def render(name: str, ctx: dict) -> str:
    return environment().get_template(name).render(**ctx)


def _missing(v: object) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def shape_tables(tables: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Sort and trim each known table for display (missing CSV -> empty list; blanks sort last)."""
    out = {}
    for name, (_, col, asc, limit) in TABLES.items():
        rows = [r for r in tables.get(name, []) if r.get("term") != "Intercept"]
        present = [r for r in rows if not _missing(r.get(col))]
        rows = sorted(present, key=lambda r: r[col], reverse=not asc) + [
            r for r in rows if _missing(r.get(col))]
        out[name] = rows[:limit] if limit else rows
    return out


def alert_summary(alerts: list[dict] | None) -> dict | None:
    """Counts by severity + the non-INFO rows; None when alerts.jsonl does not exist."""
    if alerts is None:
        return None
    counts = Counter(a.get("severity", "INFO") for a in alerts)
    return {"counts": sorted(counts.items()),
            "rows": [a for a in alerts if a.get("severity") != "INFO"]}


def findings_context(doc: dict, tables: dict[str, list[dict]], alerts: list[dict] | None,
                     recs: list[dict]) -> dict:
    refs = rec_refs(recs)
    items = [{**f, "rec_ref": refs.get(f["id"], "RECOMMENDATIONS.md")} for f in doc["findings"]]
    return {"as_of": doc["as_of"], "s": doc["summary"], "findings": items, "q_max": Q_MAX,
            "not_significant": doc["not_significant"], "t": shape_tables(tables),
            "cols": {name: spec[0] for name, spec in TABLES.items()}, "top_n": TOP_N,
            "alerts": alert_summary(alerts)}


def render_findings(doc: dict, tables: dict[str, list[dict]], alerts: list[dict] | None,
                    recs: list[dict]) -> str:
    return render("FINDINGS.md.j2", findings_context(doc, tables, alerts, recs))


def render_recommendations(recs: list[dict], doc: dict) -> str:
    return render("RECOMMENDATIONS.md.j2", {"recs": recs, "as_of": doc["as_of"]})
