"""Pure event building for the replay: raw transaction rows -> ordered auth / settlement events.

Every row gives one `auths` event at auth_ts (status `authorized`, or `failed`). Settled rows also
give one `settlements` event at settle_ts. Events are ordered by event time (auth first on a tie),
keyed by transaction_id, and carry JSON-ready values (ints, bools, "YYYY-MM-DD HH:MM:SS").
"""

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, NamedTuple

AUTHS, SETTLEMENTS = "auths", "settlements"
TS_FMT = "%Y-%m-%d %H:%M:%S"
AUTH_FIELDS = ("psp", "country", "currency", "payer_currency")
DEFAULT_MERCHANT = "casamarket"  # contract default when the column is missing or empty


class Event(NamedTuple):
    ts: datetime          # event time (merchant local)
    topic: str
    key: str              # transaction_id
    value: dict[str, Any]


def _bool(v: Any) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "1")


def _ts(v: Any) -> datetime:
    return v if isinstance(v, datetime) else datetime.strptime(str(v).strip(), TS_FMT)  # noqa: DTZ007 (naive = merchant local time)


def row_events(row: Mapping[str, Any]) -> list[Event]:
    """One raw row -> its auth event (+ settlement event when settled)."""
    auth_ts, status = _ts(row["auth_ts"]), str(row["status"]).strip().lower()
    txn = str(row["transaction_id"])
    auth = {"transaction_id": txn, "merchant_id": row.get("merchant_id") or DEFAULT_MERCHANT,
            **{f: str(row[f]) for f in AUTH_FIELDS},
            "is_cross_border": _bool(row["is_cross_border"]),
            "authorized_amount": int(row["authorized_amount"]),
            "auth_ts": auth_ts.strftime(TS_FMT),
            "status": "failed" if status == "failed" else "authorized"}
    events = [Event(auth_ts, AUTHS, txn, auth)]
    if status == "settled":
        settle_ts = _ts(row["settle_ts"])
        events.append(Event(settle_ts, SETTLEMENTS, txn, {
            "transaction_id": txn, "psp": str(row["psp"]), "currency": str(row["currency"]),
            "settled_amount": int(row["settled_amount"]), "settle_ts": settle_ts.strftime(TS_FMT)}))
    return events


def build_events(rows: Iterable[Mapping[str, Any]], limit: int | None = None) -> list[Event]:
    """All events in event-time order (auth before settlement on a tie), cut to the first `limit`."""
    events = sorted((e for r in rows for e in row_events(r)),
                    key=lambda e: (e.ts, e.topic != AUTHS, e.key))
    return events[:limit] if limit else events


def wall_offsets(events: list[Event], speed: float) -> list[float]:
    """Seconds after start at which each event is sent: event time compressed by `speed` (0 = no wait)."""
    if not events or speed <= 0:
        return [0.0] * len(events)
    t0 = events[0].ts
    return [(e.ts - t0).total_seconds() / speed for e in events]
