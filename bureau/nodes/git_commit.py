from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bureau import events
from bureau.state import Escalation, EscalationReason, Phase


def git_commit_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.GIT_COMMIT):
        run_id = state["run_id"]
        repo_path = state["repo_path"]
        spec = state.get("spec")

        if spec:
            raw_name = spec.name
        else:
            # Use parent dir name (e.g. "001-smoke-hello-world"), strip leading "NNN-" prefix
            parent = Path(state["spec_path"]).parent.name
            raw_name = re.sub(r"^\d+-", "", parent)
        spec_name = re.sub(r"[^a-z0-9]+", "-", raw_name.lower()).strip("-")[:40]

        run_id_prefix = run_id.removeprefix("run-")[:8]

        branch_name = f"feat/{spec_name}-{run_id_prefix}"
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

        subprocess.run(["git", "-C", repo_path, "add", "-A"], check=True)

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

    return {**state, "branch_name": branch_name, "phase": Phase.PR_CREATE, "_route": "ok"}


def _escalate(state: dict[str, Any], what_happened: str, reason: EscalationReason) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.GIT_COMMIT,
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
