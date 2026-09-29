"""reports/run_manifest.json: one section per step (build, validate). Not hashed (has timestamps)."""

import json
from pathlib import Path
from typing import Any

from casarecon.core import paths


def manifest_path() -> Path:
    return paths.reports_dir() / "run_manifest.json"


def update(section: str, data: Any, *, reset: bool = False) -> Path:
    """Merge `data` under `section`; `reset=True` starts a fresh manifest (a new build)."""
    out = manifest_path()
    doc = {} if reset or not out.exists() else json.loads(out.read_text())
    doc[section] = data
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    return out
