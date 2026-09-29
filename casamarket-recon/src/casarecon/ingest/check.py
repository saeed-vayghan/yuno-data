"""`recon ingest check`: DQ on the landing zone -> reports/ingest_dq.json + a table.

as_of = --as-of, else the latest file date in the lake (data time, never the wall clock).
Any FAIL (freshness) -> DataQualityError (exit 5). Drift, volume and quarantine only warn.
"""

import json
from datetime import date

import pandas as pd

from casarecon.core import log, paths
from casarecon.core.errors import DataQualityError, InputMissing
from casarecon.ingest import dq, formats, settings
from casarecon.ingest.storage import Storage, local


def inventory(store: Storage, cfg: dict) -> pd.DataFrame:
    """One row per landing file: psp, date, rows, settled rows, columns (contract names)."""
    rows = []
    for key in store.list(settings.LANDING_GLOB):
        psp, day = settings.parse_landing_key(key)
        data = store.read_bytes(key)
        fmt = cfg["formats"][cfg["psps"].get(psp, "standard")]
        rows.append({"psp": psp, "date": date.fromisoformat(day), "rows": formats.row_count(data),
                     "settled": formats.count_value(data, fmt, "status", "settled"),
                     "columns": tuple(formats.header(data, fmt))})
    return pd.DataFrame(rows, columns=["psp", "date", "rows", "settled", "columns"])


def evaluate(files: pd.DataFrame, cfg: dict, expected: list[str], n_quarantined: int,
             as_of: date) -> list[dict]:
    """Pure: all checks in a fixed order."""
    psps = sorted(set(cfg["psps"]) | set(files["psp"]))
    return [*dq.freshness(files, psps, as_of, cfg["dq"]["freshness_max_days"]),
            *dq.volume(files, psps, as_of, cfg["dq"]),
            *dq.drift(files, psps, expected),
            *dq.quarantine(n_quarantined)]


def main(as_of: str | None = None, *, store: Storage | None = None) -> str:
    """Run the checks, write reports/ingest_dq.json, print a table. Returns PASS or WARN."""
    store = store or local(settings.lake_dir())
    cfg = settings.ingest_config()
    files = inventory(store, cfg)
    if files.empty:
        raise InputMissing(f"no landing files in {settings.lake_dir()}. Run `recon ingest land` first.")
    day = date.fromisoformat(as_of) if as_of else max(files["date"])
    n_q = len(store.list(f"{settings.QUARANTINE}/**/reason.json"))
    rows = evaluate(files, cfg, list(settings.contract("transactions")["columns"]), n_q, day)
    status = dq.overall(rows)
    out = paths.reports_dir() / "ingest_dq.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = {"as_of": day.isoformat(), "status": status, "files": len(files),
               "rows": int(files["rows"].sum()), "checks": rows}
    out.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(pd.DataFrame(rows).to_string(index=False))
    log.get("ingest").info(log.kv(step="ingest.check", status=status, as_of=day, files=len(files), out=out))
    if status == "FAIL":
        bad = ", ".join(f"{r['check']}:{r['psp']}" for r in rows if r["status"] == "FAIL")
        raise DataQualityError(f"ingest DQ failed: {bad}")
    return status
