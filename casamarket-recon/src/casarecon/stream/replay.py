"""`recon stream replay`: raw transactions CSV -> auth / settlement events on Redpanda, in event-time order."""

import csv
from pathlib import Path

from casarecon.core import log, paths
from casarecon.core.errors import InputMissing
from casarecon.stream import events as ev
from casarecon.stream.kafka_io import publish


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise InputMissing(f"{path} is missing: run `recon generate` first")
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main(speed: float = 86400.0, limit: int | None = None, bootstrap: str = "localhost:19092") -> dict:
    """Publish the first `limit` events; `speed` = event seconds per wall second (0 = as fast as possible)."""
    events = ev.build_events(read_rows(paths.raw_dir() / "transactions.csv"), limit)
    sent = publish(events, ev.wall_offsets(events, speed), bootstrap)
    out = {"events": sent,
           "auths": sum(e.topic == ev.AUTHS for e in events),
           "settlements": sum(e.topic == ev.SETTLEMENTS for e in events),
           "from": str(events[0].ts) if events else None, "to": str(events[-1].ts) if events else None}
    log.get("stream").info(log.kv(**out))
    return out
