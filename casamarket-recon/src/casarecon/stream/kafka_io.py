"""The one Kafka adapter of `stream` (kafka-python, imported lazily). Redpanda speaks the Kafka API.

Not a project dependency yet: run with `uv run --with kafka-python recon stream ...`.
"""

import json
import time
from collections.abc import Sequence
from typing import Any

from casarecon.core.errors import CasaReconError
from casarecon.stream.events import Event


def _kafka() -> Any:
    try:
        import kafka
    except ModuleNotFoundError as e:
        raise CasaReconError("kafka-python is missing: use `uv run --with kafka-python recon stream ...`") from e
    return kafka


def publish(events: Sequence[Event], offsets: Sequence[float], bootstrap: str) -> int:
    """Send each event at start + its wall offset (JSON value, key = transaction_id). Returns count."""
    producer = _kafka().KafkaProducer(
        bootstrap_servers=bootstrap, linger_ms=20, acks=1,
        key_serializer=str.encode, value_serializer=lambda v: json.dumps(v).encode())
    start = time.monotonic()
    for event, offset in zip(events, offsets, strict=True):
        wait = start + offset - time.monotonic()
        if wait > 0.01:
            time.sleep(wait)
        producer.send(event.topic, key=event.key, value=event.value,
                      timestamp_ms=int(event.ts.timestamp() * 1000))
    producer.flush()
    producer.close()
    return len(events)


def consume(topic: str, bootstrap: str, limit: int, timeout_s: float) -> list[dict]:
    """Up to `limit` JSON messages from the start of `topic`; stops after `timeout_s` without data."""
    consumer = _kafka().KafkaConsumer(
        topic, bootstrap_servers=bootstrap, auto_offset_reset="earliest", enable_auto_commit=False,
        consumer_timeout_ms=int(timeout_s * 1000), value_deserializer=json.loads)
    try:
        return [msg.value for _, msg in zip(range(limit), consumer, strict=False)]
    finally:
        consumer.close()
