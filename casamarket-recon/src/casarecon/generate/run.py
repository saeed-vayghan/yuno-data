"""Entry point for `recon generate`. Owner: INFRA. Milestone: M1."""

import time

from casarecon.core import log, paths
from casarecon.core.config import load_config
from casarecon.generate import dataset, writer


def main(rows: int | None = None, seed: int | None = None) -> None:
    """Called by cli.py. Raise core errors (DataQualityError -> exit 5); return normally on success."""
    started = time.perf_counter()
    cfg = load_config()
    g = cfg.generator.model_dump()
    g["rows"] = rows if rows is not None else g["rows"]
    g["seed"] = seed if seed is not None else g["seed"]
    if g["rows"] < 1:
        raise ValueError("rows must be >= 1")
    ds = dataset.build(g, cfg.thresholds.model_dump())
    written = writer.write_all(ds, paths.raw_dir(), paths.truth_dir())
    log.get("generate").info(log.kv(
        step="generate", rows=g["rows"], seed=g["seed"], secs=round(time.perf_counter() - started, 1),
        buckets=ds.manifest["realized"]["buckets"], out=written["transactions"].parent,
    ))
