"""Ingest settings: config/ingest.yaml, the contracts and the lake layout (keys relative to the lake root)."""

import os
from pathlib import Path

import yaml

from casarecon.core import paths

LANDING, STAGED, QUARANTINE, MANIFEST = "landing", "staged", "quarantine", "_manifest.jsonl"
FX_LANDING = f"{LANDING}/reference/fx_rates_daily.csv"
FX_STAGED = f"{STAGED}/fx_rates_daily/fx_rates_daily.parquet"
LANDING_GLOB = f"{LANDING}/psp=*/date=*/settlements.csv"


def lake_dir() -> Path:
    """Env CASARECON_LAKE_DIR, else <raw dir>/../lake (same rule as dbt `_sources.yml`)."""
    return Path(os.environ.get("CASARECON_LAKE_DIR", paths.raw_dir().parent / "lake")).resolve()


def _yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def ingest_config(root: Path | None = None) -> dict:
    return _yaml((root or paths.REPO_ROOT) / "config" / "ingest.yaml")


def contract(name: str, root: Path | None = None) -> dict:
    """contracts/<name>.yaml as a dict (columns in order, banned_fields)."""
    return _yaml((root or paths.REPO_ROOT) / "contracts" / f"{name}.yaml")


def landing_key(psp: str, day: str) -> str:
    return f"{LANDING}/psp={psp}/date={day}/settlements.csv"


def staged_key(psp: str, day: str) -> str:
    """One parquet part per landing file, in the month partition of the file date."""
    return f"{STAGED}/transactions/settle_month={day[:7]}/part-{psp}-{day}.parquet"


def quarantine_dir(landing: str) -> str:
    """landing/psp=X/date=D/settlements.csv -> quarantine/psp=X/date=D (file + reason.json)."""
    return QUARANTINE + landing.removeprefix(LANDING).rsplit("/", 1)[0]


def parse_landing_key(key: str) -> tuple[str, str]:
    """'landing/psp=PSP_A/date=2026-04-03/settlements.csv' -> ('PSP_A', '2026-04-03')."""
    parts = dict(p.split("=", 1) for p in key.split("/") if "=" in p)
    return parts["psp"], parts["date"]
