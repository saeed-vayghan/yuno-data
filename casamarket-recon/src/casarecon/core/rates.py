"""Rate helpers for core queries (pure, stdlib only): Wilson interval, peer rates, excess loss."""

import math

import pandas as pd

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson 95% interval for k of n (same as statsmodels method='wilson'). n == 0 -> (0, 0)."""
    if n <= 0:
        return 0.0, 0.0
    p, z2 = k / n, z * z
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def peer_group(segment_type: str, value: str) -> str:
    """Peer rule: PSP x country -> other PSPs in the same country; otherwise all other segments."""
    return value.split("|")[1] if segment_type == "psp_country" else "all"


def with_peers(seg: pd.DataFrame) -> pd.DataFrame:
    """Add ci_low, ci_high, peer_rate, lift to a frame with segment_type, segment_value, n, n_flagged."""
    groups = [peer_group(t, v) for t, v in zip(seg.segment_type, seg.segment_value, strict=True)]
    keys = [seg.segment_type, pd.Series(groups, index=seg.index)]
    peer_n = seg.groupby(keys)["n"].transform("sum") - seg.n
    peer_k = seg.groupby(keys)["n_flagged"].transform("sum") - seg.n_flagged
    ci = [wilson(int(k), int(n)) for k, n in zip(seg.n_flagged, seg.n, strict=True)]
    out = seg.assign(ci_low=[c[0] for c in ci], ci_high=[c[1] for c in ci],
                     peer_rate=(peer_k / peer_n.where(peer_n > 0)).astype(float))
    return out.assign(lift=(out.rate / out.peer_rate.where(out.peer_rate > 0)).astype(float))


def excess_usd(rate: float, peer_rate: float, n: int, mean_loss: float) -> float:
    """max(rate - peer_rate, 0) x n x mean loss; 0 when the peer rate is unknown."""
    if math.isnan(peer_rate):
        return 0.0
    return round(max(rate - peer_rate, 0.0) * n * mean_loss, 2)
