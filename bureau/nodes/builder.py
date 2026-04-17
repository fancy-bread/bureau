from __future__ import annotations

from typing import Any

from bureau import events
from bureau.memory import Memory
from bureau.state import Phase

_STUB_MSG = "[STUB] builder output — real implementation pending"


def builder_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.BUILDER, stub=True):
        mem = Memory(state["run_id"])
        mem.write("implementation_notes", _STUB_MSG)

    return {**state, "phase": Phase.CRITIC, "_route": "ok"}
