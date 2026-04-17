from __future__ import annotations

from typing import Any

from bureau import events
from bureau.state import Phase

_STUB_URL = "[STUB] PR URL — real implementation pending"


def pr_create_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.PR_CREATE, stub=True):
        print(f"  pr_url={_STUB_URL}")

    return {**state, "phase": Phase.COMPLETE}
