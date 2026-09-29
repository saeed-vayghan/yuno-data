"""Arrival data-quality checks (pure): freshness, volume, schema drift, quarantine.

Input = one row per landing file: psp, date (datetime.date), rows, settled, columns (contract names).
Volume uses settled rows: pending rows sit on their auth day, so the last days before as_of
would always look high.
Each check returns rows {check, psp, status, value, threshold, detail}. FAIL = hard (exit 5).
"""

from datetime import date, timedelta

import pandas as pd


def _row(check: str, psp: str, status: str, value, threshold, detail: str = "") -> dict:
    return {"check": check, "psp": psp, "status": status, "value": value, "threshold": threshold,
            "detail": detail}


def freshness(files: pd.DataFrame, psps: list[str], as_of: date, max_days: int) -> list[dict]:
    """Latest file per PSP must be at most max_days before as_of. A PSP with no file fails."""
    latest = files.groupby("psp")["date"].max().to_dict() if len(files) else {}
    out = []
    for psp in psps:
        if psp not in latest:
            out.append(_row("freshness", psp, "FAIL", None, max_days, "no file"))
            continue
        lag = (as_of - latest[psp]).days
        out.append(_row("freshness", psp, "FAIL" if lag > max_days else "PASS", lag, max_days,
                        f"latest {latest[psp]}"))
    return out


def daily_volume(files: pd.DataFrame, psp: str, as_of: date) -> pd.Series:
    """Settled rows per day for one PSP from its first file to as_of; a missing day counts 0."""
    one = files[files["psp"] == psp].groupby("date")["settled"].sum()
    days = [one.index.min() + timedelta(days=i) for i in range((as_of - one.index.min()).days + 1)]
    return one.reindex(days, fill_value=0)


def volume_flags(daily: pd.Series, window: int, warmup: int, tol: float) -> pd.DataFrame:
    """Days (after `warmup` days) where rows / median(previous `window` days) is off by more than tol."""
    median = daily.shift(1).rolling(window, min_periods=window).median()
    median.iloc[:warmup] = float("nan")
    ratio = daily / median
    flagged = median.notna() & ((ratio - 1).abs() > tol)
    return pd.DataFrame({"rows": daily, "median": median, "ratio": ratio.round(2)})[flagged]


def volume(files: pd.DataFrame, psps: list[str], as_of: date, cfg: dict) -> list[dict]:
    out = []
    for psp in psps:
        if not (files["psp"] == psp).any():
            continue
        flags = volume_flags(daily_volume(files, psp, as_of), cfg["volume_window_days"],
                             cfg["volume_warmup_days"], cfg["volume_tolerance"])
        detail = ", ".join(f"{d} {int(r['rows'])} vs {r['median']:.0f}" for d, r in flags.head(5).iterrows())
        out.append(_row("volume", psp, "WARN" if len(flags) else "PASS", len(flags),
                        f"±{cfg['volume_tolerance']:.0%}", detail))
    return out


def drift(files: pd.DataFrame, psps: list[str], expected: list[str]) -> list[dict]:
    """New or missing columns (after the PSP's rename map) vs the contract, over all files of a PSP."""
    out = []
    for psp in psps:
        cols = files.loc[files["psp"] == psp, "columns"]
        if cols.empty:
            continue
        new = sorted({c for cs in cols for c in cs} - set(expected))
        missing = sorted({c for cs in cols for c in set(expected) - set(cs)})
        n_bad = int(sum(bool(set(cs) ^ set(expected)) for cs in cols))
        detail = "; ".join(p for p in (f"new: {', '.join(new)}" if new else "",
                                       f"missing: {', '.join(missing)}" if missing else "") if p)
        out.append(_row("schema_drift", psp, "WARN" if n_bad else "PASS", n_bad, 0, detail))
    return out


def quarantine(n_files: int) -> list[dict]:
    return [_row("quarantine", "*", "WARN" if n_files else "PASS", n_files, 0,
                 "see data/lake/quarantine/*/reason.json" if n_files else "")]


def overall(rows: list[dict]) -> str:
    statuses = {r["status"] for r in rows}
    return "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
