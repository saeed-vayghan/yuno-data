"""The alerts' only file I/O (small adapter): write reports/alerts.jsonl + reports/alerts.md.

Stable bytes: fixed field order, sorted rows, no timestamps -> two runs give the same hash.
"""

import json
from pathlib import Path


def to_jsonl(alerts: list[dict]) -> str:
    return "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in alerts)


def write(out_dir: Path, alerts: list[dict], markdown: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl, md = out_dir / "alerts.jsonl", out_dir / "alerts.md"
    jsonl.write_text(to_jsonl(alerts), encoding="utf-8")
    md.write_text(markdown, encoding="utf-8")
    return jsonl, md
