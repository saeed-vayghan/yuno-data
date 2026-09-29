"""ui_q on INFRA's 500-row `fixture_db` (real dbt output). Skipped until the fixture exists."""

from pathlib import Path

import pytest

from casarecon.adapters.duckdb_store import DuckDbStore
from casarecon.core import deps
from casarecon.core.queries import ui_q


@pytest.fixture
def real_store(request):
    try:
        db = request.getfixturevalue("fixture_db")
    except pytest.FixtureLookupError:
        pytest.skip("fixture_db not in tests/conftest.py yet (INFRA M1)")
    if hasattr(db, "query"):
        return db
    return DuckDbStore(Path(db)) if isinstance(db, (str, Path)) else deps.get_store()


def test_ui_q_on_real_db(real_store):
    k = ui_q.kpis(week="all", store=real_store)
    assert k["n"] > 0 and 0 <= k["flag_rate"] <= 1
    assert round(k["net_usd"], 2) == k["net_usd"]
    trend = ui_q.weekly_trend(store=real_store)
    assert trend["n"].sum() == k["n"] and trend["is_closed"].any()
    opts = ui_q.filter_options(store=real_store)
    assert set(trend["auth_week"]) <= set(opts["weeks"]) and opts["weeks"] == sorted(opts["weeks"])
    s = ui_q.outlier_summary(min_usd=0, store=real_store)
    assert s["n"] >= ui_q.outlier_summary(min_usd=50, store=real_store)["n"]
    txn = real_store.query("select transaction_id from marts.fct_transaction_discrepancy "
                           "where category = 'large' order by transaction_id limit 1")
    assert not txn.empty, "500-row fixture should have large rows"
    tid = txn["transaction_id"].iloc[0]
    d = ui_q.transaction_detail(tid, store=real_store)
    assert d["customer"].startswith("cus_••••") and len(d["customer"]) == len("cus_••••") + 4
    assert ui_q.similar_count(tid, store=real_store)["n"] >= 1
    assert list(ui_q.pending(store=real_store).columns) == [
        "psp", "country", "n", "amount_usd", "oldest_age_days"]
