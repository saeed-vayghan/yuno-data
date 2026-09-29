"""Segment counts and segment-vs-peer tests on pandas DataFrames (pure).

A *segment frame* has the `core.segment_rates` columns we rely on:
`segment_type, segment_value, n, n_flagged, mean_loss_usd, median_loss_usd`.
A *test row* adds `rate, ci_low, ci_high, peer_n, peer_rate, lift, p, excess_usd`.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from casarecon.analysis import stats

# segment_type -> fct column(s); mirrors the dims of core.segment_rates
DIMS: dict[str, str | list[str]] = {
    "country": "country", "currency": "currency", "psp": "psp", "psp_country": ["psp", "country"],
    "amount_tier": "amount_tier", "is_weekend": "is_weekend", "lag_bucket": "lag_bucket",
    "cross_border": "is_cross_border",
}


def label(v: object) -> str:
    """Segment label: booleans -> 'true'/'false' (as in the marts), everything else str()."""
    return str(v).lower() if isinstance(v, bool | np.bool_) else str(v)


def is_true(v: object) -> bool:
    return str(v).strip().lower() in {"true", "t", "1", "yes"}


def rate_frame(df: pd.DataFrame, by: str | list[str], flag: str = "is_meaningful",
               segment_type: str | None = None) -> pd.DataFrame:
    """Count rows per segment. Loss = -residual_usd over flagged rows (mean and median)."""
    cols = [by] if isinstance(by, str) else list(by)
    d = df.assign(_flag=df[flag].fillna(False).astype(bool), _loss=-df["residual_usd"])
    g = d.groupby(cols, sort=True)
    out = pd.DataFrame({"n": g.size(), "n_flagged": g["_flag"].sum().astype(int)})
    loss = d[d["_flag"]].groupby(cols)["_loss"]
    out["mean_loss_usd"] = loss.mean()
    out["median_loss_usd"] = loss.median()
    out = out.fillna({"mean_loss_usd": 0.0, "median_loss_usd": 0.0}).reset_index()
    out["segment_value"] = out[cols].apply(lambda r: "|".join(label(v) for v in r), axis=1)
    out["segment_type"] = segment_type or "_".join(cols)
    return out.drop(columns=cols)


def segments_from_fct(fct: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Pure stand-in for `core.segment_rates(dim)` over all DIMS (used by tests)."""
    return {name: rate_frame(fct, by, segment_type=name) for name, by in DIMS.items()}


TEST_COLS = ("rate", "ci_low", "ci_high", "peer_n", "peer_rate", "lift", "p", "excess_usd")


def _test_values(k: int, n: int, pk: int, pn: int, mean_loss: float) -> dict:
    rate = k / n if n else np.nan
    peer_rate = pk / pn if pn else np.nan
    lo, hi = stats.wilson(k, n)
    return {"rate": rate, "ci_low": lo, "ci_high": hi, "peer_n": pn, "peer_rate": peer_rate,
            "lift": stats.lift(rate, peer_rate), "p": stats.rate_test(k, n, pk, pn),
            "excess_usd": stats.excess_loss(rate, peer_rate, n, mean_loss)}


def compare_to_peers(seg: pd.DataFrame, group: Callable[[str], str] | None = None,
                     metric: str = "flag rate") -> pd.DataFrame:
    """Test each segment against the other segments of its group (default: all other rows).

    `group` maps a segment_value to its peer group, e.g. 'PSP_B|AR' -> 'AR' (peer rule).
    """
    s = seg.reset_index(drop=True).drop(columns=list(TEST_COLS), errors="ignore")
    keys = s["segment_value"].map(group) if group else pd.Series("all", index=s.index)
    tot_n = s.groupby(keys)["n"].transform("sum")
    tot_k = s.groupby(keys)["n_flagged"].transform("sum")
    rows = [_test_values(int(r.n_flagged), int(r.n), int(tk - r.n_flagged), int(tn - r.n),
                         float(r.mean_loss_usd))
            for r, tn, tk in zip(s.itertuples(), tot_n, tot_k, strict=True)]
    return pd.concat([s, pd.DataFrame(rows, index=s.index)], axis=1).assign(metric=metric)


def two_group(a: pd.DataFrame, b: pd.DataFrame, flag: pd.Series | str = "is_meaningful",
              **labels: object) -> dict:
    """One test row: rows `a` (segment) vs rows `b` (peers). `flag` is a column name or a bool
    Series aligned to the union of both frames' index."""
    fa = (a[flag] if isinstance(flag, str) else flag.reindex(a.index)).fillna(False).astype(bool)
    fb = (b[flag] if isinstance(flag, str) else flag.reindex(b.index)).fillna(False).astype(bool)
    loss = -a.loc[fa, "residual_usd"]
    mean_loss = float(loss.mean()) if len(loss) else 0.0
    row = {"n": len(a), "n_flagged": int(fa.sum()), "mean_loss_usd": mean_loss,
           "median_loss_usd": float(loss.median()) if len(loss) else 0.0}
    return {**labels, **row, **_test_values(int(fa.sum()), len(a), int(fb.sum()), len(b), mean_loss)}


def top_causes(fct: pd.DataFrame, by: str | list[str]) -> pd.Series:
    """Most common likely_cause among flagged rows per segment (index = segment_value)."""
    flagged = fct[fct["is_meaningful"].fillna(False).astype(bool) & fct["likely_cause"].notna()]
    if flagged.empty:
        return pd.Series(dtype=object)
    counts = rate_frame(flagged.assign(_one=True), [*([by] if isinstance(by, str) else by),
                                                    "likely_cause"], flag="_one")
    counts[["segment_value", "cause"]] = counts["segment_value"].str.rsplit("|", n=1, expand=True)
    counts = counts.sort_values(["segment_value", "n", "cause"], ascending=[True, False, True])
    return counts.drop_duplicates("segment_value").set_index("segment_value")["cause"]
