"""Money rules: money_leak, large_rows, pending_aging. Pure: (RuleInput, cfg, week) -> alert dicts."""

from casarecon.alerts.record import RuleInput, insufficient, pct, record, seg_of, usd


def money_leak(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """Portfolio under-settled USD / settled USD in `week` (FX residual at auth-day rate)."""
    cur = data.frame[data.frame["auth_week"] == week]
    n = int(cur["n"].sum())
    if n < data.min_n:
        return [insufficient(cfg, week, "ALL", n, data.min_n)]
    under, volume = float(cur["gross_under_usd"].sum()), float(cur["settled_usd"].sum())
    leak = 100 * under / volume if volume else 0.0
    warn, crit = data.money["warn_pct"], data.money["crit_pct"]
    if leak < warn:
        return []
    sev, limit = (cfg["severity_crit"], crit) if leak >= crit else (cfg["severity_warn"], warn)
    return [record(cfg, week, "ALL", severity=sev, n=n, value=leak, threshold=limit,
                   message=f"Under-settled {usd(under)} = {leak:.2f}% of settled USD in {week} "
                           f"(warn {warn}%, crit {crit}%).")]


def large_rows(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """One summary alert when `week` has any `large` rows: count, $ total, top PSP x country."""
    cur = data.frame[data.frame["auth_week"] == week]
    n = int(cur["n"].sum())
    if n < data.min_n:
        return [insufficient(cfg, week, "ALL", n, data.min_n)]
    n_large, total = int(cur["n_large"].sum()), float(cur["large_usd"].sum())
    if n_large == 0:
        return []
    top = (cur.groupby(["psp", "country"], as_index=False)[["n_large", "large_usd"]].sum()
           .query("n_large > 0").sort_values(["large_usd", "psp", "country"],
                                             ascending=[False, True, True]).head(cfg["top_n"]))
    tops = ", ".join(f"{seg_of(r.psp, r.country)} {usd(r.large_usd)}" for r in top.itertuples())
    return [record(cfg, week, "ALL", n=n, value=total, threshold=0.0,
                   message=f"{n_large} large rows ({usd(total)} absolute) in {week}; top: {tops}.")]


PENDING_DEFAULTS = {"age_days": 7, "warn_share": 0.10, "crit_share": 0.25}  # until alerts.yaml has them


def pending_limits(cfg: dict) -> dict:
    return {k: cfg.get(k, v) for k, v in PENDING_DEFAULTS.items()}


def pending_aging(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """PSP x country share of pending rows older than age_days (vs as_of): >= warn_share SEV3,
    >= crit_share SEV2. Measured at as_of over all pending rows; < min_n pending -> INSUFFICIENT_DATA."""
    lim = pending_limits(cfg)
    g = data.frame.groupby(["psp", "country"], as_index=False)[["n_open", "n_open_old"]].sum()
    out = []
    for r in g[g["n_open"] > 0].itertuples():
        seg, share = seg_of(r.psp, r.country), r.n_open_old / r.n_open
        if r.n_open < data.min_n:
            out.append(insufficient(cfg, week, seg, r.n_open, data.min_n, psp=r.psp, country=r.country))
        elif share >= lim["warn_share"]:
            crit = share >= lim["crit_share"]
            out.append(record(cfg, week, seg, psp=r.psp, country=r.country,
                              severity="SEV2" if crit else "SEV3", n=r.n_open, value=share,
                              threshold=lim["crit_share"] if crit else lim["warn_share"],
                              message=f"{pct(share)} of {r.n_open} pending rows in {r.psp} {r.country} "
                                      f"are older than {lim['age_days']} days."))
    return out
