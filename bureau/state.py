from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

from bureau.config import DEFAULT_BUILDER_MODEL, DEFAULT_REVIEWER_MODEL


class Phase(StrEnum):
    VALIDATE_SPEC = "validate_spec"
    REPO_ANALYSIS = "repo_analysis"
    MEMORY = "memory"
    TASKS_LOADER = "tasks_loader"
    PREPARE_BRANCH = "prepare_branch"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    COMPLETE_BRANCH = "complete_branch"
    PR_CREATE = "pr_create"
    ESCALATE = "escalate"
    COMPLETE = "complete"
    FAILED = "failed"


class RunStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"
    ABORTED = "aborted"


class EscalationReason(StrEnum):
    SPEC_INVALID = "SPEC_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"
    BLOCKER = "BLOCKER"
    CONSTITUTION_CRITICAL = "CONSTITUTION_CRITICAL"
    MAX_RETRIES = "MAX_RETRIES"
    PLAN_INCOMPLETE = "PLAN_INCOMPLETE"
    RALPH_EXHAUSTED = "RALPH_EXHAUSTED"
    RALPH_ROUNDS_EXCEEDED = "RALPH_ROUNDS_EXCEEDED"
    CONSTITUTION_VIOLATION = "CONSTITUTION_VIOLATION"
    PR_FAILED = "PR_FAILED"
    DIRTY_REPO = "DIRTY_REPO"
    GIT_PUSH_FAILED = "GIT_PUSH_FAILED"
    GIT_BRANCH_EXISTS = "GIT_BRANCH_EXISTS"
    TASKS_MISSING = "TASKS_MISSING"
    TASKS_COMPLETE = "TASKS_COMPLETE"


@dataclass
class UserStory:
    title: str
    priority: str
    description: str
    acceptance_scenarios: list[str] = field(default_factory=list)


@dataclass
class FunctionalRequirement:
    id: str
    text: str
    needs_clarification: bool = False


@dataclass
class Spec:
    name: str
    branch: str
    status: str
    user_stories: list[UserStory] = field(default_factory=list)
    functional_requirements: list[FunctionalRequirement] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class RepoContext:
    language: str
    base_image: str
    install_cmd: str
    test_cmd: str
    build_cmd: str = ""
    lint_cmd: str = ""
    max_builder_attempts: int = 3
    max_ralph_rounds: int = 3
    command_timeout: int = 300
    builder_model: str = DEFAULT_BUILDER_MODEL
    reviewer_model: str = DEFAULT_REVIEWER_MODEL


@dataclass
class Escalation:
    run_id: str
    phase: Phase
    reason: EscalationReason
    what_happened: str
    what_is_needed: str
    options: list[str]
    timestamp: str


@dataclass
class RunRecord:
    run_id: str
    spec_path: str
    repo_path: str
    status: RunStatus
    current_phase: Phase
    started_at: str
    updated_at: str
    pr_url: Optional[str] = None


def make_initial_state(
    run_id: str,
    spec_path: str,
    repo_path: str,
    spec_folder: str = "",
    tasks_path: str = "",
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "spec_path": spec_path,
        "repo_path": repo_path,
        "phase": Phase.VALIDATE_SPEC,
        "spec": None,
        "spec_text": "",
        "repo_context": None,
        "escalations": [],
        "decisions": [],
        "messages": [],
        "task_plan": None,
        "ralph_round": 0,
        "builder_attempts": 0,
        "build_attempts": [],
        "ralph_rounds": [],
        "reviewer_findings": [],
        "run_summary": None,
        "branch_name": "",
        "spec_folder": spec_folder,
        "tasks_path": tasks_path,
        "plan_text": "",
    }
