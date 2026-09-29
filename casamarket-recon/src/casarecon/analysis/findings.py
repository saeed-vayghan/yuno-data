"""findings.json builder (pure). Ranked by usd_quarter desc; only q < 0.05 become findings.

The data window is one quarter, so window $ = usd_quarter. Byte-stable: no wall-clock time,
floats rounded to 6 dp (the adapter sorts keys).
"""

import math
from datetime import date, datetime

import numpy as np
import pandas as pd

from casarecon.analysis.checks import truth_min

Q_MAX = 0.05
CFO_ESTIMATE_USD = 127_000
MAX_NOT_SIGNIFICANT = 10


def jsonable(x: object) -> object:
    """Plain JSON types: numpy -> python, floats rounded to 6 dp, NaN/inf -> None, dates -> ISO."""
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [jsonable(v) for v in x]
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float):
        return round(x, 6) if math.isfinite(x) else None
    if isinstance(x, datetime | date | pd.Timestamp):
        return x.isoformat()
    if x is pd.NA or x is pd.NaT:
        return None
    return x


def headline(r: pd.Series) -> str:
    """One sentence, words only (numbers are added by the report template)."""
    seg = str(r["segment_value"])
    return {
        "peer": f"{r['psp']} in {r['country']} flags more often than other PSPs in {r['country']}",
        "weekend": "Weekend authorizations flag more often than weekday ones",
        "cross_border": "Cross-border payments flag more often than domestic ones",
        "cause_psp": f"{r['psp']} carries a disproportionate share of `{r['likely_cause']}` gaps",
        "fee_drift": f"{r['psp']} fee gaps jumped in {seg.split('|')[-1]} vs earlier months",
        "lag": f"{r['country']} orders over $300 settle late more often than other {r['country']} orders",
        "partial_capture": "Multi-item orders flag more often (partial captures)",
        "fraud_hold": "High-risk orders flag more often (fraud holds)",
    }.get(r["kind"], f"{r['segment_type']} {seg} differs from its peers")


def candidates(tests: pd.DataFrame) -> pd.DataFrame:
    """Keyed rows that are worse than their peers (rate > peer rate; peers must exist) and cost
    money (excess $ > 0; lag findings are about delay, so they are kept regardless)."""
    rate = pd.to_numeric(tests["rate"], errors="coerce")
    peer = pd.to_numeric(tests["peer_rate"], errors="coerce").fillna(math.inf)
    costly = (pd.to_numeric(tests["excess_usd"], errors="coerce") > 0) | (tests["kind"] == "lag")
    return tests[tests["key"].notna() & (rate > peer) & costly]


def _segment(r: pd.Series) -> str:
    """'true' on a boolean segment reads badly; use the finding key instead."""
    return r["key"] if str(r["segment_value"]) in ("true", "false") else r["segment_value"]


def _item(i: int, r: pd.Series, total_under: float) -> dict:
    usd = float(r["excess_usd"])
    return {"id": f"F{i}", "key": r["key"], "kind": r["kind"], "headline": headline(r),
            "metric": r["metric"], "segment": _segment(r), "psp": r["psp"],
            "country": r["country"], "n": int(r["n"]), "n_flagged": int(r["n_flagged"]),
            "rate": r["rate"], "ci": [r["ci_low"], r["ci_high"]], "peer_rate": r["peer_rate"],
            "lift": r["lift"], "q": r["q"], "usd_quarter": usd, "usd_median": r["median_loss_usd"],
            "share_of_loss": usd / total_under if total_under else 0.0,
            "likely_cause": r["likely_cause"], "usd_note": r["usd_note"], "figure": None}


def summarize(fct: pd.DataFrame, pareto: pd.DataFrame, worst: pd.DataFrame | None,
              truth: pd.DataFrame, glm_dropped: list[str]) -> dict:
    """Headline numbers for the report summary (settled rows in `fct`)."""
    res = fct["residual_usd"]
    under, over = float((-res).clip(lower=0).sum()), float(res.clip(lower=0).sum())
    n = len(fct)
    flagged = int(fct["is_meaningful"].fillna(False).astype(bool).sum())
    non_exact = int((fct["category"].notna() & (fct["category"] != "exact")).sum())
    ok = worst[~worst["low_sample"].astype(bool)] if worst is not None and len(worst) else None
    return {"n_rows": n, "n_flagged": flagged, "flag_rate": flagged / n if n else 0.0,
            "non_exact_rate": non_exact / n if n else 0.0, "gross_under_usd": under,
            "gross_over_usd": over, "net_usd": under - over, "cfo_estimate_usd": CFO_ESTIMATE_USD,
            "window": {"from": fct["auth_month"].min(), "to": fct["auth_month"].max(),
                       "months": int(fct["auth_month"].nunique())},
            "worst_week": ok.iloc[0].to_dict() if ok is not None and len(ok) else None,
            "causes": pareto.to_dict("records"), "truth_min": truth_min(truth),
            "tip_rows": int(fct["likely_cause"].eq("tip").sum()),
            "unexplained_rows": int(fct["likely_cause"].eq("unexplained").sum()),
            "glm_dropped": list(glm_dropped)}


def build_findings(tests: pd.DataFrame, summary: dict, as_of: object) -> dict:
    """{"as_of", "summary", "findings": [...], "not_significant": [...]} as plain JSON types."""
    cand = candidates(tests)
    sig = cand[cand["q"] < Q_MAX].sort_values(["excess_usd", "key"], ascending=[False, True])
    items = [_item(i, r, summary["gross_under_usd"]) for i, (_, r) in enumerate(sig.iterrows(), 1)]
    rest = cand[~(cand["q"] < Q_MAX)].sort_values(["q", "key"]).head(MAX_NOT_SIGNIFICANT)
    not_sig = [{"key": r["key"], "segment": r["segment_value"], "metric": r["metric"],
                "lift": r["lift"], "q": r["q"]} for _, r in rest.iterrows()]
    return jsonable({"as_of": as_of, "summary": summary, "findings": items,
                     "not_significant": not_sig})


def with_figures(doc: dict, figures: dict[str, str]) -> dict:
    """Copy of `doc` with each finding's `figure` set from {finding id: path relative to reports/}."""
    items = [{**f, "figure": figures.get(f["id"])} for f in doc["findings"]]
    return {**doc, "findings": items}
