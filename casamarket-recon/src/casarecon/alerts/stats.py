"""Tiny stdlib stats for the rules: one-sided two-proportion z-test, Benjamini-Hochberg, Wilson CI."""

import math


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """One-sided p-value that rate1 > rate2 (pooled z-test). 1.0 when undefined."""
    if min(n1, n2) == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return 0.5 * math.erfc(z / math.sqrt(2))


def bh(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values, same order as the input."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    q, running = [0.0] * m, 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * m / rank)
        q[i] = running
    return q


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k / n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))
