from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generator
from uuid import uuid4

from cloudevents.v1.conversion import to_json
from cloudevents.v1.http import CloudEvent

RUN_STARTED = "run.started"
RUN_COMPLETED = "run.completed"
PR_CREATED = "pr.created"
RUN_ESCALATED = "run.escalated"
RUN_FAILED = "run.failed"
PHASE_STARTED = "phase.started"
PHASE_COMPLETED = "phase.completed"
RALPH_STARTED = "ralph.started"
RALPH_ATTEMPT = "ralph.attempt"
RALPH_COMPLETED = "ralph.completed"
BUILDER_TOOL = "builder.tool"


class OutputFormat(Enum):
    TEXT = "text"
    CLOUDEVENTS = "cloudevents"


_FORMAT = OutputFormat(os.environ.get("BUREAU_OUTPUT_FORMAT", "text").lower())

_source_uri: str = os.environ.get("BUREAU_SOURCE_URI", "urn:bureau:run:unknown")


def _register_run(run_id: str) -> None:
    global _source_uri
    if not os.environ.get("BUREAU_SOURCE_URI"):
        _source_uri = f"urn:bureau:run:{run_id}"


def is_cloudevents_mode() -> bool:
    return _FORMAT == OutputFormat.CLOUDEVENTS


def _emit_cloudevents(event: str, **kwargs: Any) -> None:
    if event == RUN_STARTED and "id" in kwargs:
        _register_run(kwargs["id"])
    ce = CloudEvent(
        attributes={
            "type": f"com.fancybread.bureau.{event}",
            "source": _source_uri,
            "id": str(uuid4()),
            "time": datetime.now(timezone.utc).isoformat(),
            "datacontenttype": "application/json",
        },
        data=kwargs or {},
    )
    print(to_json(ce).decode(), flush=True)


def emit(event: str, **kwargs: Any) -> None:
    if _FORMAT == OutputFormat.CLOUDEVENTS:
        _emit_cloudevents(event, **kwargs)
    else:
        parts = [f"[bureau] {event}"]
        for key, value in kwargs.items():
            parts.append(f"{key}={value}")
        print("  ".join(parts[:1]) + ("  " + "  ".join(parts[1:]) if len(parts) > 1 else ""), flush=True)

    from bureau import kafka_publisher

    if kafka_publisher.is_kafka_enabled():
        run_id = kwargs.get("id", "unknown")
        kafka_publisher.publish(event, str(run_id), **kwargs)


@contextmanager
def phase(name: str, stub: bool = False) -> Generator[None, None, None]:
    """Context manager that emits phase.started / phase.completed around a block."""
    kwargs: dict[str, Any] = {"phase": name}
    if stub:
        kwargs["stub"] = "true"
    emit(PHASE_STARTED, **kwargs)
    start = time.monotonic()
    yield
    duration = time.monotonic() - start
    completed_kwargs: dict[str, Any] = {"phase": name, "duration": f"{duration:.1f}s"}
    if stub:
        completed_kwargs["stub"] = "true"
    emit(PHASE_COMPLETED, **completed_kwargs)
