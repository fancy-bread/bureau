from __future__ import annotations

from typing import Any

from bureau import events
from bureau.memory import Memory
from bureau.state import Phase

_STUB_MSG = "[STUB] planner output — real implementation pending"


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.PLANNER, stub=True):
        mem = Memory(state["run_id"])
        mem.write("plan", _STUB_MSG)
        mem.write("task_list", _STUB_MSG)
        mem.write("constitution_self_check", _STUB_MSG)

    return {**state, "phase": Phase.BUILDER, "_route": "ok"}
