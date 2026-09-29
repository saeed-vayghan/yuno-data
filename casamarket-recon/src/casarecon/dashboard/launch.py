"""Entry point for `recon dashboard`: runs Streamlit on app.py. Owner: FRONTEND."""

import subprocess
import sys
from pathlib import Path

from casarecon.core import paths

APP = Path(__file__).with_name("app.py")


def command(port: int = 8501, host: str = "localhost") -> list[str]:
    """The streamlit command; the CLI flags beat .streamlit/config.toml (Docker passes 0.0.0.0)."""
    return [sys.executable, "-m", "streamlit", "run", str(APP),
            "--server.port", str(port), "--server.address", host]


def main(port: int = 8501, host: str = "localhost") -> None:
    # cwd = repo root, so Streamlit finds .streamlit/config.toml (theme, headless, no telemetry)
    raise SystemExit(subprocess.run(command(port, host), cwd=paths.REPO_ROOT, check=False).returncode)
