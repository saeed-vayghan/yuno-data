"""DuckDB adapter for the `Store` port: short read-only connections, errors mapped to core errors."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from casarecon.core.errors import DbBusy, DbMissing


@dataclass(frozen=True)
class DuckDbStore:
    path: Path

    @contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        if not self.path.exists():
            raise DbMissing(str(self.path))
        try:
            con = duckdb.connect(str(self.path), read_only=True)
        except duckdb.IOException as e:  # "Could not set lock on file"
            raise DbBusy("rebuilding, retry") from e
        try:
            yield con
        finally:
            con.close()

    def query(self, sql: str, params: Sequence[Any] = ()) -> pd.DataFrame:
        """Run one parameterized query. DATE columns come back as `datetime.date` (not Timestamp)."""
        with self.connect() as con:
            cur = con.execute(sql, list(params))
            dates = [d[0] for d in cur.description if str(d[1]).upper() == "DATE"]
            df = cur.df()
        for col in dates:
            df[col] = [None if pd.isna(v) else v.date() for v in df[col]]
        return df

    def version(self) -> float:
        return self.path.stat().st_mtime if self.path.exists() else 0.0
