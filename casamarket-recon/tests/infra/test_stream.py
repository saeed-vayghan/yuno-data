"""Streaming path without Docker: replay event builder + compare (pure), and match.sql vs the dbt rules."""

import json
import re

import jinja2
import pandas as pd
import yaml

from casarecon.core import paths
from casarecon.stream import compare, events

MATCH_SQL = paths.REPO_ROOT / "infra" / "stream" / "sql" / "match.sql"

ROWS = [  # raw CSV rows (strings, as csv.DictReader gives them)
    {"transaction_id": "txn_b", "merchant_id": "casamarket", "psp": "PSP_A", "country": "MX",
     "currency": "MXN", "payer_currency": "USD", "is_cross_border": "true", "status": "settled",
     "auth_ts": "2026-04-01 10:00:00", "settle_ts": "2026-04-03 09:00:00",
     "authorized_amount": "10000", "settled_amount": "10050"},
    {"transaction_id": "txn_a", "merchant_id": "casamarket", "psp": "PSP_B", "country": "CL",
     "currency": "CLP", "payer_currency": "CLP", "is_cross_border": "false", "status": "failed",
     "auth_ts": "2026-04-02 08:00:00", "settle_ts": "", "authorized_amount": "5000", "settled_amount": ""},
    {"transaction_id": "txn_c", "merchant_id": "casamarket", "psp": "PSP_C", "country": "AR",
     "currency": "ARS", "payer_currency": "ARS", "is_cross_border": "false", "status": "pending",
     "auth_ts": "2026-04-03 09:00:00", "settle_ts": "", "authorized_amount": "700", "settled_amount": ""},
]


def test_replay_events_order_json_and_compare():
    evs = events.build_events(ROWS)
    assert [(e.topic, e.key) for e in evs] == [
        ("auths", "txn_b"), ("auths", "txn_a"),
        ("auths", "txn_c"), ("settlements", "txn_b")]  # same ts: auth before settlement
    auth_b, settle_b = evs[0].value, evs[3].value
    assert auth_b == {"transaction_id": "txn_b", "merchant_id": "casamarket", "psp": "PSP_A",
                      "country": "MX", "currency": "MXN", "payer_currency": "USD",
                      "is_cross_border": True, "authorized_amount": 10000,
                      "auth_ts": "2026-04-01 10:00:00", "status": "authorized"}
    assert settle_b == {"transaction_id": "txn_b", "psp": "PSP_A", "currency": "MXN",
                        "settled_amount": 10050, "settle_ts": "2026-04-03 09:00:00"}
    assert evs[1].value["status"] == "failed" and evs[2].value["status"] == "authorized"
    assert json.loads(json.dumps(auth_b)) == auth_b
    assert len(events.build_events(ROWS, limit=2)) == 2
    assert events.wall_offsets(evs, 86400) == [0.0, 22 / 24, 47 / 24, 47 / 24]  # 1 event day per second
    assert events.wall_offsets(evs, 0) == [0.0] * 4

    stream = pd.DataFrame({"transaction_id": ["t1", "t2", "t3"], "category": ["exact", "large", "exact"]})
    batch = pd.DataFrame({"transaction_id": ["t1", "t2"], "category": ["exact", "meaningful"]})
    table = compare.compare(stream, batch).set_index("category")
    assert table.loc["ALL", ["n", "n_match"]].tolist() == [3, 1]
    assert table.loc["meaningful", "match_rate"] == 0 and table.loc["(not in batch)", "n"] == 1


def _norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().lower()


def test_match_sql_uses_the_dbt_category_rules():
    t = yaml.safe_load((paths.CONFIG_DIR / "thresholds.yaml").read_text())
    macros = jinja2.Environment().from_string(
        (paths.DBT_DIR / "macros" / "discrepancy_rules.sql").read_text()).module
    rule = _norm(str(macros.category_case(t, "abs_residual_usd")))
    sql = _norm(MATCH_SQL.read_text())
    assert rule in sql, f"match.sql CASE drifted from dbt category_case: {rule}"
    for cutoff in (f"<= {t['rounding_minor_units']}", f"<= {t['fx_tolerance_pct']}",
                   f"<= {t['large_pct']}", f"< {t['large_usd']}"):
        assert cutoff in rule
    # same expected-settled formula as dbt expected_settled_sql() + the sink column order compare reads
    assert "round(authorized_amount * fx_settle / fx_auth, 0)" in sql
    ddl = re.search(r"create table matched_sink \((.*?)\) with", sql).group(1)
    assert [c.split()[0] for c in ddl.split(", ")] == list(compare.SINK_COLUMNS)
