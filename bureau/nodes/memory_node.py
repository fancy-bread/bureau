from __future__ import annotations

from typing import Any

from bureau import events
from bureau.memory import Memory
from bureau.state import Phase


def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.MEMORY):
        run_id = state["run_id"]
        mem = Memory(run_id)
        if state.get("spec"):
            mem.write("spec_summary", state["spec"].name)

    return {**state, "phase": Phase.TASKS_LOADER}
