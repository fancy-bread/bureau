from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from bureau import events
from bureau.config import load_constitution
from bureau.memory import Memory
from bureau.models import BuildAttempt, RalphRound
from bureau.personas.critic import run_critic
from bureau.state import Escalation, EscalationReason, Phase


def critic_node(state: dict[str, Any]) -> dict[str, Any]:
    run_id = state["run_id"]
    spec_path = state["spec_path"]
    repo_path = state["repo_path"]
    repo_context = state.get("repo_context")
    ralph_round = state.get("ralph_round", 0)

    spec_text = state.get("spec_text") or Path(spec_path).read_text(encoding="utf-8")
    constitution = load_constitution(repo_path, repo_context)
    model = repo_context.critic_model if repo_context else "claude-opus-4-7"

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    mem = Memory(run_id)
    try:
        summary_dict = mem.read("builder_summary")
        builder_summary = _format_builder_summary(summary_dict)
    except KeyError:
        builder_summary = "No builder summary available."

    try:
        verdict = run_critic(
            client=client,
            spec_text=spec_text,
            constitution=constitution,
            builder_summary=builder_summary,
            ralph_round=ralph_round,
            model=model,
        )
    except Exception as exc:
        return _escalate(
            state,
            f"Critic failed to produce a verdict: {exc}",
            EscalationReason.BLOCKER,
        )

    all_attempts: list[dict] = state.get("build_attempts", [])
    round_attempts = [
        BuildAttempt.model_validate(a) for a in all_attempts if a.get("round") == ralph_round
    ]

    ralph_round_record = RalphRound(
        round=ralph_round,
        build_attempts=round_attempts,
        critic_verdict=verdict.verdict,
        critic_findings=verdict.findings,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )

    existing_ralph_rounds = list(state.get("ralph_rounds", []))
    existing_ralph_rounds.append(ralph_round_record.model_dump())

    mem.write("critic_findings", [f.model_dump() for f in verdict.findings])

    updated_state = {
        **state,
        "ralph_rounds": existing_ralph_rounds,
        "critic_findings": [f.model_dump() for f in verdict.findings],
    }

    if verdict.verdict == "pass":
        events.emit(events.PHASE_COMPLETED, phase=Phase.CRITIC, verdict="pass")
        events.emit(events.RALPH_COMPLETED, rounds=ralph_round + 1, verdict="pass")
        return {**updated_state, "phase": Phase.PR_CREATE, "_route": "pass"}

    if verdict.verdict == "escalate":
        violations = [f for f in verdict.findings if f.verdict == "violation"]
        detail = violations[0].detail if violations else verdict.summary
        return _escalate(
            updated_state,
            f"Critic detected a constitution violation: {detail}",
            EscalationReason.CONSTITUTION_VIOLATION,
        )

    # verdict == "revise"
    max_rounds = repo_context.max_ralph_rounds if repo_context else 3
    if ralph_round >= max_rounds - 1:
        unmet = [f.ref_id for f in verdict.findings if f.verdict == "unmet"]
        return _escalate(
            updated_state,
            f"Ralph Loop exceeded {max_rounds} round(s). Unresolved: {', '.join(unmet)}",
            EscalationReason.RALPH_ROUNDS_EXCEEDED,
        )

    events.emit(events.PHASE_COMPLETED, phase=Phase.CRITIC, verdict="revise", round=ralph_round)

    return {
        **updated_state,
        "ralph_round": ralph_round + 1,
        "builder_attempts": 0,
        "phase": Phase.BUILDER,
        "_route": "revise",
    }


def _format_builder_summary(summary: dict) -> str:
    lines = [f"## Builder Summary (Round {summary.get('ralph_round', '?')})\n"]
    files = summary.get("files_changed", [])
    if files:
        lines.append("### Files Changed\n")
        lines.extend(f"- {f}" for f in files)
    lines.append("\n### Test Output\n")
    lines.append(summary.get("last_test_output", "(no output)"))
    return "\n".join(lines)


def _escalate(state: dict[str, Any], reason: str, escalation_reason: EscalationReason) -> dict[str, Any]:
    what_needed = (
        "Revise the spec to remove the violating requirement."
        if escalation_reason == EscalationReason.CONSTITUTION_VIOLATION
        else "Review unresolved findings and provide guidance."
    )
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.CRITIC,
        reason=escalation_reason,
        what_happened=reason,
        what_is_needed=what_needed,
        options=[
            "Revise the spec and resume",
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
