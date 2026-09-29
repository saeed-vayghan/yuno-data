"""The alerts' only file I/O (small adapter).

- reports/alerts.jsonl + alerts.md + notifications.jsonl (local outbox)
- data/alerts/history.jsonl (alert memory; env CASARECON_ALERT_HISTORY overrides the path)
- config/alert_state.yaml (ack / mute by key; env CASARECON_ALERT_STATE overrides the path)

Stable bytes: fixed field order, sorted rows, no timestamps -> two runs give the same hash.
Writes go to a temp file first, then rename, so a reader never sees half a file.
"""

import json
import os
from pathlib import Path

import yaml

from casarecon.core import paths

STATE_HEADER = ("# Alert ack / mute by key. Written by `recon alert ack|mute`; safe to edit by hand.\n"
                "# ack:  KEY: {period: YYYY-Www, note: text}   (seen by the owner, this open streak)\n"
                "# mute: KEY: {until: YYYY-Www, note: text}    (recorded, not notified, while period <= until)\n")


def history_path() -> Path:
    return Path(os.environ.get("CASARECON_ALERT_HISTORY",
                               paths.REPO_ROOT / "data" / "alerts" / "history.jsonl")).resolve()


def state_path() -> Path:
    return Path(os.environ.get("CASARECON_ALERT_STATE",
                               paths.CONFIG_DIR / "alert_state.yaml")).resolve()


def _atomic(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def read_jsonl(path: Path) -> list[dict]:
    """Rows of a jsonl file; [] when missing."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(out_dir: Path, alerts: list[dict], markdown: str,
          outbox: list[dict] | None = None) -> tuple[Path, Path]:
    jsonl = _atomic(out_dir / "alerts.jsonl", to_jsonl(alerts))
    md = _atomic(out_dir / "alerts.md", markdown)
    _atomic(out_dir / "notifications.jsonl", to_jsonl(outbox or []))
    return jsonl, md


def read_history() -> list[dict]:
    return read_jsonl(history_path())


def write_history(rows: list[dict]) -> Path:
    return _atomic(history_path(), to_jsonl(rows))


def read_state() -> dict:
    """{'ack': {key: {...}}, 'mute': {key: {...}}}; empty sections when the file is missing."""
    path = state_path()
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None) or {}
    return {"ack": dict(raw.get("ack") or {}), "mute": dict(raw.get("mute") or {})}


def write_state(state: dict) -> Path:
    body = yaml.safe_dump({"ack": state.get("ack") or {}, "mute": state.get("mute") or {}},
                          sort_keys=True, allow_unicode=True, default_flow_style=False)
    return _atomic(state_path(), STATE_HEADER + body)
