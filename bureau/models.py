from __future__ import annotations

from pydantic import BaseModel


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


class CriticFinding(BaseModel):
    type: str
    ref_id: str
    verdict: str
    detail: str
    remediation: str = ""


class CriticVerdict(BaseModel):
    verdict: str
    findings: list[CriticFinding]
    summary: str
    round: int


class RalphRound(BaseModel):
    round: int
    build_attempts: list[BuildAttempt]
    critic_verdict: str
    critic_findings: list[CriticFinding]
    completed_at: str


class RunSummary(BaseModel):
    run_id: str
    spec_name: str
    spec_path: str
    branch: str
    ralph_rounds: int
    frs_addressed: list[str]
    critic_verdict: str
    critic_findings: list[CriticFinding]
    pr_url: str
    duration_seconds: float
    completed_at: str
