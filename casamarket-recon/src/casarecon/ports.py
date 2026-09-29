"""Ports: the only interfaces core/domain code depends on. Adapters live in casarecon.adapters."""

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol

import pandas as pd


class Store(Protocol):
    """Read-only analytical store (default: DuckDB file)."""

    def query(self, sql: str, params: Sequence[Any] = ()) -> pd.DataFrame: ...
    def connect(self) -> AbstractContextManager[Any]: ...
    def version(self) -> float: ...


class ReportFiles(Protocol):
    """Read/write report artifacts (json, md, jsonl). Readers return None when missing."""

    def read_json(self, path: Path) -> Any | None: ...
    def write_json(self, path: Path, data: Any) -> None: ...
    def read_text(self, path: Path) -> str | None: ...
    def write_text(self, path: Path, text: str) -> None: ...
    def read_jsonl(self, path: Path) -> list[dict] | None: ...
    def write_jsonl(self, path: Path, rows: Sequence[dict]) -> None: ...


Notifier = Callable[[str], bool]
"""Send one message (e.g. Slack). Returns True if sent."""

DbtRunner = Callable[[Sequence[str], dict[str, str]], int]
"""Run a dbt command (args, extra env). Returns the exit code."""
