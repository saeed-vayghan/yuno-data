"""The one logistic GLM (pure): flag ~ PSP x country + tier + cross-border + weekend + lag bucket.

Lag is also an outcome (P2), so its coefficient is a link, not a cause.
"""

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.tools.sm_exceptions import ConvergenceWarning, PerfectSeparationWarning

FORMULA = ("flag ~ C(psp) * C(country) + C(amount_tier) + is_cross_border + is_weekend"
           " + C(lag_bucket)")
MIN_CELL = 200
GLM_COLUMNS = ["term", "odds_ratio", "or_ci_low", "or_ci_high", "p"]


def _prepare(fct: pd.DataFrame) -> pd.DataFrame:
    return fct.assign(flag=fct["is_meaningful"].fillna(False).astype(int),
                      is_cross_border=fct["is_cross_border"].astype(int),
                      is_weekend=fct["is_weekend"].astype(int))


def _fit(df: pd.DataFrame) -> pd.DataFrame:
    """Fit once; raise ValueError on non-convergence or separation."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        warnings.simplefilter("error", PerfectSeparationWarning)
        try:
            res = smf.glm(FORMULA, data=df, family=sm.families.Binomial()).fit()
        except Exception as e:  # separation, singular design, bad formula levels
            raise ValueError(str(e)) from e
    with np.errstate(over="ignore"):  # huge coefficients on tiny cells -> inf odds ratio, not an error
        ci = np.exp(res.conf_int())
        odds = np.exp(res.params.values)
    return pd.DataFrame({"term": res.params.index, "odds_ratio": odds, "or_ci_low": ci[0].values,
                         "or_ci_high": ci[1].values, "p": res.pvalues.values})


def small_cells(df: pd.DataFrame, min_cell: int) -> list[str]:
    """PSP x country cells with fewer than min_cell rows, as 'PSP|CC'."""
    sizes = df.groupby(["psp", "country"]).size()
    return sorted(f"{p}|{c}" for (p, c), n in sizes.items() if n < min_cell)


def fit_glm(fct: pd.DataFrame, min_cell: int = MIN_CELL) -> tuple[pd.DataFrame, list[str]]:
    """Return (odds-ratio table, dropped cells). On failure drop PSP x country cells with
    n < min_cell and refit once; if that fails too, return an empty table and ['all']."""
    df = _prepare(fct)
    try:
        return _fit(df), []
    except ValueError:
        pass
    dropped = small_cells(df, min_cell)
    keep = ~(df["psp"] + "|" + df["country"]).isin(dropped)
    try:
        return _fit(df[keep]), dropped
    except ValueError:
        return pd.DataFrame(columns=GLM_COLUMNS), ["all"]
