"""Overview rows #13 kpis, #14 weekly_trend, #15 week_over_week (BACKEND). Re-exported by ui_q."""

import pandas as pd

from casarecon.core.errors import BadFilter
from casarecon.core.filters import WEEK_RE, Filters
from casarecon.core.queries.ui_q_base import (
    AGG, FCT, SETTLED, as_of, is_closed, last_closed_week, min_sample, prev_week, store_of, where,
    with_rates,
)
from casarecon.ports import Store

TREND_COLS = ["auth_week", "week_start", "series", "n", "n_flagged", "rate", "net_usd",
              "gross_under_usd", "is_closed", "low_sample"]
WOW_COLS = ["psp", "country", "week_prev", "week_last", "rate_prev", "rate_last", "delta_pts",
            "n_prev", "n_last", "low_sample"]
_ZERO = pd.Series({"n": 0, "n_flagged": 0, "n_large": 0, "rate": 0.0, "net_usd": 0.0,
                   "gross_under_usd": 0.0})


def _kpi(row: pd.Series) -> dict:
    rate = 0.0 if pd.isna(row["rate"]) else float(row["rate"])
    return {"n": int(row["n"]), "n_flagged": int(row["n_flagged"]), "n_large": int(row["n_large"]),
            "flag_rate": rate, "net_usd": float(row["net_usd"]),
            "gross_under_usd": float(row["gross_under_usd"])}


def _resolve_week(week: str, store: Store) -> str | None:
    if week == "last_closed":
        a = as_of(store)
        return None if a is None else last_closed_week(a)
    if not WEEK_RE.match(week):
        raise BadFilter(f"bad week: {week} (expected 'last_closed', 'all' or YYYY-Www)")
    return week


def kpis(filters: Filters | None = None, week: str = "last_closed", *,
         store: Store | None = None) -> dict:
    s = store_of(store)
    cond, params = where(filters)
    if week == "all":
        df = s.query(f"select {AGG} from {FCT} where {SETTLED}{cond}", params)
        return _kpi(with_rates(df).iloc[0])
    wk = _resolve_week(week, s)
    prev = prev_week(wk) if wk else None
    df = with_rates(s.query(
        f"select auth_week, {AGG} from {FCT} where {SETTLED}{cond} and auth_week in (?, ?) "
        "group by auth_week", [*params, wk, prev])).set_index("auth_week")
    cur, old = (_kpi(df.loc[w]) if w in df.index else _kpi(_ZERO) for w in (wk, prev))
    return {**cur, "week": wk, "prev_week": prev,
            "delta_rate_pts": round((cur["flag_rate"] - old["flag_rate"]) * 100, 4),
            "delta_net_usd": round(cur["net_usd"] - old["net_usd"], 2),
            "delta_n_large": cur["n_large"] - old["n_large"]}


def weekly_trend(filters: Filters | None = None, by: str = "portfolio", *,
                 store: Store | None = None) -> pd.DataFrame:
    if by not in ("portfolio", "psp"):
        raise BadFilter(f"unknown by: {by} (allowed: portfolio, psp)")
    s = store_of(store)
    cond, params = where(filters)
    series = "psp" if by == "psp" else "'ALL'"
    df = with_rates(s.query(
        f"select auth_week, week_start, {series} as series, {AGG} from {FCT} "
        f"where {SETTLED}{cond} group by all order by week_start, series", params))
    df["week_start"] = pd.to_datetime(df["week_start"]).dt.date
    a = as_of(s)
    df["is_closed"] = [a is not None and is_closed(ws, a) for ws in df["week_start"]]
    df["low_sample"] = df["n"] < min_sample()
    return df[TREND_COLS].reset_index(drop=True)


def week_over_week(filters: Filters | None = None, *, store: Store | None = None) -> pd.DataFrame:
    s = store_of(store)
    a = as_of(s)
    if a is None:
        return pd.DataFrame(columns=WOW_COLS)
    last = last_closed_week(a)
    prev = prev_week(last)
    cond, params = where(filters)
    df = with_rates(s.query(
        f"select psp, country, auth_week, {AGG} from {FCT} where {SETTLED}{cond} "
        "and auth_week in (?, ?) group by all", [*params, last, prev]))
    keep = ["psp", "country", "n", "rate"]
    cur = df[df["auth_week"] == last][keep].rename(columns={"n": "n_last", "rate": "rate_last"})
    old = df[df["auth_week"] == prev][keep].rename(columns={"n": "n_prev", "rate": "rate_prev"})
    out = cur.merge(old, on=["psp", "country"], how="outer")
    out[["n_last", "n_prev"]] = out[["n_last", "n_prev"]].fillna(0).astype(int)
    out = out.assign(week_prev=prev, week_last=last,
                     delta_pts=((out["rate_last"] - out["rate_prev"]) * 100).round(4),
                     low_sample=out[["n_last", "n_prev"]].min(axis=1) < min_sample())
    out = out.sort_values(["delta_pts", "psp", "country"], ascending=[False, True, True],
                          na_position="last")
    return out[WOW_COLS].reset_index(drop=True)
