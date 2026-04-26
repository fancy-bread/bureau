from __future__ import annotations

import atexit
import os
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cloudevents.v1.conversion import to_json
from cloudevents.v1.http import CloudEvent

_INSTANCE_ID: str = os.environ.get("BUREAU_INSTANCE_ID", "").strip() or str(uuid4())
_TOPIC: str = os.environ.get("BUREAU_KAFKA_TOPIC", "bureau.runs")
_producer = None  # confluent_kafka.Producer | None


def _init() -> None:
    global _producer
    servers = os.environ.get("BUREAU_KAFKA_BOOTSTRAP_SERVERS", "").strip()
    if not servers:
        return
    from confluent_kafka import Producer  # type: ignore[import-untyped]

    _producer = Producer({"bootstrap.servers": servers, "acks": "0"})


def _flush() -> None:
    if _producer is not None:
        _producer.flush(timeout=0)


_init()
atexit.register(_flush)


def is_kafka_enabled() -> bool:
    return _producer is not None


def publish(event: str, run_id: str, **kwargs: Any) -> None:
    if _producer is None:
        return
    try:
        ce = CloudEvent(
            attributes={
                "type": f"com.fancybread.bureau.{event}",
                "source": f"urn:bureau:instance:{_INSTANCE_ID}:run:{run_id}",
                "id": str(uuid4()),
                "time": datetime.now(timezone.utc).isoformat(),
                "datacontenttype": "application/json",
            },
            data=kwargs or {},
        )
        _producer.produce(_TOPIC, key=run_id.encode(), value=to_json(ce))
    except Exception as e:
        print(f"[bureau/kafka] publish failed: {e}", file=sys.stderr)
