"""The only I/O in generate/: read the contract, write CSVs, truth parquet and the manifest."""

import json
from importlib.metadata import version
from pathlib import Path

import pandas as pd
import yaml

from casarecon.core import paths

TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def contract_columns(root: Path | None = None) -> list[str]:
    """Column order from contracts/transactions.yaml."""
    with ((root or paths.REPO_ROOT) / "contracts" / "transactions.yaml").open() as f:
        return list(yaml.safe_load(f)["columns"])


def to_raw(txn: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Contract columns only, in contract order; ints stay ints, bools lowercase, ts as text."""
    out = txn[columns].copy()
    out["is_cross_border"] = out["is_cross_border"].map({True: "true", False: "false"})
    for col in ("auth_ts", "settle_ts"):
        out[col] = out[col].dt.strftime(TS_FORMAT)
    out["authorized_amount"] = out["authorized_amount"].astype("int64")
    out["settled_amount"] = out["settled_amount"].astype("Int64")
    return out


def write_all(ds, raw_dir: Path, truth_dir: Path) -> dict[str, Path]:
    """Write the 4 outputs (byte-identical for the same Dataset). Returns name -> path."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "transactions": raw_dir / "transactions.csv",
        "fx_rates_daily": raw_dir / "fx_rates_daily.csv",
        "labels": truth_dir / "labels.parquet",
        "manifest": raw_dir / "generation_manifest.json",
    }
    to_raw(ds.transactions, contract_columns()).to_csv(out["transactions"], index=False, lineterminator="\n")
    ds.fx_rates.to_csv(out["fx_rates_daily"], index=False, float_format="%.6f", lineterminator="\n")
    ds.labels.to_parquet(out["labels"], index=False)
    manifest = {**ds.manifest, "versions": {p: version(p) for p in ("casarecon", "numpy", "pandas")}}
    out["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return out
