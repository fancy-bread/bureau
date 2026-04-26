from __future__ import annotations

from typing import Any

from bureau import events
from bureau.run_manager import get_run, write_run_record, write_run_summary
from bureau.state import Escalation, Phase, RunStatus


def escalate_node(state: dict[str, Any]) -> dict[str, Any]:
    run_id = state["run_id"]
    escalations: list[Escalation] = state.get("escalations", [])

    if escalations:
        esc = escalations[-1]
        events.emit(
            events.RUN_ESCALATED,
            id=run_id,
            phase=esc.phase,
            reason=esc.reason,
            what_happened=esc.what_happened[:1000],
            what_is_needed=esc.what_is_needed,
        )
        if not events.is_cloudevents_mode():
            print()
            print(f"  What happened:  {esc.what_happened}")
            print(f"  What's needed:  {esc.what_is_needed}")
            print("  Options:")
            for i, opt in enumerate(esc.options, 1):
                print(f"    {i}. {opt}")
            print()
            print(f'  Resume: bureau resume {run_id} --response "..."')
    else:
        events.emit(
            events.RUN_ESCALATED, id=run_id, phase=state.get("phase", "unknown"), reason="UNKNOWN"
        )

    try:
        record = get_run(run_id)
        record.status = RunStatus.PAUSED
        record.current_phase = Phase.ESCALATE
        write_run_record(record)
    except Exception:
        pass

    write_run_summary(state, "escalated")

    return {**state, "phase": Phase.ESCALATE}
