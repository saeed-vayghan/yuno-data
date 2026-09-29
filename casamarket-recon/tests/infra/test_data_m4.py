"""M4 data layer (DATA): incremental == full, dated fee join, provisional weeks. Fixture DB only."""

from datetime import date

import duckdb
import pandas as pd

from casarecon import core
from casarecon.core import weeks
from casarecon.pipeline import build

CUT = "2026-06-10"  # the "earlier" run sees rows authorised by CUT; later settlements are still pending


def _truncate(src: pd.DataFrame) -> pd.DataFrame:
    """What the raw file looked like at CUT: no later rows, later settlements still pending."""
    df = src[src.auth_ts <= CUT].copy()
    late = df.settle_ts.notna() & (df.settle_ts > CUT)
    df.loc[late, ["status", "settle_ts", "settled_amount"]] = ["pending", None, None]
    return df


def _diff(a, b, table: str) -> int:
    with duckdb.connect() as con:
        con.execute(f"attach '{a}' as a (read_only)")
        con.execute(f"attach '{b}' as b (read_only)")
        return con.sql(f"select count(*) from (select * from a.marts.{table} except all "
                       f"select * from b.marts.{table})").fetchone()[0]


def test_incremental_after_late_settlements_equals_full_build(fixture_db, tmp_env):
    src_raw, raw = fixture_db.parent / "raw", tmp_env / "raw"
    raw.mkdir()
    (raw / "fx_rates_daily.csv").write_text((src_raw / "fx_rates_daily.csv").read_text())
    full = pd.read_csv(src_raw / "transactions.csv", dtype=str)
    _truncate(full).to_csv(raw / "transactions.csv", index=False)
    build.main()                                 # full build of the earlier file
    full.to_csv(raw / "transactions.csv", index=False)
    build.main(incremental=True)                 # new rows + late settlements
    db = tmp_env / "casarecon.duckdb"
    for table in ("fct_transaction_discrepancy", "mart_psp_weekly", "mart_cause_summary"):
        assert _diff(db, fixture_db, table) == 0 == _diff(fixture_db, db, table), table


def test_dated_fee_join_picks_the_fee_valid_on_the_auth_date(fixture_db):
    with duckdb.connect(str(fixture_db), read_only=True) as con:
        fees = con.sql("""select psp, auth_date >= date '2026-06-01' as june, contract_fee_usd, count(*) n
                          from marts.fct_transaction_discrepancy group by all""").df()
    assert (fees.n > 0).all()
    got = {(r.psp, r.june): r.contract_fee_usd for r in fees.itertuples()}
    assert got[("PSP_C", False)] == 0 and got[("PSP_C", True)] == 1.5
    assert all(v == 0 for (psp, _), v in got.items() if psp != "PSP_C")


def test_provisional_weeks_match_the_restatement_window(fixture_db):
    st = core.status()
    start = weeks.provisional_from(st["as_of"])
    pw = core.psp_weekly()
    expected = sorted({w for w, end in zip(pw.auth_week, pw.week_end, strict=True)
                       if pd.Timestamp(end).date() >= start})
    assert st["provisional_weeks"] == expected
    assert st["last_closed_week"] in expected  # closed for reporting, still open to late settlements
    assert start == date(2026, 6, 15) and st["last_closed_week"] == "2026-W25"
    assert pw.is_provisional.equals(pw.auth_week.isin(expected))
