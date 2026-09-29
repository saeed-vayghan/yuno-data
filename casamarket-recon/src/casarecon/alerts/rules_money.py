"""Money rules: money_leak, large_rows, pending_aging. Pure: (RuleInput, cfg, week) -> alert dicts."""

from casarecon.alerts.record import RuleInput, insufficient, record, seg_of, usd


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


def pending_aging(data: RuleInput, cfg: dict, week: str) -> list[dict]:
    """PSP x country oldest pending age vs as_of: > warn_days SEV3, > crit_days SEV2.
    Segments with < min_n pending rows are INSUFFICIENT_DATA (so a 500-row smoke run never fires)."""
    out = []
    for r in data.pending.itertuples():
        age, seg = float(r.oldest_age_days), seg_of(r.psp, r.country)
        if r.n < data.min_n:
            out.append(insufficient(cfg, week, seg, r.n, data.min_n, psp=r.psp, country=r.country))
            continue
        if age <= cfg["warn_days"]:
            continue
        crit = age > cfg["crit_days"]
        out.append(record(cfg, week, seg, psp=r.psp, country=r.country,
                          severity="SEV2" if crit else "SEV3", n=r.n, value=age,
                          threshold=cfg["crit_days"] if crit else cfg["warn_days"],
                          message=f"{r.n} pending rows in {r.psp} {r.country} ({usd(r.amount_usd)}); "
                                  f"oldest is {age:.1f} days old."))
    return out
