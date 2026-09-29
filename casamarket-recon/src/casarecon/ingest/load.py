"""`recon ingest load`: landing -> contract check -> staged parquet, or quarantine + reason.json.

Idempotent: `_manifest.jsonl` keeps one line per processed file (key + sha256); a file with the
same hash is skipped. A changed file is processed again and replaces its part.
`--from D1 --to D2` (backfill/replay) forces the landing files of those dates again, also ones
quarantined before; a file that now passes leaves quarantine.
"""

import hashlib
import io
import json
from datetime import date

import pyarrow.parquet as pq

from casarecon.core import log
from casarecon.core.errors import BadFilter
from casarecon.ingest import contract as cc
from casarecon.ingest import formats, settings
from casarecon.ingest.storage import Storage, local

FX_FORMAT = {"delimiter": ",", "ts_format": formats.ISO_TS, "rename": {}}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seen(store: Storage) -> dict[tuple[str, str], str]:
    """(file key, sha256) -> last status ('loaded' | 'quarantined') of files already processed."""
    if not store.exists(settings.MANIFEST):
        return {}
    lines = store.read_bytes(settings.MANIFEST).decode().splitlines()
    return {(r["file"], r["sha256"]): r["status"] for r in map(json.loads, filter(None, lines))}


def parquet_bytes(table) -> bytes:
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    return buf.getvalue()


def process(key: str, data: bytes, fmt: dict, contract: dict, target: str, expect: dict,
            store: Storage) -> dict:
    """Check one file; write its part, or move it to quarantine. Returns the manifest line."""
    df = formats.decode(data, fmt, contract)
    result = cc.check(df, contract, expect)
    line = {"file": key, "sha256": sha256(data), "rows": len(df)}
    if result.ok:
        store.write_bytes(target, parquet_bytes(result.table))
        store.reset(settings.quarantine_dir(key))  # a fixed re-delivery leaves quarantine
        return {**line, "status": "loaded", "target": target}
    qdir = settings.quarantine_dir(key)
    kept = cc.redact(df, contract)
    store.write_bytes(f"{qdir}/{key.rsplit('/', 1)[-1]}",
                      data if len(kept.columns) == len(df.columns) else kept.to_csv(index=False).encode())
    reason = {"file": key, "sha256": line["sha256"], "rows": len(df), "problems": list(result.problems)}
    store.write_bytes(f"{qdir}/reason.json", (json.dumps(reason, indent=2) + "\n").encode())
    store.delete(target)  # an older good version of this file must not stay in staged
    return {**line, "status": "quarantined", "target": qdir}


def tasks(store: Storage, cfg: dict) -> list[tuple[str, str | None, dict, str, str, dict]]:
    """(landing key, file date, format, contract name, staged key, expected values) per landing file."""
    out = [(settings.FX_LANDING, None, FX_FORMAT, "fx_rates_daily", settings.FX_STAGED, {})]
    for key in store.list(settings.LANDING_GLOB):
        psp, day = settings.parse_landing_key(key)
        fmt = cfg["formats"][cfg["psps"].get(psp, "standard")]
        out.append((key, day, fmt, "transactions", settings.staged_key(psp, day), {"psp": psp}))
    return out


def forced(day: str | None, date_from: str | None, date_to: str | None) -> bool:
    """True when a dated landing file is inside [date_from, date_to] (either end may be open)."""
    if day is None or (date_from is None and date_to is None):
        return False
    return (date_from or day) <= day <= (date_to or day)


def main(date_from: str | None = None, date_to: str | None = None, *,
         store: Storage | None = None) -> dict[str, int]:
    """Load every new or changed landing file (+ all files dated D1..D2). Returns counts per outcome."""
    for d in (date_from, date_to):
        try:
            _ = d is None or date.fromisoformat(d)
        except ValueError as e:
            raise BadFilter(f"bad date {d!r}: use YYYY-MM-DD") from e
    store = store or local(settings.lake_dir())
    cfg, done = settings.ingest_config(), seen(store)
    contracts = {n: settings.contract(n) for n in ("transactions", "fx_rates_daily")}
    counts = {"loaded": 0, "quarantined": 0, "skipped": 0, "rows": 0}
    for key, day, fmt, name, target, expect in tasks(store, cfg):
        if not store.exists(key):
            continue
        data = store.read_bytes(key)
        status = done.get((key, sha256(data)))
        done_ok = status == "quarantined" or (status == "loaded" and store.exists(target))
        if done_ok and not forced(day, date_from, date_to):
            counts["skipped"] += 1
            continue
        line = process(key, data, fmt, contracts[name], target, expect, store)
        store.append_line(settings.MANIFEST, json.dumps(line, sort_keys=True))
        counts[line["status"]] += 1
        counts["rows"] += line["rows"] if line["status"] == "loaded" and name == "transactions" else 0
    log.get("ingest").info(log.kv(step="ingest.load", **counts, lake=settings.lake_dir()))
    return counts
