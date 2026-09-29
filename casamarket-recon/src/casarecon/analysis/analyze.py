"""The whole analysis as one pure function: DataFrames in, (findings doc, CSV tables) out."""

import pandas as pd

from casarecon.analysis import checks, glm, rca
from casarecon.analysis.findings import build_findings, summarize
from casarecon.analysis.signatures import signature_table

# CSV name -> questions it holds (reports/analysis/<name>.csv)
QUESTION_TABLES = {"q1_country": ["Q1"], "q2_psp_country": ["Q2"], "q3_size": ["Q3"],
                   "q4_time": ["Q4"], "q5_cause_psp": ["Q5"], "q6_other": ["Q6"]}


def analyze(fct: pd.DataFrame, seg: dict[str, pd.DataFrame], *, pareto: pd.DataFrame,
            worst: pd.DataFrame | None, truth: pd.DataFrame | None, as_of: object,
            late_days: float, high_risk: float, sensitivity_pcts: list[float],
            large_usd: float, glm_min_cell: int = glm.MIN_CELL) -> tuple[dict, dict[str, pd.DataFrame]]:
    """`fct` = settled fct rows; `seg` = {dim: core.segment_rates(dim)}; `pareto` = cause_summary();
    `worst` = worst_week('last'); `truth` = labels (None if absent). Returns (doc, tables)."""
    tests = rca.all_tests(seg, fct, late_days=late_days, high_risk=high_risk)
    glm_table, dropped = glm.fit_glm(fct, min_cell=glm_min_cell)
    truth_table = (checks.truth_scores(fct, truth) if truth is not None
                   else pd.DataFrame(columns=checks.TRUTH_COLUMNS))
    tables = {name: tests[tests["question"].isin(qs)] for name, qs in QUESTION_TABLES.items()}
    tables |= {"q5_signatures": signature_table(fct), "glm": glm_table, "truth_check": truth_table,
               "sensitivity": checks.sensitivity(fct, sensitivity_pcts, large_usd),
               "cause_pareto": pareto}
    summary = summarize(fct, pareto, worst, truth_table, dropped)
    return build_findings(tests, summary, as_of), tables
