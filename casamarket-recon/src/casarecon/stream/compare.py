"""`recon stream compare`: Flink matched rows (CSV sink) vs the batch fct category, per transaction_id.

Pure part: `compare(stream, batch)` -> one row per batch category + `ALL`. Exit 5 below MIN_MATCH.
"""

import os
from pathlib import Path

import pandas as pd

from casarecon import core
from casarecon.core import paths
from casarecon.core.errors import DataQualityError, InputMissing

MIN_MATCH = 0.99
# Column order of the `matched_sink` table in infra/stream/sql/match.sql (CSV has no header).
SINK_COLUMNS = ("transaction_id", "psp", "country", "currency", "is_cross_border", "auth_ts",
                "settle_ts", "authorized_amount", "settled_amount", "fx_auth", "fx_settle",
                "expected_settled", "residual", "residual_pct", "residual_usd", "category")


def stream_dir() -> Path:
    """<lake>/stream; lake = env CASARECON_LAKE_DIR, else <raw dir>/../lake (same rule as ingest)."""
    lake = Path(os.environ.get("CASARECON_LAKE_DIR", paths.raw_dir().parent / "lake")).resolve()
    return lake / "stream"


def read_matched(folder: Path) -> pd.DataFrame:
    """All committed sink files (Flink keeps in-progress files hidden as `.part-*`), last row per id."""
    files = sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.startswith("."))
    if not files:
        raise InputMissing(f"no stream output in {folder}: run `make stream-job stream-replay` first")
    df = pd.concat([pd.read_csv(p, header=None, names=list(SINK_COLUMNS), dtype={"category": str})
                    for p in files], ignore_index=True)
    df["category"] = df["category"].str.strip()
    return df.drop_duplicates("transaction_id", keep="last")


def compare(stream: pd.DataFrame, batch: pd.DataFrame) -> pd.DataFrame:
    """Per batch category: n stream rows, n equal, match_rate. Ids missing from batch count as misses."""
    j = stream[["transaction_id", "category"]].merge(
        batch[["transaction_id", "category"]], on="transaction_id", how="left", suffixes=("_stream", ""))
    j["category"] = j["category"].fillna("(not in batch)")
    j["ok"] = j["category_stream"] == j["category"]
    per = j.groupby("category", sort=True)["ok"].agg(n="size", n_match="sum").reset_index()
    total = pd.DataFrame([{"category": "ALL", "n": len(j), "n_match": int(j["ok"].sum())}])
    out = pd.concat([per, total], ignore_index=True)
    out["match_rate"] = (out["n_match"] / out["n"]).round(4)
    return out


def main() -> pd.DataFrame:
    """Compare and return the table; raise DataQualityError (exit 5) when the ALL rate < MIN_MATCH."""
    table = compare(read_matched(stream_dir() / "matched"), core.settled_facts())
    rate = float(table.loc[table["category"] == "ALL", "match_rate"].iloc[0])
    print(table.to_string(index=False))
    if rate < MIN_MATCH:
        raise DataQualityError(f"stream vs batch category match {rate:.2%} < {MIN_MATCH:.0%}")
    return table
