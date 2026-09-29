"""Storage adapter: the only file I/O in ingest/. Keys are '/'-separated paths under one root.

`LocalStorage` works on a local folder. Another backend (e.g. object storage) only needs the same
methods; the ingest logic never touches `Path` or `open` itself.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def list(self, pattern: str) -> list[str]: ...
    def exists(self, key: str) -> bool: ...
    def read_bytes(self, key: str) -> bytes: ...
    def write_bytes(self, key: str, data: bytes) -> None: ...
    def append_line(self, key: str, line: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def reset(self, prefix: str) -> None: ...


@dataclass(frozen=True)
class LocalStorage:
    root: Path

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"key escapes the storage root: {key}")
        return path

    def list(self, pattern: str) -> list[str]:
        """Sorted keys matching a glob pattern (files only)."""
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.glob(pattern) if p.is_file())

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def write_bytes(self, key: str, data: bytes) -> None:
        """Atomic: write a temp file next to the target, then rename."""
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def append_line(self, key: str, line: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line.rstrip("\n") + "\n")

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def reset(self, prefix: str) -> None:
        """Remove everything under prefix (a folder key) or the file itself."""
        path = self._path(prefix)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


def local(root: Path) -> LocalStorage:
    root.mkdir(parents=True, exist_ok=True)
    return LocalStorage(root)
