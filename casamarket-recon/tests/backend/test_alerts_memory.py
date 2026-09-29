"""Alert memory (open_since streak, mute), routing + dedupe, and the `recon alert` CLI."""

import json

import pytest
from typer.testing import CliRunner

from casarecon.alerts import memory, notify
from casarecon.alerts.run import remember
from casarecon.cli import app

W = "2026-W25"
SLACK = {"enabled": False, "severities": ["SEV2", "SEV3"]}


def alert(status="ONGOING", key="peer|PSP_B|AR", severity="SEV2", period=W) -> dict:
    return {"period": period, "rule_id": key.split("|")[0], "segment": key.split("|", 1)[1],
            "key": key, "psp": "PSP_B", "country": "AR", "severity": severity, "status": status,
            "owner": "PSP ops", "n": 100, "value": 0.2, "threshold": 0.1, "message": "m"}


def hist(period, status="ONGOING", sent=None, key="peer|PSP_B|AR") -> dict:
    return {"period": period, "key": key, "rule_id": "peer", "severity": "SEV2", "status": status,
            "open_since": None, "muted": False, "sent": sent}


@pytest.fixture(autouse=True)
def _tmp_memory(monkeypatch, tmp_path):
    monkeypatch.setenv("CASARECON_ALERT_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.setenv("CASARECON_ALERT_STATE", str(tmp_path / "alert_state.yaml"))
    monkeypatch.setenv("CASARECON_REPORTS_DIR", str(tmp_path / "reports"))


def test_open_since_walks_back_the_streak():
    # fired W19, not W20, then W21-W24 -> the current streak starts at W21
    h = [hist("2026-W19"), hist("2026-W20", "RESOLVED"), hist("2026-W21", "NEW"),
         hist("2026-W22"), hist("2026-W23"), hist("2026-W24")]
    assert memory.open_since(alert("ONGOING"), h) == "2026-W21"
    assert memory.open_since(alert("RESOLVED"), h) == "2026-W21"  # the streak that just ended
    assert memory.open_since(alert("NEW"), h) == W
    assert memory.open_since(alert("ONGOING"), []) == "2026-W24"  # no history: it fired in W-1
    assert memory.open_since(alert("INSUFFICIENT_DATA", severity="INFO"), h) is None


def test_mute_records_but_does_not_notify():
    state = {"mute": {"peer|PSP_B|AR": {"until": "2026-W26", "note": "ticket 42"}}}
    alerts, outbox, history = remember([alert("NEW")], W, [], state, SLACK)
    assert alerts[0]["muted"] is True and alerts[0]["open_since"] == W
    assert outbox == [] and history[0]["sent"] is None and history[0]["muted"] is True
    expired = {"mute": {"peer|PSP_B|AR": {"until": "2026-W24"}}}  # until < period -> not muted
    _, outbox, _ = remember([alert("NEW")], W, [], expired, SLACK)
    assert [(o["action"], o["channels"], o["dedupe_key"]) for o in outbox] == [
        ("trigger", ["outbox", "slack"], "peer|PSP_B|AR|2026-W25")]


def test_dedupe_ongoing_resolve_and_same_period_rerun_is_stable():
    sent_before = [hist("2026-W23", "NEW", sent="trigger"), hist("2026-W24")]
    _, outbox, _ = remember([alert("ONGOING")], W, sent_before, {}, SLACK)
    assert outbox == []  # already sent in this streak
    _, outbox, _ = remember([alert("ONGOING")], W, [hist("2026-W24")], {}, SLACK)
    assert [o["action"] for o in outbox] == ["trigger"]  # never sent before -> send once
    _, outbox, _ = remember([alert("RESOLVED")], W, sent_before, {}, SLACK)
    assert [o["action"] for o in outbox] == ["resolve"]
    info = remember([alert("NEW", severity="INFO")], W, [], {}, {"severities": []})[1]
    assert info == [] and notify.routing_of({"severities": []})["SEV2"] == ["outbox"]
    # re-running the same period reads only earlier periods and replaces its own lines
    first = remember([alert("NEW")], W, [], {}, SLACK)
    again = remember([alert("NEW")], W, first[2], {}, SLACK)
    assert again == first and [h["period"] for h in again[2]] == [W]


def test_alert_cli_ack_mute_history(tmp_path):
    (tmp_path / "reports").mkdir()
    rec = {**alert("NEW"), "open_since": W, "muted": False}
    (tmp_path / "reports" / "alerts.jsonl").write_text(json.dumps(rec) + "\n")
    (tmp_path / "history.jsonl").write_text(json.dumps(hist(W, "NEW", sent="trigger")) + "\n")
    run = CliRunner().invoke
    assert run(app, ["alert", "ack", "peer|PSP_B|AR", "--note", "T-1"]).exit_code == 0
    out = run(app, ["alert", "list"]).output
    assert "peer|PSP_B|AR" in out and f"{W}: T-1" in out
    assert run(app, ["alert", "mute", "peer|PSP_B|AR", "--until", "2026-W27"]).exit_code == 0
    assert run(app, ["alert", "mute", "peer|PSP_B|AR", "--until", "soon"]).exit_code == 2
    assert run(app, ["alert", "ack", "nope|X"]).exit_code == 2
    assert "trigger" in run(app, ["alert", "history", "peer|PSP_B|AR"]).output
    assert "until: 2026-W27" in (tmp_path / "alert_state.yaml").read_text()
