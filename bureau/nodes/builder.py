from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from bureau import events
from bureau.config import load_constitution
from bureau.memory import Memory
from bureau.models import BuildAttempt, TaskPlan
from bureau.personas.builder import run_builder_attempt
from bureau.state import Escalation, EscalationReason, Phase
from bureau.tools.shell_tools import execute_shell_tool


def builder_node(state: dict[str, Any]) -> dict[str, Any]:
    run_id = state["run_id"]
    spec_path = state["spec_path"]
    repo_path = state["repo_path"]
    repo_context = state.get("repo_context")
    ralph_round = state.get("ralph_round", 0)

    spec_text = state.get("spec_text") or Path(spec_path).read_text(encoding="utf-8")
    constitution = load_constitution(repo_path, repo_context)

    max_attempts = repo_context.max_builder_attempts if repo_context else 3
    test_cmd = repo_context.test_cmd if repo_context else "pytest"
    build_cmd = repo_context.build_cmd if repo_context else ""
    install_cmd = repo_context.install_cmd if repo_context else ""
    model = repo_context.builder_model if repo_context else "claude-sonnet-4-6"
    timeout = repo_context.command_timeout if repo_context else 300

    task_plan_dict = state.get("task_plan")
    task_plan_text = _format_task_plan(task_plan_dict)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Run install_cmd once at round start
    if install_cmd:
        raw = execute_shell_tool("run_command", {"command": install_cmd}, repo_path, timeout)
        parsed = json.loads(raw)
        if parsed["exit_code"] != 0:
            return _escalate(
                state,
                f"install_cmd failed (exit {parsed['exit_code']}): {parsed['stderr'][-2000:]}",
                EscalationReason.RALPH_EXHAUSTED,
            )

    events.emit(events.RALPH_STARTED, phase="builder", round=ralph_round)

    existing_attempts: list[dict] = list(state.get("build_attempts", []))
    round_attempts: list[BuildAttempt] = []

    passed = False
    for attempt_num in range(max_attempts):
        attempt = run_builder_attempt(
            client=client,
            spec_text=spec_text,
            task_plan_text=task_plan_text,
            constitution=constitution,
            test_cmd=test_cmd,
            build_cmd=build_cmd,
            repo_path=repo_path,
            model=model,
            ralph_round=ralph_round,
            attempt_num=attempt_num,
            previous_attempts=round_attempts,
            timeout=timeout,
        )
        round_attempts.append(attempt)
        existing_attempts.append(attempt.model_dump())

        events.emit(
            events.RALPH_ATTEMPT,
            phase="builder",
            round=ralph_round,
            attempt=attempt_num,
            result="pass" if attempt.passed else "fail",
        )

        if attempt.passed:
            passed = True
            break

    if not passed:
        last_output = round_attempts[-1].test_output if round_attempts else ""
        return _escalate(
            state,
            f"Builder exhausted {max_attempts} attempt(s) in round {ralph_round} without "
            f"a passing test run. Last test output: {last_output[-1000:]}",
            EscalationReason.RALPH_EXHAUSTED,
        )

    mem = Memory(run_id)
    mem.write(
        "builder_summary",
        {
            "ralph_round": ralph_round,
            "files_changed": round_attempts[-1].files_changed,
            "last_test_output": round_attempts[-1].test_output,
            "attempts": [a.model_dump() for a in round_attempts],
        },
    )

    return {
        **state,
        "build_attempts": existing_attempts,
        "builder_attempts": len(round_attempts),
        "phase": Phase.CRITIC,
    }


def _format_task_plan(task_plan_dict: dict | None) -> str:
    if not task_plan_dict:
        return "No task plan available."
    try:
        plan = TaskPlan.model_validate(task_plan_dict)
        lines = [f"## Task Plan: {plan.spec_name}\n"]
        for task in plan.tasks:
            deps = f" (depends on: {', '.join(task.depends_on)})" if task.depends_on else ""
            frs = f" [{', '.join(task.fr_ids)}]"
            lines.append(f"- [{task.id}]{frs}{deps}: {task.description}")
        return "\n".join(lines)
    except Exception:
        return str(task_plan_dict)


def _escalate(
    state: dict[str, Any], reason: str, escalation_reason: EscalationReason
) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.BUILDER,
        reason=escalation_reason,
        what_happened=reason,
        what_is_needed="Review the failing tests and provide guidance on the approach.",
        options=[
            "Add the required context to the spec and resume",
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
