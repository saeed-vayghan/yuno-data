"""Rate rules: peer, change, settle_lag. Pure: (RuleInput, rule cfg, week) -> list of alert dicts."""

import math

import pandas as pd

from casarecon.alerts.record import RuleInput, insufficient, pct, record, seg_of, trailing
from casarecon.alerts.stats import bh, two_prop_p, wilson
from casarecon.core.queries.ui_q_base import prev_week


def _window(data: RuleInput, weeks: list[str]) -> pd.DataFrame:
    return data.frame[data.frame["auth_week"].isin(weeks)]


def peer(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """PSP x country flag rate (trailing weeks) vs other PSPs in the same country; BH q + gap."""
    g = (_window(data, trailing(week, cfg["window_weeks"]))
         .groupby(["psp", "country"], as_index=False)[["n", "n_flagged"]].sum())
    tot = g.groupby("country")[["n", "n_flagged"]].transform("sum")
    g = g.assign(peer_n=tot["n"] - g["n"], peer_k=tot["n_flagged"] - g["n_flagged"])
    ok = (g["n"] >= data.min_n) & (g["peer_n"] >= data.min_n)
    out = [insufficient(cfg, week, seg_of(r.psp, r.country), r.n, data.min_n, psp=r.psp,
                        country=r.country) for r in g[~ok].itertuples()]
    big = g[ok].reset_index(drop=True)
    qs = bh([two_prop_p(r.n_flagged, r.n, r.peer_k, r.peer_n) for r in big.itertuples()])
    for r, q in zip(big.itertuples(), qs):
        rate, peer_rate = r.n_flagged / r.n, r.peer_k / r.peer_n
        gap = rate - peer_rate
        if q < cfg["q_max"] and gap * 100 >= cfg["min_gap_pts"]:
            lo, hi = wilson(r.n_flagged, r.n)
            qtxt = "q < 0.001" if q < 0.001 else f"q = {q:.3f}"
            out.append(record(
                cfg, week, seg_of(r.psp, r.country), psp=r.psp, country=r.country, n=r.n,
                value=rate, threshold=peer_rate + cfg["min_gap_pts"] / 100,
                message=f"{r.psp} flags {pct(rate)} of {r.country} rows vs {pct(peer_rate)} for "
                        f"other PSPs (+{gap * 100:.1f} pts, {qtxt}; 95% CI {pct(lo)}-{pct(hi)})."))
    return out


def change(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """p-chart: weekly flag rate above p_bar + sigma*sqrt(p_bar(1-p_bar)/n), p_bar = prior weeks."""
    base_weeks = trailing(prev_week(week), cfg["window_weeks"])
    f = data.frame
    long = pd.concat([f.assign(psp=None, country=None, segment="ALL"),
                      f.assign(segment=f["psp"] + "|" + f["country"])])
    out = []
    for seg, s in long.groupby("segment", sort=True):
        cur, base = s[s["auth_week"] == week], s[s["auth_week"].isin(base_weeks)]
        n, k = int(cur["n"].sum()), int(cur["n_flagged"].sum())
        who = {k: (v if isinstance(v, str) else None)
               for k, v in (("psp", s["psp"].iloc[0]), ("country", s["country"].iloc[0]))}
        full_base = base.loc[base["n"] > 0, "auth_week"].nunique() >= cfg["window_weeks"]
        if n < data.min_n or not full_base:
            out.append(insufficient(cfg, week, seg, n, data.min_n, **who))
            continue
        p_bar = base["n_flagged"].sum() / base["n"].sum()
        ucl = p_bar + cfg["sigma"] * math.sqrt(p_bar * (1 - p_bar) / n)
        if k / n > ucl:
            out.append(record(cfg, week, seg, n=n, value=k / n, threshold=ucl, **who,
                              message=f"{seg} flag rate {pct(k / n)} in {week} is above the "
                                      f"control limit {pct(ucl)} (baseline {pct(p_bar)})."))
    return out


def settle_lag(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """Country x amount tier late share (settled lag or pending age > late_days), trailing weeks."""
    g = (_window(data, trailing(week, cfg["window_weeks"]))
         .groupby(["country", "amount_tier"], as_index=False)[["n", "n_open", "n_late"]].sum())
    out = []
    for r in g.itertuples():
        seg, den = f"{r.country}|{r.amount_tier}", r.n + r.n_open
        if den < data.min_n:
            out.append(insufficient(cfg, week, seg, den, data.min_n, country=r.country))
        elif r.n_late / den > cfg["max_late_share"]:
            out.append(record(cfg, week, seg, country=r.country, n=den, value=r.n_late / den,
                              threshold=cfg["max_late_share"],
                              message=f"{pct(r.n_late / den)} of {seg} rows settle after "
                                      f"{cfg['late_days']} days (limit {pct(cfg['max_late_share'])})."))
    return out
