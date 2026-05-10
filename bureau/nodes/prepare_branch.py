from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bureau import events
from bureau.state import Escalation, EscalationReason, Phase


def _derive_branch_name(state: dict[str, Any]) -> str:
    run_id = state["run_id"]
    folder_name = Path(state["spec_path"]).parent.name
    spec_name = re.sub(r"[^a-z0-9]+", "-", folder_name.lower()).strip("-")[:40]
    run_id_prefix = run_id.removeprefix("run-")[:8]
    return f"feat/{spec_name}-{run_id_prefix}"


def prepare_branch_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.PREPARE_BRANCH):
        repo_path = state["repo_path"]
        branch_name = _derive_branch_name(state)

        for attempt in range(1, 4):
            candidate = branch_name if attempt == 1 else f"{branch_name}-{attempt}"
            result = subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", candidate],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                branch_name = candidate
                break
            if "already exists" in result.stderr:
                continue
            return _escalate(
                state,
                f"git checkout -b failed: {result.stderr.strip()}",
                EscalationReason.GIT_BRANCH_EXISTS,
            )
        else:
            return _escalate(
                state,
                f"Branch name collision after 3 attempts: {branch_name}",
                EscalationReason.GIT_BRANCH_EXISTS,
            )

    return {**state, "branch_name": branch_name, "_route": "ok"}


def _escalate(state: dict[str, Any], what_happened: str, reason: EscalationReason) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.PREPARE_BRANCH,
        reason=reason,
        what_happened=what_happened,
        what_is_needed="Resolve the git issue in the target repo before retrying.",
        options=[
            "Delete the conflicting branch or reset the repo",
            "bureau abort <run-id>",
        ],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        **state,
        "escalations": state.get("escalations", []) + [escalation],
        "phase": Phase.ESCALATE,
        "_route": "escalate",
    }
