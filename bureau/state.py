from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional


class Phase(StrEnum):
    VALIDATE_SPEC = "validate_spec"
    REPO_ANALYSIS = "repo_analysis"
    MEMORY = "memory"
    PLANNER = "planner"
    BUILDER = "builder"
    CRITIC = "critic"
    GIT_COMMIT = "git_commit"
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
    constitution_path: Optional[str] = None
    max_builder_attempts: int = 3
    max_ralph_rounds: int = 3
    command_timeout: int = 300
    planner_model: str = "claude-opus-4-7"
    builder_model: str = "claude-sonnet-4-6"
    critic_model: str = "claude-opus-4-7"


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


class RunState(dict):
    """LangGraph state for a bureau run. Extends dict for TypedDict compatibility."""


def make_initial_state(run_id: str, spec_path: str, repo_path: str) -> dict[str, Any]:
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
        "critic_findings": [],
        "run_summary": None,
        "branch_name": "",
    }
