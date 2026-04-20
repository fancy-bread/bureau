from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Any

from bureau import events
from bureau.memory import Memory
from bureau.repo_analyser import ConfigInvalidError, ConfigMissingError, parse_repo_config
from bureau.state import Escalation, EscalationReason, Phase


def repo_analysis_node(state: dict[str, Any]) -> dict[str, Any]:
    with events.phase(Phase.REPO_ANALYSIS):
        run_id = state["run_id"]
        repo_path = state["repo_path"]

        try:
            repo_context = parse_repo_config(repo_path)
        except ConfigMissingError as exc:
            return _escalate(state, str(exc), EscalationReason.CONFIG_MISSING)
        except ConfigInvalidError as exc:
            return _escalate(state, str(exc), EscalationReason.CONFIG_MISSING)

        dirty_result = subprocess.run(
            ["git", "-C", repo_path, "diff", "--quiet", "HEAD"],
            capture_output=True,
        )
        untracked_result = subprocess.run(
            ["git", "-C", repo_path, "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
        )
        if dirty_result.returncode != 0 or untracked_result.stdout.strip():
            tracked_diff = subprocess.run(
                ["git", "-C", repo_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
            )
            file_list = tracked_diff.stdout.strip() or untracked_result.stdout.strip()
            return _escalate_dirty(
                state,
                f"Target repo has uncommitted changes:\n{file_list}",
            )

        mem = Memory(run_id)
        mem.write("repo_context", repo_context.__dict__)

    return {**state, "repo_context": repo_context, "phase": Phase.MEMORY, "_route": "ok"}


def _escalate(
    state: dict[str, Any], reason: str, escalation_reason: EscalationReason
) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.REPO_ANALYSIS,
        reason=escalation_reason,
        what_happened=reason,
        what_is_needed="A valid .bureau/config.toml with all required fields.",
        options=[
            "Run `bureau init --repo <path>` to scaffold the config file",
            "Manually create .bureau/config.toml with language, base_image, install_cmd, test_cmd",
        ],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        **state,
        "escalations": state.get("escalations", []) + [escalation],
        "phase": Phase.ESCALATE,
        "_route": "escalate",
    }


def _escalate_dirty(state: dict[str, Any], what_happened: str) -> dict[str, Any]:
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.REPO_ANALYSIS,
        reason=EscalationReason.DIRTY_REPO,
        what_happened=what_happened,
        what_is_needed="Commit, stash, or discard changes in the target repo before running bureau.",
        options=[
            "git stash && bureau resume <run-id>",
            "git checkout . && git clean -fd to discard all changes",
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
