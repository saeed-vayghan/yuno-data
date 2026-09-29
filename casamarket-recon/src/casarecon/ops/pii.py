"""`recon ops pii-scan`: look for banned fields and full customer IDs in local data and outputs.

Rules (banned fields come from every `contracts/*.yaml`):
- A banned field (pan, card_number, cvv, email, name) must not be a record field anywhere (CSV
  column, parquet column, JSONL key): raw, the lake (landing, quarantine, staged), reports, alerts.
- A full customer ID (`cus_` + 12 hex) is a token (`pii: token`), so raw and lake may hold it.
  It must never reach an output (reports/, data/alerts/): outputs show `cus_••••7f3a` only.
A hit raises DataQualityError, so the CLI exits 5.
"""

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import yaml

from casarecon.core import paths
from casarecon.core.errors import DataQualityError

CUSTOMER_ID = re.compile(r"\bcus_[0-9a-f]{12}\b")  # contract format "cus_ + 12 hex"
TEXT_SUFFIXES = (".csv", ".json", ".jsonl", ".md", ".html", ".txt")
MAX_SHOWN = 20


def banned_fields(contracts_dir: Path | None = None) -> frozenset[str]:
    """Union of `banned_fields` over all contracts, lower case."""
    folder = contracts_dir or paths.REPO_ROOT / "contracts"
    out: set[str] = set()
    for f in sorted(folder.glob("*.yaml")):
        out |= {str(b).lower() for b in (yaml.safe_load(f.read_text()) or {}).get("banned_fields", [])}
    return frozenset(out)


def default_zones() -> dict[str, tuple[Path, bool]]:
    """zone -> (folder, is_output). Only outputs are checked for full customer IDs."""
    from casarecon.ingest.settings import lake_dir

    data = paths.db_path().parent
    return {"raw": (paths.raw_dir(), False), "lake": (lake_dir(), False),
            "reports": (paths.reports_dir(), True), "alerts": (data / "alerts", True)}


# ---- pure checks -------------------------------------------------------------------------------

def field_hits(names: Iterable[str], banned: frozenset[str]) -> list[str]:
    return sorted({n for n in names if n.strip().strip('"').lower() in banned})


def id_hits(text: str) -> list[str]:
    return sorted(set(CUSTOMER_ID.findall(text)))


# ---- file readers (IO) -------------------------------------------------------------------------

def _names(path: Path) -> set[str]:
    """Record field names of one tabular file: CSV header, parquet schema, JSONL row keys.
    JSON documents (manifests, findings) are not records, so only the ID check reads them."""
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        return set(pq.read_schema(path).names)
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", errors="replace") as fh:
            return set(fh.readline().rstrip("\r\n").split(","))
    if path.suffix == ".jsonl":
        rows = (json.loads(line) for line in path.read_text().splitlines() if line.strip())
        return {k for row in rows if isinstance(row, dict) for k in row}
    return set()


def scan_file(path: Path, banned: frozenset[str], is_output: bool) -> list[str]:
    hits = [f"{path}: banned field '{n}'" for n in field_hits(_names(path), banned)]
    if is_output and path.suffix in TEXT_SUFFIXES:
        ids = id_hits(path.read_text(encoding="utf-8", errors="replace"))
        hits += [f"{path}: unmasked customer id {i[:8]}…" for i in ids[:3]]
    return hits


def scan(zones: Mapping[str, tuple[Path, bool]], banned: frozenset[str]) -> tuple[int, list[str]]:
    """(files scanned, hit messages) over every zone folder that exists."""
    n, hits = 0, []
    for folder, is_output in zones.values():
        for path in sorted(p for p in folder.rglob("*") if p.is_file()) if folder.exists() else ():
            if path.suffix in (*TEXT_SUFFIXES, ".parquet"):
                n += 1
                hits += scan_file(path, banned, is_output)
    return n, hits


def main(zones: Mapping[str, tuple[Path, bool]] | None = None) -> dict:
    """Scan; raise DataQualityError (exit 5) on any hit. Returns {'files': n, 'zones': [...]}."""
    zones = zones or default_zones()
    n, hits = scan(zones, banned_fields())
    if hits:
        more = f"\n… and {len(hits) - MAX_SHOWN} more" if len(hits) > MAX_SHOWN else ""
        raise DataQualityError(f"pii-scan: {len(hits)} hit(s)\n" + "\n".join(hits[:MAX_SHOWN]) + more)
    return {"files": n, "zones": [str(z[0]) for z in zones.values()]}
