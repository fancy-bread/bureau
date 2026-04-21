from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bureau import events
from bureau.models import Task, TaskPlan
from bureau.state import Escalation, EscalationReason, Phase


def tasks_loader_node(state: dict[str, Any]) -> dict[str, Any]:
    tasks_path_str = state.get("tasks_path", "")

    events.emit(events.PHASE_STARTED, phase=Phase.TASKS_LOADER)
    start = time.monotonic()

    if not tasks_path_str:
        spec_folder = state.get("spec_folder", "")
        tasks_path_str = str(Path(spec_folder) / "tasks.md") if spec_folder else ""

    tasks_path = Path(tasks_path_str) if tasks_path_str else None

    if not tasks_path or not tasks_path.exists():
        return _escalate(
            state,
            EscalationReason.TASKS_MISSING,
            f"tasks.md not found at {tasks_path_str}",
            "Run /speckit-tasks to generate tasks.md before invoking bureau.",
        )

    content = tasks_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    incomplete_lines = [ln for ln in lines if re.match(r"^- \[ \] ", ln)]
    complete_lines = [ln for ln in lines if re.match(r"^- \[x\] ", ln, re.IGNORECASE)]

    if not incomplete_lines:
        if complete_lines:
            return _escalate(
                state,
                EscalationReason.TASKS_COMPLETE,
                "tasks.md exists but all tasks are already complete.",
                "Nothing to build. If this is a re-run, reset tasks or create a new spec.",
            )
        return _escalate(
            state,
            EscalationReason.TASKS_MISSING,
            f"tasks.md at {tasks_path_str} contains no parseable task items.",
            "Run /speckit-tasks to generate tasks.md before invoking bureau.",
        )

    tasks: list[Task] = []
    for i, line in enumerate(incomplete_lines):
        description = re.sub(r"^- \[ \] ", "", line)
        match = re.search(r"T\d+", description)
        task_id = match.group(0) if match else f"T{i + 1:03d}"
        tasks.append(Task(id=task_id, description=description, fr_ids=[], done=False))

    spec_folder_path = Path(state.get("spec_folder", "") or tasks_path.parent)
    spec_name = re.sub(r"^\d+-", "", spec_folder_path.name)

    plan_text = ""
    plan_md = spec_folder_path / "plan.md"
    if plan_md.exists():
        plan_text = plan_md.read_text(encoding="utf-8")

    task_plan = TaskPlan(
        tasks=tasks,
        spec_name=spec_name,
        fr_coverage=[],
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    duration = time.monotonic() - start
    events.emit(
        events.PHASE_COMPLETED, phase=Phase.TASKS_LOADER,
        duration=f"{duration:.1f}s", tasks=len(tasks),
    )

    return {
        **state,
        "task_plan": task_plan.model_dump(),
        "plan_text": plan_text,
        "phase": Phase.BUILDER,
        "_route": "ok",
    }


def _escalate(
    state: dict[str, Any],
    reason: EscalationReason,
    what_happened: str,
    what_is_needed: str,
) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.TASKS_LOADER,
        reason=reason,
        what_happened=what_happened,
        what_is_needed=what_is_needed,
        options=["Run /speckit-tasks in the spec folder", f"bureau abort {state['run_id']}"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        **state,
        "escalations": state.get("escalations", []) + [escalation],
        "phase": Phase.ESCALATE,
        "_route": "escalate",
    }
