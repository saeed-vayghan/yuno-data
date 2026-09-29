"""Tiny hand-countable fct table in a tmp DuckDB, shaped like dbt's marts.fct_transaction_discrepancy.

as_of = 2026-06-30 12:00 -> last closed week 2026-W25 (Jun 15-21), previous 2026-W24.
Imported by test_ui_q.py / test_alerts_run.py (`minidb` fixture).
"""

from datetime import datetime

import duckdb
import pandas as pd
import pytest

from casarecon.adapters.duckdb_store import DuckDbStore

# id, auth_ts, psp, country, status, category, likely_cause, residual_usd, lag_days
ROWS = [
    ("t_may", "2026-05-01 10:00", "PSP_D", "CL", "settled", "exact", None, 0.0, 1),
    ("t24a", "2026-06-08 12:00", "PSP_A", "MX", "settled", "exact", None, 0.0, 1),
    ("t24b", "2026-06-09 12:00", "PSP_A", "MX", "settled", "large", "psp_fee", -40.0, 2),
    ("t25a", "2026-06-15 12:00", "PSP_A", "MX", "settled", "exact", None, 0.0, 1),
    ("t25b", "2026-06-16 12:00", "PSP_A", "MX", "settled", "meaningful", "psp_adjustment", -5.0, 1),
    ("t25c", "2026-06-17 12:00", "PSP_A", "MX", "settled", "large", "psp_fee", -30.0, 9),
    ("t25d", "2026-06-18 12:00", "PSP_A", "MX", "settled", "large", "tip", 25.0, 1),
    ("t25e", "2026-06-19 12:00", "PSP_B", "AR", "settled", "exact", None, 0.0, 1),
    ("t25f", "2026-06-20 12:00", "PSP_B", "AR", "settled", "fx_tolerance", "fx_timing", -0.5, 1),
    ("t26a", "2026-06-23 12:00", "PSP_A", "MX", "settled", "meaningful", "unexplained", -3.0, 1),
    ("t26p", "2026-06-25 12:00", "PSP_A", "MX", "pending", None, None, None, None),
    ("t24p", "2026-06-10 12:00", "PSP_C", "CO", "pending", None, None, None, None),
    ("t26x", "2026-06-24 12:00", "PSP_E", "CO", "failed", None, None, None, None),
    ("t27a", "2026-06-29 12:00", "PSP_B", "AR", "settled", "exact", None, 0.0, 1),
]
AS_OF = datetime(2026, 6, 30, 12)

_DERIVED = """
create schema marts;
create table marts.fct_transaction_discrepancy as
select *,
  'cus_8f2a91c0' || right(transaction_id, 4) as customer_id,
  auth_ts::date as auth_date, strftime(auth_ts, '%G-W%V') as auth_week,
  date_trunc('week', auth_ts)::date as week_start, strftime(auth_ts, '%Y-%m') as auth_month,
  strftime(auth_ts, '%a') as auth_weekday, isodow(auth_ts) in (6, 7) as is_weekend,
  auth_ts + to_seconds(cast(lag_days * 86400 as bigint)) as settle_ts,
  lag_days::double as settle_lag_days, lag_days > 7 as is_lag_outlier,
  abs(residual_usd) as abs_residual_usd,
  case when residual_usd < 0 then 'under' when residual_usd > 0 then 'over'
       when residual_usd = 0 then 'none' end as direction,
  'MXN' as currency, 2 as exponent, '50-200' as amount_tier, false as is_cross_border,
  null::varchar as why_flagged, 10000 as authorized_amount, 10000 as expected_settled,
  (10000 + residual_usd * 20)::bigint as settled_amount, (residual_usd * 20)::bigint as diff_local,
  residual_usd / 5 as residual_pct, 20.0 as fx_auth, 20.0 as fx_settle, 0.0 as fx_move_pct,
  100.0 as amount_usd, 100.0 + residual_usd as settled_usd, 1 as item_count, 0.1 as risk_score,
  false as rounding_flag
from base;
-- status() reads provisional weeks (M4 restatement window) from the weekly mart: none here.
create table marts.mart_psp_weekly as
select distinct auth_week, false as is_provisional from marts.fct_transaction_discrepancy;
"""


def build_minidb(path, rows=ROWS) -> DuckDbStore:
    base = pd.DataFrame(rows, columns=["transaction_id", "auth_ts", "psp", "country", "status",
                                       "category", "likely_cause", "residual_usd", "lag_days"])
    base["auth_ts"] = pd.to_datetime(base["auth_ts"])
    base = base.astype({"residual_usd": "float64", "lag_days": "float64",
                        "category": "object", "likely_cause": "object"})
    con = duckdb.connect(str(path))
    con.register("base", base)
    con.execute(_DERIVED)
    con.close()
    return DuckDbStore(path)


@pytest.fixture
def minidb(tmp_path) -> DuckDbStore:
    return build_minidb(tmp_path / "mini.duckdb")

