from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class PipelinePhase(StrEnum):
    INSTALL = "install"
    LINT = "lint"
    BUILD = "build"
    TEST = "test"


class PipelineResult(BaseModel):
    passed: bool
    failed_phase: Optional[PipelinePhase] = None
    failed_output: str = ""
    phases_run: list[PipelinePhase] = []


class Task(BaseModel):
    id: str
    description: str
    fr_ids: list[str]
    depends_on: list[str] = []
    files_affected: list[str] = []
    done: bool = False


class TaskPlan(BaseModel):
    tasks: list[Task]
    spec_name: str
    fr_coverage: list[str]
    uncovered_frs: list[str] = []
    created_at: str


class BuildAttempt(BaseModel):
    round: int
    attempt: int
    files_changed: list[str] = []
    test_output: str
    test_exit_code: int
    passed: bool
    timestamp: str


class ReviewerFinding(BaseModel):
    type: str
    ref_id: str
    verdict: str
    detail: str
    remediation: str = ""


class ReviewerVerdict(BaseModel):
    verdict: str
    findings: list[ReviewerFinding]
    summary: str
    round: int


class RalphRound(BaseModel):
    round: int
    build_attempts: list[BuildAttempt]
    reviewer_verdict: str
    reviewer_findings: list[ReviewerFinding]
    completed_at: str


class RunSummary(BaseModel):
    run_id: str
    spec_name: str
    spec_path: str
    branch: str
    ralph_rounds: int
    frs_addressed: list[str]
    reviewer_verdict: str
    reviewer_findings: list[ReviewerFinding]
    pr_url: str
    duration_seconds: float
    completed_at: str
