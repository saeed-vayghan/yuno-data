"""Small seeded sampling helpers. Every function takes the one shared `rng`; nothing global."""

from datetime import date, datetime, timedelta

import numpy as np


def categorical(rng: np.random.Generator, weights: dict, n: int) -> np.ndarray:
    """n draws of the dict keys, with the dict values as (normalised) probabilities."""
    keys = list(weights)
    p = np.array([weights[k] for k in keys], dtype=float)
    return np.array(keys, dtype=object)[rng.choice(len(keys), size=n, p=p / p.sum())]


def hex_tokens(rng: np.random.Generator, prefix: str, n: int) -> np.ndarray:
    """n unique `prefix + 12 hex` ids (collisions redrawn, still deterministic)."""
    values = rng.integers(0, 2**48, size=n, dtype=np.int64)
    while len(np.unique(values)) < n:
        _, first = np.unique(values, return_index=True)
        dup = np.setdiff1d(np.arange(n), first)
        values[dup] = rng.integers(0, 2**48, size=len(dup), dtype=np.int64)
    return np.array([f"{prefix}{v:012x}" for v in values], dtype=object)


def weighted_pick(rng: np.random.Generator, weights: np.ndarray, k: int) -> np.ndarray:
    """Indices of k items drawn without replacement, P ∝ weight (Efraimidis–Spirakis keys).

    Zero-weight items are never picked; k is capped at the number of positive weights.
    """
    ok = weights > 0
    k = int(min(max(k, 0), ok.sum()))
    keys = np.full(len(weights), -np.inf)
    keys[ok] = np.log(rng.random(ok.sum())) / weights[ok]
    return np.argsort(-keys, kind="stable")[:k]


def window(start: date, months: int) -> tuple[datetime, datetime]:
    """[start 00:00:00, last second of the last full month]. Naive on purpose: merchant local time."""
    y, m = divmod(start.month - 1 + months, 12)
    end = datetime(start.year + y, m + 1, 1) - timedelta(seconds=1)  # noqa: DTZ001
    return datetime(start.year, start.month, start.day), end  # noqa: DTZ001


def half_away(x: np.ndarray, dp: int = 0) -> np.ndarray:
    """Vectorised round half away from zero (DuckDB round()); numpy's round is banker's."""
    scale = 10.0**dp
    return np.sign(x) * np.floor(np.abs(x) * scale + 0.5) / scale
