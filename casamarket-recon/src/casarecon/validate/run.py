"""Entry point for `recon validate`: the data-quality gate after `build`. Owner: INFRA.

Mode comes from the row count (not a flag): rows >= thresholds.full_run_min_rows -> full run.
Any FAIL -> DataQualityError (exit 5). Result merged into reports/run_manifest.json["validate"].
"""

import pandas as pd

from casarecon.core import log
from casarecon.core.config import load_config
from casarecon.core.deps import get_store
from casarecon.core.errors import DataQualityError
from casarecon.pipeline import manifest
from casarecon.ports import Store
from casarecon.validate.checks import Check, as_rows, evaluate, overall
from casarecon.validate.metrics import read_metrics


def render(checks: list[Check]) -> str:
    df = pd.DataFrame(as_rows(checks))
    df["bounds"] = [f"[{lo:g}, {hi:g}]" for lo, hi in zip(df.low, df.high, strict=True)]
    return df[["name", "target", "realized", "bounds", "status"]].to_string(index=False)


def main(*, store: Store | None = None) -> str:
    """Run the gate; print the table; return 'PASS' or 'WARN'. Raises DataQualityError on FAIL."""
    m = read_metrics(store or get_store())
    full = m["rows"] >= load_config().thresholds.full_run_min_rows
    checks = evaluate(m, full)
    status = overall(checks)
    print(render(checks))
    manifest.update("validate", {"status": status, "mode": "full" if full else "smoke",
                                 "checks": as_rows(checks)})
    log.get("validate").info(log.kv(step="validate", mode="full" if full else "smoke", status=status))
    if status == "FAIL":
        bad = ", ".join(c.name for c in checks if c.status == "FAIL")
        raise DataQualityError(f"validation failed: {bad}")
    return status
