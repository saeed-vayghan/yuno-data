"""PSP file-format adapters (pure): contract-shaped text table <-> one PSP's CSV bytes.

A format (config/ingest.yaml `formats`) = delimiter + timestamp format + column renames.
All values stay text here; typing happens in `contract.py`. Empty string = null.
"""

import io

import pandas as pd

ISO_TS = "%Y-%m-%d %H:%M:%S"


def ts_columns(contract: dict) -> list[str]:
    return [c for c, spec in contract["columns"].items() if spec["type"] == "timestamp"]


def _reformat_ts(col: pd.Series, src: str, dst: str) -> pd.Series:
    """Re-render timestamps; a value that does not parse is kept as is (the contract check reports it)."""
    if src == dst:
        return col
    parsed = pd.to_datetime(col.where(col != ""), format=src, errors="coerce")
    return parsed.dt.strftime(dst).where(parsed.notna(), col)


def encode(df: pd.DataFrame, fmt: dict, contract: dict) -> bytes:
    """Contract table (text, ISO timestamps) -> the PSP's CSV bytes."""
    out = df.copy()
    for col in ts_columns(contract):
        out[col] = _reformat_ts(out[col], ISO_TS, fmt["ts_format"])
    out = out.rename(columns=fmt.get("rename") or {})
    return out.to_csv(index=False, sep=fmt["delimiter"], lineterminator="\n").encode()


def header(data: bytes, fmt: dict) -> list[str]:
    """Column names of a PSP file, mapped back to contract names where the format renames them."""
    first = data.split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
    back = {v: k for k, v in (fmt.get("rename") or {}).items()}
    return [back.get(c.strip(), c.strip()) for c in first.split(fmt["delimiter"])] if first else []


def decode(data: bytes, fmt: dict, contract: dict) -> pd.DataFrame:
    """PSP CSV bytes -> text table with contract column names and ISO timestamps."""
    df = pd.read_csv(io.BytesIO(data), sep=fmt["delimiter"], dtype=str, keep_default_na=False)
    df = df.rename(columns={v: k for k, v in (fmt.get("rename") or {}).items()})
    df.columns = [str(c).strip() for c in df.columns]
    for col in ts_columns(contract):
        if col in df:
            df[col] = _reformat_ts(df[col], fmt["ts_format"], ISO_TS)
    return df


def row_count(data: bytes) -> int:
    """Data rows in a CSV (lines minus the header), without parsing."""
    lines = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
    return max(lines - 1, 0)


def count_value(data: bytes, fmt: dict, column: str, value: str) -> int:
    """Rows where a contract column equals value (0 when the column is missing)."""
    if column not in header(data, fmt):
        return 0
    name = (fmt.get("rename") or {}).get(column, column)
    col = pd.read_csv(io.BytesIO(data), sep=fmt["delimiter"], dtype=str, usecols=[name], keep_default_na=False)
    return int((col[name].str.strip() == value).sum())
