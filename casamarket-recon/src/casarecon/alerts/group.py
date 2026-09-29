"""Collapse peer alerts: one PSP high in many countries = one PSP-wide alert. Pure."""

from casarecon.alerts.record import FIRING, pct, record


def _gap_pts(r: dict, min_gap_pts: float) -> float:
    """peer record: value = rate, threshold = peer rate + min gap."""
    return (r["value"] - (r["threshold"] - min_gap_pts / 100)) * 100


def _merge(cfg: dict, week: str, psp: str, rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda r: r["country"])
    n = sum(r["n"] for r in rows)
    parts = ", ".join(f"{r['country']} {pct(r['value'])} (+{_gap_pts(r, cfg['min_gap_pts']):.1f} pts)"
                      for r in rows)
    return record(cfg, week, f"{psp}|ALL", psp=psp, n=n,
                  value=sum(r["value"] * r["n"] for r in rows) / n,
                  threshold=min(r["threshold"] for r in rows),
                  message=f"{psp} flags more than other PSPs in {len(rows)} countries: {parts}. "
                          "Same PSP everywhere points to a PSP-side cause (fee, rounding, policy).")


def group_peers(rows: list[dict], cfg: dict, week: str) -> list[dict]:
    """If a PSP fires in >= group_min_countries countries, replace those rows with one alert."""
    k = cfg.get("group_min_countries", 3)
    by_psp: dict[str, list[dict]] = {}
    for r in rows:
        if r["status"] == FIRING:
            by_psp.setdefault(r["psp"], []).append(r)
    grouped = {p for p, rs in by_psp.items() if len(rs) >= k}
    kept = [r for r in rows if not (r["status"] == FIRING and r["psp"] in grouped)]
    return kept + [_merge(cfg, week, p, by_psp[p]) for p in sorted(grouped)]
