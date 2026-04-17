from __future__ import annotations

from typing import Any

from bureau import events
from bureau.memory import Memory
from bureau.state import Phase

_STUB_MSG = "[STUB] critic findings — real implementation pending"


def critic_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.CRITIC, stub=True):
        mem = Memory(state["run_id"])
        mem.write("critic_findings", _STUB_MSG)

    return {**state, "phase": Phase.PR_CREATE, "_route": "pass"}
