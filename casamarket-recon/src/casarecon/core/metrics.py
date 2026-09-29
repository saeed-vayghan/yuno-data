"""The one place for metric definitions (pure, stdlib only). Owner: ALERTS.

Python functions for code that has numbers, SQL fragments for queries that aggregate in DuckDB.
Both say the same thing; change a definition here and every caller follows.

- flag rate   = flagged settled rows / settled rows (flagged = category meaningful or large)
- gross under = sum of max(-residual_usd, 0) (PSP paid us less); gross over = max(residual_usd, 0)
- net loss    = gross under - gross over (positive = we lost money)
- leak share  = 100 x gross under / settled USD (percent of settled volume)
- excess loss = max(rate - peer_rate, 0) x n x mean loss (loss above what peers would lose)
"""

import math
from collections.abc import Sequence

Z95 = 1.959963984540054
FLAGGED_CATEGORIES = ("meaningful", "large")

# SQL fragments (column names of marts.fct_transaction_discrepancy). No user values inside.
SETTLED_SQL = "status = 'settled'"
FLAGGED_SQL = "category in ('meaningful', 'large')"
LARGE_SQL = "category = 'large'"
UNDER_SQL = "greatest(-residual_usd, 0)"
OVER_SQL = "greatest(residual_usd, 0)"
# One aggregate block (count, flagged, large, gross under / over) for settled-row queries.
AGG_SQL = f"""count(*) as n,
  count(*) filter (where {FLAGGED_SQL}) as n_flagged,
  count(*) filter (where {LARGE_SQL}) as n_large,
  round(coalesce(sum({UNDER_SQL}), 0), 2) as gross_under_usd,
  round(coalesce(sum({OVER_SQL}), 0), 2) as gross_over_usd"""


def is_flagged(category: str | None) -> bool:
    return category in FLAGGED_CATEGORIES


def flag_rate(n_flagged: int, n: int, empty: float = math.nan) -> float:
    """n_flagged / n; `empty` (default NaN) when n = 0."""
    return n_flagged / n if n > 0 else empty


def gross_under(residual_usd: float) -> float:
    return max(-residual_usd, 0.0)


def gross_over(residual_usd: float) -> float:
    return max(residual_usd, 0.0)


def net_loss(under_usd: float, over_usd: float) -> float:
    """Gross under minus gross over, rounded to cents (positive = money lost)."""
    return round(under_usd - over_usd, 2)


def leak_share_pct(under_usd: float, settled_usd: float) -> float:
    """Under-settled USD as a percent of settled USD; 0 when nothing settled."""
    return 100 * under_usd / settled_usd if settled_usd else 0.0


def excess_loss(rate: float, peer_rate: float, n: int, mean_loss: float) -> float:
    """max(rate - peer_rate, 0) x n x max(mean_loss, 0); 0 when any input is NaN."""
    if any(math.isnan(v) for v in (rate, peer_rate, mean_loss)):
        return 0.0
    return max(rate - peer_rate, 0.0) * n * max(mean_loss, 0.0)


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson 95% interval for k of n (same as statsmodels method='wilson'). n == 0 -> (0, 0)."""
    if n <= 0:
        return 0.0, 0.0
    p, z2 = k / n, z * z
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """One-sided p-value that rate1 > rate2 (pooled z-test). 1.0 when undefined."""
    if min(n1, n2) == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    return 0.5 * math.erfc((k1 / n1 - k2 / n2) / se / math.sqrt(2))


def bh(pvalues: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg q-values in input order. NaN p-values stay NaN and are not counted."""
    idx = [i for i, p in enumerate(pvalues) if p is not None and not math.isnan(p)]
    q, running, m = [math.nan] * len(pvalues), 1.0, len(idx)
    for rank, i in reversed(list(enumerate(sorted(idx, key=lambda j: pvalues[j]), start=1))):
        running = min(running, pvalues[i] * m / rank)
        q[i] = running
    return q
