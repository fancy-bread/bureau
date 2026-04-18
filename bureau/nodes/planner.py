from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from bureau import events
from bureau.config import load_constitution
from bureau.memory import Memory
from bureau.personas.planner import run_planner
from bureau.state import Escalation, EscalationReason, Phase


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.PLANNER):
        run_id = state["run_id"]
        spec_path = state["spec_path"]
        repo_path = state["repo_path"]
        repo_context = state.get("repo_context")

        spec_text = state.get("spec_text") or Path(spec_path).read_text(encoding="utf-8")
        constitution = load_constitution(repo_path, repo_context)
        model = repo_context.planner_model if repo_context else "claude-opus-4-7"

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        try:
            task_plan = run_planner(
                client=client,
                spec_text=spec_text,
                constitution=constitution,
                repo_path=repo_path,
                model=model,
            )
        except Exception as exc:
            return _escalate(state, f"Planner failed: {exc}", EscalationReason.BLOCKER)

        spec = state.get("spec")
        if spec:
            p1_frs = {fr.id for fr in spec.functional_requirements}
            covered = set(task_plan.fr_coverage)
            uncovered_p1 = (p1_frs - covered) | set(task_plan.uncovered_frs)
            if uncovered_p1:
                return _escalate(
                    state,
                    f"Planner could not map all P1 FRs to tasks. Uncovered: "
                    f"{', '.join(sorted(uncovered_p1))}",
                    EscalationReason.PLAN_INCOMPLETE,
                )

        mem = Memory(run_id)
        mem.write("task_plan", task_plan.model_dump())

    return {
        **state,
        "task_plan": task_plan.model_dump(),
        "phase": Phase.BUILDER,
        "_route": "ok",
    }


def _escalate(
    state: dict[str, Any], reason: str, escalation_reason: EscalationReason
) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.PLANNER,
        reason=escalation_reason,
        what_happened=reason,
        what_is_needed="Review the spec and ensure all P1 FRs are addressable given the codebase.",
        options=[
            "Revise the spec to clarify unresolvable requirements and resume",
            "Abort this run with `bureau abort <run-id>`",
        ],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        **state,
        "escalations": state.get("escalations", []) + [escalation],
        "phase": Phase.ESCALATE,
        "_route": "escalate",
    }
