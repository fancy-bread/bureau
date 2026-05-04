from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bureau import events
from bureau.state import Escalation, EscalationReason, Phase


def complete_branch_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.COMPLETE_BRANCH):
        run_id = state["run_id"]
        repo_path = state["repo_path"]
        branch_name = state["branch_name"]
        spec = state.get("spec")

        if spec:
            raw_name = spec.name
        else:
            parent = Path(state["spec_path"]).parent.name
            raw_name = re.sub(r"^\d+-", "", parent)
        spec_name = re.sub(r"[^a-z0-9]+", "-", raw_name.lower()).strip("-")[:40]
        run_id_prefix = run_id.removeprefix("run-")[:8]

        subprocess.run(["git", "-C", repo_path, "add", "-A"], check=True)

        # Builder may have committed everything incrementally — only commit if there are staged changes.
        status = subprocess.run(
            ["git", "-C", repo_path, "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if status.returncode != 0:
            commit_msg = f"feat: {spec_name} [bureau/{run_id_prefix}]"
            subprocess.run(
                ["git", "-C", repo_path, "commit", "-m", commit_msg],
                check=True,
            )

        _git_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            push_result = subprocess.run(
                ["git", "-C", repo_path, "push", "origin", branch_name],
                capture_output=True,
                text=True,
                env=_git_env,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return _escalate(
                state,
                "git push timed out after 120s — check network and remote credentials",
                EscalationReason.GIT_PUSH_FAILED,
            )
        if push_result.returncode != 0:
            return _escalate(
                state,
                f"git push failed: {push_result.stderr.strip()}",
                EscalationReason.GIT_PUSH_FAILED,
            )

    return {**state, "phase": Phase.PR_CREATE, "_route": "ok"}


def _escalate(state: dict[str, Any], what_happened: str, reason: EscalationReason) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.COMPLETE_BRANCH,
        reason=reason,
        what_happened=what_happened,
        what_is_needed="Resolve the git issue in the target repo before retrying.",
        options=[
            "Check git remote configuration with `git remote -v`",
            "Verify push permissions with `gh auth status`",
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
