from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Generator

RUN_STARTED = "run.started"
RUN_COMPLETED = "run.completed"
RUN_ESCALATED = "run.escalated"
RUN_FAILED = "run.failed"
PHASE_STARTED = "phase.started"
PHASE_COMPLETED = "phase.completed"
RALPH_STARTED = "ralph.started"
RALPH_ATTEMPT = "ralph.attempt"
RALPH_COMPLETED = "ralph.completed"
BUILDER_TOOL = "builder.tool"


def emit(event: str, **kwargs: Any) -> None:
    """Print a structured bureau run event to stdout."""
    parts = [f"[bureau] {event}"]
    for key, value in kwargs.items():
        parts.append(f"{key}={value}")
    print("  ".join(parts[:1]) + ("  " + "  ".join(parts[1:]) if len(parts) > 1 else ""), flush=True)


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
