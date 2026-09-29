"""Checks on the pipeline's own labels (pure): truth scoring and threshold sensitivity."""

from collections.abc import Sequence

import pandas as pd

UNSCORED = {"tip", "unexplained"}  # never planted; reported as counts, not precision/recall
TRUTH_COLUMNS = ["cause", "n_pred", "n_true", "tp", "precision", "recall"]


def truth_scores(pred: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """Precision / recall of `likely_cause` vs truth `true_cause`, per cause, joined on transaction_id."""
    j = pred[["transaction_id", "likely_cause"]].merge(
        truth[["transaction_id", "true_cause"]], on="transaction_id", how="left")
    causes = sorted((set(j["likely_cause"].dropna()) | set(j["true_cause"].dropna())) - UNSCORED)
    rows = []
    for c in causes:
        p, t = j["likely_cause"].eq(c), j["true_cause"].eq(c)
        tp, n_pred, n_true = int((p & t).sum()), int(p.sum()), int(t.sum())
        rows.append({"cause": c, "n_pred": n_pred, "n_true": n_true, "tp": tp,
                     "precision": tp / n_pred if n_pred else None,
                     "recall": tp / n_true if n_true else None})
    return pd.DataFrame(rows, columns=TRUTH_COLUMNS)


def truth_min(scores: pd.DataFrame) -> float | None:
    """Lowest precision or recall in the table (None if empty)."""
    vals = pd.concat([scores["precision"], scores["recall"]]).dropna()
    return float(vals.min()) if len(vals) else None


def sensitivity(fct: pd.DataFrame, pcts: Sequence[float], large_usd: float) -> pd.DataFrame:
    """Flag rate if the `meaningful` cut were each pct (rows beyond exact/rounding only);
    the $ cut (>= large_usd) always flags."""
    candidate = fct["category"].notna() & ~fct["category"].isin(["exact", "rounding"])
    n = len(fct)
    rows = []
    for pct in pcts:
        hit = candidate & ((fct["residual_pct"].abs() > pct) | (fct["abs_residual_usd"] >= large_usd))
        rows.append({"cut_pct": float(pct), "n": n, "n_flagged": int(hit.sum()),
                     "rate": hit.sum() / n if n else 0.0})
    return pd.DataFrame(rows)
