"""`recon ingest land`: simulate PSP deliveries. Split the generated raw CSV into one daily file per PSP.

File date = settle date for settled rows, else the auth date (a PSP daily report also lists the
pending and failed payments of that day). Each PSP file uses that PSP's format (config/ingest.yaml).
"""

import pandas as pd

from casarecon.core import log, paths
from casarecon.core.errors import InputMissing
from casarecon.ingest import formats, settings
from casarecon.ingest.storage import Storage, local


def report_date(df: pd.DataFrame) -> pd.Series:
    """'YYYY-MM-DD' of the PSP report that carries each row."""
    ts = df["settle_ts"].where(df["settle_ts"] != "", df["auth_ts"])
    return ts.str.slice(0, 10)


def split(df: pd.DataFrame, cfg: dict, contract: dict) -> dict[str, bytes]:
    """Pure: raw text table -> {landing key: PSP file bytes}, rows sorted by transaction_id."""
    df = df.assign(_date=report_date(df)).sort_values("transaction_id", kind="stable")
    out = {}
    for (psp, day), part in df.groupby(["psp", "_date"], sort=True):
        fmt = cfg["formats"][cfg["psps"][psp]]
        out[settings.landing_key(psp, day)] = formats.encode(part.drop(columns="_date"), fmt, contract)
    return out


def main(reset: bool = True, *, store: Storage | None = None) -> dict[str, int]:
    """Write landing files (+ the FX feed). reset=True starts a fresh lake (landing, staged,
    quarantine, manifest), because a new `recon generate` is a new delivery history."""
    raw = paths.raw_dir()
    txn, fx = raw / "transactions.csv", raw / "fx_rates_daily.csv"
    if not (txn.exists() and fx.exists()):
        raise InputMissing(f"no generated data in {raw}. Run `recon generate` first.")
    store = store or local(settings.lake_dir())
    if reset:
        for zone in (settings.LANDING, settings.STAGED, settings.QUARANTINE, settings.MANIFEST):
            store.reset(zone)
    cfg, contract = settings.ingest_config(), settings.contract("transactions")
    files = split(pd.read_csv(txn, dtype=str, keep_default_na=False), cfg, contract)
    for key, data in files.items():
        store.write_bytes(key, data)
    store.write_bytes(settings.FX_LANDING, fx.read_bytes())
    rows = sum(formats.row_count(d) for d in files.values())
    log.get("ingest").info(log.kv(step="ingest.land", files=len(files), rows=rows, psps=len(cfg["psps"]),
                                  lake=settings.lake_dir()))
    return {"files": len(files), "rows": rows}
