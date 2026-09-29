"""Alerts: the 6 rules as pure functions on tiny frames (fire + silent), status logic, end-to-end run."""

import hashlib

import pandas as pd
import pytest

from casarecon.alerts import run
from casarecon.alerts.evaluate import evaluate, with_status
from casarecon.alerts.record import FIELDS, RuleInput, record, trailing
from casarecon.alerts.rules_money import large_rows, money_leak, pending_aging
from casarecon.alerts.rules_rate import change, peer, settle_lag
from casarecon.core.config import load_config
from tests.backend.test_ui_q_minidb import minidb  # noqa: F401  (fixture)

W, PREV = "2026-W25", "2026-W24"
CFG = {r["id"]: r for r in load_config().alerts.rules}
COLS = ["psp", "country", "amount_tier", "auth_week", "n", "n_flagged", "n_large", "large_usd",
        "gross_under_usd", "gross_over_usd", "settled_usd", "n_open", "n_open_old", "n_late"]


def row(psp="PSP_A", country="MX", week=W, n=200, flagged=20, tier="50-200", **kw) -> dict:
    return {"psp": psp, "country": country, "amount_tier": tier, "auth_week": week, "n": n,
            "n_flagged": flagged, "n_large": 0, "large_usd": 0.0, "gross_under_usd": 0.0,
            "gross_over_usd": 0.0, "settled_usd": 100.0 * n, "n_open": 0, "n_open_old": 0, "n_late": 0,
            **kw}


def data(rows) -> RuleInput:
    return RuleInput(frame=pd.DataFrame(rows, columns=COLS), min_n=50,
                     money={"warn_pct": 1.5, "crit_pct": 2.5, "weekly_usd": 9800})


def peer_rows(b_flagged: int) -> list[dict]:
    return [row(p, "AR", w, 200, b_flagged if p == "PSP_B" else 20)
            for w in trailing(W, 4) for p in ("PSP_A", "PSP_B", "PSP_C")]


def change_rows(last_flagged: int, base_weeks: int = 8) -> list[dict]:
    return [row(week=w, n=500, flagged=50) for w in trailing(PREV, base_weeks)] + [
        row(n=500, flagged=last_flagged)]


def test_rate_rules_peer_change_settle_lag():
    [a] = peer(data(peer_rows(40)), CFG["peer"], W)  # 20% vs 10% for other AR PSPs
    assert (a["key"], a["psp"], a["country"], a["severity"]) == ("peer|PSP_B|AR", "PSP_B", "AR", "SEV2")
    assert (a["value"], a["threshold"]) == (0.2, 0.12) and "q < 0.001" in a["message"]
    assert peer(data(peer_rows(20)), CFG["peer"], W) == []

    fired = change(data(change_rows(100)), CFG["change"], W)  # 20% vs 10% baseline, n=500
    assert {x["segment"] for x in fired} == {"ALL", "PSP_A|MX"} and fired[0]["threshold"] < 0.15
    assert change(data(change_rows(55)), CFG["change"], W) == []
    thin = change(data(change_rows(100, base_weeks=5)), CFG["change"], W)  # < 8 prior weeks
    assert {(x["status"], x["severity"]) for x in thin} == {("INSUFFICIENT_DATA", "INFO")}

    late = [row(country="CO", tier="200+", week=w, n=100, n_late=10) for w in trailing(W, 4)]
    [s] = settle_lag(data(late), CFG["settle_lag"], W)
    assert (s["segment"], s["country"], s["psp"], s["value"]) == ("CO|200+", "CO", None, 0.1)
    ok = [row(country="CO", tier="200+", week=w, n=100, n_late=3) for w in trailing(W, 4)]
    assert settle_lag(data(ok), CFG["settle_lag"], W) == []


def test_money_rules_leak_large_pending_and_small_n():
    leak = lambda under: money_leak(data([row(n=1000, gross_under_usd=under)]), CFG["money_leak"], W)  # noqa: E731
    assert [a["severity"] for a in leak(3000.0) + leak(2000.0) + leak(1000.0)] == ["SEV2", "SEV3"]

    rows = [row("PSP_A", "MX", n_large=2, large_usd=90.0), row("PSP_D", "CL", n_large=5, large_usd=400.0),
            row("PSP_B", "AR", n_large=1, large_usd=25.0), row("PSP_C", "CO", n_large=1, large_usd=21.0)]
    [a] = large_rows(data(rows), CFG["large_rows"], W)
    assert a["value"] == 536.0 and a["message"].startswith("9 large rows")
    assert "top: PSP_D|CL $400.00, PSP_A|MX $90.00, PSP_B|AR $25.00." in a["message"]
    assert large_rows(data([row()]), CFG["large_rows"], W) == []

    # share of pending rows older than 7 d: 30% -> SEV2, 12% -> SEV3, 5% -> silent, n < 50 -> INFO
    pend = [row("PSP_C", "CO", n_open=60, n_open_old=18), row("PSP_A", "MX", n_open=50, n_open_old=6),
            row("PSP_E", "CL", n_open=60, n_open_old=3), row("PSP_B", "AR", n_open=10, n_open_old=9)]
    out = pending_aging(data(pend), CFG["pending_aging"], W)
    assert [(x["segment"], x["severity"], x["threshold"]) for x in out] == [
        ("PSP_A|MX", "SEV3", 0.1), ("PSP_B|AR", "INFO", 50.0), ("PSP_C|CO", "SEV2", 0.25)]

    small = data([row(n=10, flagged=9, gross_under_usd=500.0, n_large=5, large_usd=500.0)])
    for rule in (money_leak, large_rows):  # n < 50 -> INSUFFICIENT_DATA, never an alert
        [x] = rule(small, CFG[rule.__name__], W)
        assert (x["status"], x["severity"], x["n"]) == ("INSUFFICIENT_DATA", "INFO", 10)


def test_status_new_ongoing_resolved_and_sorting():
    fire = lambda seg, wk: record(CFG["peer"], wk, seg, n=100, value=0.2, threshold=0.1, message="m")  # noqa: E731
    now, before = [fire("PSP_A|MX", W), fire("PSP_B|AR", W)], [fire("PSP_B|AR", PREV), fire("PSP_C|CO", PREV)]
    status = {r["segment"]: (r["status"], r["period"]) for r in with_status(now, before, W)}
    assert status == {"PSP_A|MX": ("NEW", W), "PSP_B|AR": ("ONGOING", W), "PSP_C|CO": ("RESOLVED", W)}

    rows = peer_rows(40) + [row(n=1000, gross_under_usd=3000.0, n_large=1, large_usd=30.0)]
    out = evaluate(data(rows), list(CFG.values()), W, PREV)
    assert all(tuple(a) == FIELDS for a in out)
    sev = [a["severity"] for a in out]
    assert sev == sorted(sev, key={"SEV2": 0, "SEV3": 1, "INFO": 2}.get)
    by_rule = {a["rule_id"]: a["status"] for a in out if a["severity"] != "INFO"}
    assert by_rule["peer"] == "ONGOING" and by_rule["money_leak"] == "NEW"  # W-1 window overlaps


def test_run_writes_deterministic_reports_slack_off(minidb, tmp_path):
    calls: list[str] = []
    first = run.main(store=minidb, out_dir=tmp_path, notify=calls.append)
    digest = hashlib.sha256((tmp_path / "alerts.jsonl").read_bytes()).hexdigest()
    run.main(store=minidb, out_dir=tmp_path, notify=calls.append)
    assert hashlib.sha256((tmp_path / "alerts.jsonl").read_bytes()).hexdigest() == digest
    assert calls == []  # slack.enabled is false in config/alerts.yaml
    # mini DB is tiny (like a smoke run): every line is INSUFFICIENT_DATA, period = last closed week
    assert {(a["status"], a["severity"], a["period"]) for a in first} == {("INSUFFICIENT_DATA", "INFO", W)}
    assert {a["rule_id"] for a in first} == set(CFG)
    md = (tmp_path / "alerts.md").read_text()
    assert md.startswith(f"# Alerts: {W}") and "## Money" in md


@pytest.fixture(autouse=True)
def _no_slack_env(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)


def test_peer_alerts_group_by_psp_and_keep_status():
    from casarecon.alerts.evaluate import with_status
    from casarecon.alerts.group import group_peers
    from casarecon.alerts.record import record
    cfg = {"id": "peer", "owner": "PSP ops", "severity": "SEV2", "min_gap_pts": 2,
           "group_min_countries": 3}
    rows = lambda w, cs: [record(cfg, w, f"PSP_C|{c}", psp="PSP_C", country=c, n=100,  # noqa: E731
                                 value=0.17, threshold=0.16, message="m") for c in cs]
    now = group_peers(rows("W2", ["AR", "CL", "MX"]), cfg, "W2")
    assert [r["segment"] for r in now] == ["PSP_C|ALL"]
    out = with_status(now, group_peers(rows("W1", ["CO"]), cfg, "W1"), "W2")
    assert [(r["segment"], r["status"]) for r in out] == [("PSP_C|ALL", "ONGOING")]
