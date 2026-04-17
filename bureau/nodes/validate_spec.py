from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bureau import events
from bureau.spec_parser import SpecParseError, parse_spec
from bureau.state import Escalation, EscalationReason, Phase


def validate_spec_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.VALIDATE_SPEC):
        run_id = state["run_id"]
        spec_path = state["spec_path"]

        try:
            spec = parse_spec(spec_path)
        except SpecParseError as exc:
            return _escalate(state, str(exc))

        p1_stories = [s for s in spec.user_stories if s.priority == "P1"]
        if not p1_stories:
            return _escalate(state, "Spec has no P1 user stories.")

        needs_clarification = [
            fr.id for fr in spec.functional_requirements if fr.needs_clarification
        ]
        if needs_clarification:
            return _escalate(
                state,
                f"Spec contains [NEEDS CLARIFICATION] markers in: {', '.join(needs_clarification)}",
            )

    return {**state, "spec": spec, "phase": Phase.REPO_ANALYSIS, "_route": "ok"}


def _escalate(state: dict[str, Any], reason: str) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.VALIDATE_SPEC,
        reason=EscalationReason.SPEC_INVALID,
        what_happened=reason,
        what_is_needed="Resolve the spec issue before running bureau.",
        options=[
            "Edit spec.md and remove all [NEEDS CLARIFICATION] markers or fix missing sections",
            "Run /speckit-clarify to resolve ambiguities interactively",
        ],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        **state,
        "escalations": state.get("escalations", []) + [escalation],
        "phase": Phase.ESCALATE,
        "_route": "escalate",
    }
