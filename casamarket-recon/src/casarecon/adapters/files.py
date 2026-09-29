"""File adapter for the `ReportFiles` port (json, md, jsonl) + csv, parquet and figures.
Owner: BACKEND. Readers return None when the file is missing; writers create parent folders."""

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from casarecon.core import log

FIGURE_FORMAT_ENV = "CASARECON_FIGURE_FORMAT"  # "html" skips PNG export (fast tests / no Chrome)


def _dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_json(path: Path, data: Any) -> None:
    """Byte-stable: sorted keys, indent 2, trailing newline, no NaN."""
    text = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    _dir(path).write_text(text + "\n", encoding="utf-8")


def read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def write_text(path: Path, text: str) -> None:
    _dir(path).write_text(text, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def write_jsonl(path: Path, rows: Sequence[dict]) -> None:
    text = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)
    _dir(path).write_text(text, encoding="utf-8")


def read_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def write_csv(path: Path, df: pd.DataFrame) -> None:
    """No index; floats rounded to 6 dp so reruns are byte-identical."""
    df.round(6).to_csv(_dir(path), index=False, lineterminator="\n")


def read_parquet(path: Path) -> pd.DataFrame | None:
    return pd.read_parquet(path) if path.exists() else None


def write_figures(figs: Mapping[Path, Any]) -> dict[Path, Path]:
    """Save Plotly figures as PNG (kaleido) in one batch; on any error (or env
    CASARECON_FIGURE_FORMAT=html) save .html instead. Returns {requested path: written path}."""
    pngs = {p: _dir(p.with_suffix(".png")) for p in figs}
    if figs and os.environ.get(FIGURE_FORMAT_ENV, "png") != "html":
        try:
            import plotly.io as pio

            pio.write_images(list(figs.values()), list(pngs.values()))
            return pngs
        except Exception as e:  # kaleido/Chrome missing must never fail the command
            log.get("files").warning("PNG export failed (%s); writing HTML figures", e)
    out = {}
    for p, fig in figs.items():
        out[p] = _dir(p.with_suffix(".html"))
        fig.write_html(out[p], include_plotlyjs="cdn", full_html=True)
    return out
