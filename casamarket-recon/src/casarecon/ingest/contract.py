"""Contract check on arrival (pure): text table + contract -> typed Arrow table, or the reasons it is bad.

A file is all-or-nothing: one bad row quarantines the whole file (a PSP delivery is one unit;
a half-loaded day would hide money). Extra columns are dropped here and reported as drift by `check`.
"""

from dataclasses import dataclass

import pandas as pd
import pyarrow as pa

from casarecon.ingest.formats import ISO_TS

ISO_DATE = "%Y-%m-%d"
ARROW = {"str": pa.string(), "int": pa.int64(), "float": pa.float64(), "bool": pa.bool_(),
         "timestamp": pa.timestamp("us"), "date": pa.date32()}
MAX_EXAMPLES = 5


@dataclass(frozen=True)
class Result:
    table: pa.Table | None      # typed rows (contract columns, contract order) when ok
    problems: tuple[dict, ...]  # [{column, problem, rows, examples}] when not ok

    @property
    def ok(self) -> bool:
        return not self.problems


def arrow_schema(contract: dict) -> pa.Schema:
    return pa.schema([(c, ARROW[s["type"]]) for c, s in contract["columns"].items()])


def parse(col: pd.Series, kind: str) -> tuple[pd.Series, pd.Series]:
    """(typed values, mask of non-empty values that do not parse as `kind`)."""
    text = col.str.strip()
    empty = text == ""
    if kind == "int":
        ok = text.str.fullmatch(r"-?\d+")
        typed = pd.to_numeric(text.where(ok), errors="coerce").astype("Int64")
    elif kind == "float":
        typed = pd.to_numeric(text.where(~empty), errors="coerce")
    elif kind == "bool":
        typed = text.str.lower().map({"true": True, "false": False})
    elif kind in ("timestamp", "date"):
        typed = pd.to_datetime(text.where(~empty), format=ISO_TS if kind == "timestamp" else ISO_DATE,
                               errors="coerce")
        typed = typed.dt.date if kind == "date" else typed.astype("datetime64[us]")
    else:
        typed = text.where(~empty, None)
    return typed, ~empty & pd.isna(typed)


def _row_problems(df: pd.DataFrame, contract: dict) -> tuple[dict[str, pd.Series], list[dict]]:
    typed, found = {}, []
    for name, spec in contract["columns"].items():
        values, bad_type = parse(df[name], spec["type"])
        typed[name] = values
        checks = {"type": bad_type, "null": df[name].str.strip().eq("") & (not spec.get("nullable", False))}
        if "enum" in spec:
            checks["enum"] = values.notna() & ~values.isin(spec["enum"])
        for bound, op in (("min", "lt"), ("max", "gt")):
            if bound in spec:
                checks[bound] = values.notna() & getattr(values.astype(float), op)(spec[bound])
        for problem, mask in checks.items():
            if mask.any():
                rows = [int(i) + 2 for i in df.index[mask][:MAX_EXAMPLES]]  # file line numbers
                found.append({"column": name, "problem": problem, "rows": int(mask.sum()), "examples": rows})
    return typed, found


def check(df: pd.DataFrame, contract: dict, expect: dict | None = None) -> Result:
    """Columns, banned fields, types, nulls, enums, min/max; `expect` = {column: value} every row must have."""
    cols = list(contract["columns"])
    banned = sorted(set(map(str.lower, df.columns)) & {b.lower() for b in contract.get("banned_fields", [])})
    missing = [c for c in cols if c not in df.columns]
    file_level = ([{"column": c, "problem": "banned_field"} for c in banned]
                  + [{"column": c, "problem": "missing_column"} for c in missing])
    if file_level:
        return Result(None, tuple(file_level))
    typed, found = _row_problems(df, contract)
    for col, value in (expect or {}).items():
        wrong = df[col].str.strip() != value
        if wrong.any():
            found.append({"column": col, "problem": f"not {value}", "rows": int(wrong.sum()),
                          "examples": [int(i) + 2 for i in df.index[wrong][:MAX_EXAMPLES]]})
    if found:
        return Result(None, tuple(found))
    frame = pd.DataFrame(typed)[cols]
    return Result(pa.Table.from_pandas(frame, schema=arrow_schema(contract), preserve_index=False), ())


def redact(df: pd.DataFrame, contract: dict) -> pd.DataFrame:
    """Drop banned columns before a bad file is kept in quarantine (never store a PAN, e-mail, ...)."""
    banned = {b.lower() for b in contract.get("banned_fields", [])}
    return df[[c for c in df.columns if c.lower() not in banned]]
