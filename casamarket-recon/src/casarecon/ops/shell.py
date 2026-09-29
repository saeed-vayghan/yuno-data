"""The one side-effect adapter of `ops`: run a `recon ...` sub-command as a subprocess.

Backfill calls other groups (`recon ingest`, `recon build`) through their CLI, so it only depends
on the public command line, not on their Python internals.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from casarecon.core import paths


def recon_exe() -> str:
    """The `recon` next to this Python (the uv venv), else whatever is on PATH."""
    local = Path(sys.executable).with_name("recon")
    return str(local) if local.exists() else (shutil.which("recon") or "recon")


def run_recon(args: Sequence[str], env: dict[str, str]) -> int:
    """`recon <args>` from the repo root with extra env; output streams to stderr. Returns exit code."""
    proc = subprocess.run([recon_exe(), *args], cwd=paths.REPO_ROOT, env={**os.environ, **env},
                          stdout=sys.stderr, check=False)
    return proc.returncode
