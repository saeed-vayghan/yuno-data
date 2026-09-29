"""Root-cause tests, one function per brief question (pure). Every function returns a *test table*
(see segments.py); `all_tests` stacks them and runs BH once over every p-value.

Rows with a `key` are finding candidates (findings.py); the rest answer the brief questions only.
"""

import numpy as np
import pandas as pd

from casarecon.analysis import causes, stats
from casarecon.analysis.segments import compare_to_peers, is_true, top_causes, two_group

COLUMNS = ["question", "key", "kind", "segment_type", "segment_value", "psp", "country", "likely_cause",
           "metric", "n", "n_flagged", "rate", "ci_low", "ci_high", "peer_n", "peer_rate", "lift", "p",
           "q", "excess_usd", "mean_loss_usd", "median_loss_usd", "usd_note"]


def _keyed(t: pd.DataFrame, key: str, fct: pd.DataFrame, col: str) -> pd.DataFrame:
    """Mark the 'true' row of a boolean segment as finding `key`, with its top cause."""
    hit = t["segment_value"].map(is_true)
    return t.assign(key=np.where(hit, key, None), kind=np.where(hit, key, None),
                    likely_cause=t["segment_value"].map(top_causes(fct, col)).where(hit))


def q1_geo(seg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Q1 countries and currencies: each vs the rest."""
    return pd.concat([compare_to_peers(seg["country"]), compare_to_peers(seg["currency"])])


def q2_psp_country(seg: dict[str, pd.DataFrame], fct: pd.DataFrame) -> pd.DataFrame:
    """Q2 PSP x country vs the other PSPs in the same country (peer rule)."""
    t = compare_to_peers(seg["psp_country"], group=lambda v: v.split("|")[1])
    parts = t["segment_value"].str.split("|", expand=True)
    return t.assign(psp=parts[0], country=parts[1], kind="peer",
                    key=(parts[0] + "_" + parts[1] + "_peer").str.lower(),
                    likely_cause=t["segment_value"].map(top_causes(fct, ["psp", "country"])))


def q3_size(seg: dict[str, pd.DataFrame], fct: pd.DataFrame) -> pd.DataFrame:
    """Q3 rate by amount tier; Spearman of |residual_pct| vs amount_usd on non-exact rows."""
    nx = fct[fct["category"].notna() & (fct["category"] != "exact")]
    rho, p = stats.spearman(nx["amount_usd"].tolist(), nx["residual_pct"].abs().tolist())
    rho_row = {"segment_type": "size_vs_magnitude", "segment_value": "spearman", "n": len(nx),
               "metric": "spearman rho", "rate": rho, "p": p}
    return pd.concat([compare_to_peers(seg["amount_tier"]), pd.DataFrame([rho_row])])


def lag_tests(fct: pd.DataFrame, late_days: float) -> pd.DataFrame:
    """P2-style test per country: orders over $300 vs the rest of that country on settle lag.
    Metric = late share (lag > late_days); p = one-sided Mann-Whitney; $ = flag-rate excess."""
    rows = []
    for country, d in fct.groupby("country", sort=True):
        big = d["is_over_300"].fillna(False).astype(bool)
        if big.all() or not big.any():
            continue
        late = d["settle_lag_days"] > late_days
        row = two_group(d[big], d[~big], late, segment_type="lag_over_300",
                        segment_value=f"{country}|over_300", key=f"{country.lower()}_over_300_lag",
                        kind="lag", country=country, metric="late share", usd_note="delay, not loss")
        money = two_group(d[big], d[~big])
        row |= {k: money[k] for k in ("excess_usd", "mean_loss_usd", "median_loss_usd")}
        row["p"] = stats.mann_whitney(d.loc[big, "settle_lag_days"].tolist(),
                                      d.loc[~big, "settle_lag_days"].tolist(), "greater")
        rows.append(row)
    return pd.DataFrame(rows)


def q4_time(seg: dict[str, pd.DataFrame], fct: pd.DataFrame, late_days: float) -> pd.DataFrame:
    """Q4 weekend vs weekday, rate by lag bucket, over-$300 lag per country."""
    weekend = _keyed(compare_to_peers(seg["is_weekend"]), "weekend", fct, "is_weekend")
    return pd.concat([weekend, compare_to_peers(seg["lag_bucket"]), lag_tests(fct, late_days)])


def q6_other(seg: dict[str, pd.DataFrame], fct: pd.DataFrame) -> pd.DataFrame:
    """Brief example: cross-border vs domestic."""
    return _keyed(compare_to_peers(seg["cross_border"]), "cross_border", fct, "is_cross_border")


def all_tests(seg: dict[str, pd.DataFrame], fct: pd.DataFrame, *, late_days: float,
              high_risk: float) -> pd.DataFrame:
    """Every test, one table, `q` from a single BH run over all p-values."""
    parts = {"Q1": q1_geo(seg), "Q2": q2_psp_country(seg, fct), "Q3": q3_size(seg, fct),
             "Q4": q4_time(seg, fct, late_days), "Q5": causes.q5_cause_psp(fct),
             "Q6": pd.concat([q6_other(seg, fct), causes.other_tests(fct, high_risk)])}
    t = pd.concat([p.assign(question=q) for q, p in parts.items()], ignore_index=True)
    t = t.reindex(columns=COLUMNS)
    t["q"] = stats.bh(t["p"].astype(float).tolist())
    return t
