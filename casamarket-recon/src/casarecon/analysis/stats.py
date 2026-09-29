"""Pure statistics helpers. No I/O. Wilson comes from `core.rates` (pure, stdlib) so there is one copy."""

import math
from collections.abc import Sequence

from scipy.stats import chi2_contingency, fisher_exact, mannwhitneyu, spearmanr
from statsmodels.stats.multitest import multipletests

from casarecon.core import rates as core_rates


def wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson 95% interval for k successes out of n. n == 0 -> (0.0, 0.0).
    One implementation for core and analysis: delegates to `core.rates.wilson` (stdlib, pure)."""
    return core_rates.wilson(int(k), int(n))


def lift(rate: float, peer_rate: float) -> float:
    """rate / peer_rate; NaN when the peer rate is 0 or unknown."""
    if not peer_rate or math.isnan(peer_rate):
        return math.nan
    return rate / peer_rate


def rate_test(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value for rate k1/n1 vs k2/n2: chi-square, Fisher if any expected cell < 5."""
    if min(n1, n2) <= 0 or k1 + k2 in (0, n1 + n2):
        return 1.0
    table = [[k1, n1 - k1], [k2, n2 - k2]]
    _, p, _, expected = chi2_contingency(table)
    if (expected < 5).any():
        return float(fisher_exact(table)[1])
    return float(p)


def bh(pvals: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg q-values in input order. NaN p-values stay NaN and are not counted."""
    idx = [i for i, p in enumerate(pvals) if p is not None and not math.isnan(p)]
    out = [math.nan] * len(pvals)
    if idx:
        qs = multipletests([pvals[i] for i in idx], method="fdr_bh")[1]
        for i, q in zip(idx, qs, strict=True):
            out[i] = float(q)
    return out


def spearman(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """(rho, p). Fewer than 3 points -> (NaN, 1.0)."""
    if len(x) < 3:
        return math.nan, 1.0
    res = spearmanr(x, y)
    return float(res.statistic), float(res.pvalue)


def mann_whitney(a: Sequence[float], b: Sequence[float], alternative: str = "two-sided") -> float:
    """Mann-Whitney U p-value; 1.0 if either group is empty."""
    if len(a) == 0 or len(b) == 0:
        return 1.0
    return float(mannwhitneyu(a, b, alternative=alternative).pvalue)


def excess_loss(rate: float, peer_rate: float, n: int, mean_loss: float) -> float:
    """Loss above the peer rate: max(rate - peer_rate, 0) * n * mean_loss. Never negative."""
    if any(math.isnan(v) for v in (rate, peer_rate, mean_loss)):
        return 0.0
    return max(rate - peer_rate, 0.0) * n * max(mean_loss, 0.0)
