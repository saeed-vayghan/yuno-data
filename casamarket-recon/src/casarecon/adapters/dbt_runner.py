"""dbt adapter for the `DbtRunner` port: runs dbt as a subprocess from the dbt/ folder.

dbt output goes to stderr so `recon` stdout stays clean for piping. Exit codes (dbt):
0 ok, 1 a model/test failed, 2 dbt itself crashed.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from casarecon.core import paths


def _dbt_exe() -> str:
    """The dbt next to this Python (the uv venv), else whatever is on PATH."""
    local = Path(sys.executable).with_name("dbt")
    return str(local) if local.exists() else (shutil.which("dbt") or "dbt")


def run_dbt(args: Sequence[str], env: dict[str, str]) -> int:
    """`dbt <args>` with project + profiles in dbt/. Returns the dbt exit code."""
    cmd = [_dbt_exe(), *args, "--project-dir", str(paths.DBT_DIR), "--profiles-dir", str(paths.DBT_DIR)]
    proc = subprocess.run(cmd, cwd=paths.DBT_DIR, env={**os.environ, **env}, stdout=sys.stderr,
                          check=False)
    return proc.returncode
