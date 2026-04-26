from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from bureau import events
from bureau.config import load_constitution
from bureau.memory import Memory
from bureau.models import BuildAttempt, PipelinePhase, RalphRound, ReviewerFinding, ReviewerVerdict
from bureau.personas.reviewer import run_reviewer
from bureau.state import Escalation, EscalationReason, Phase
from bureau.tools.pipeline import run_pipeline

_SKILLS_ROOT = Path(__file__).parent.parent / "skills" / "addyosmani"


def _load_review_skill(skills_root: Path) -> str:
    review_dir = skills_root / "review"
    md_files = sorted(review_dir.glob("*.md"))
    return "\n\n".join(f.read_text(encoding="utf-8") for f in md_files)


def reviewer_node(state: dict[str, Any]) -> dict[str, Any]:
    run_id = state["run_id"]
    spec_path = state["spec_path"]
    repo_path = state["repo_path"]
    repo_context = state.get("repo_context")
    ralph_round = state.get("ralph_round", 0)

    # Pre-flight: review skill must be present
    review_dir = _SKILLS_ROOT / "review"
    if not any(review_dir.glob("*.md")):
        return _escalate(
            state,
            "review skill missing from bureau/skills/addyosmani/review/",
            EscalationReason.BLOCKER,
        )

    review_skill = _load_review_skill(_SKILLS_ROOT)

    spec_text = state.get("spec_text") or Path(spec_path).read_text(encoding="utf-8")
    constitution = load_constitution(repo_path, repo_context)
    model = repo_context.reviewer_model if repo_context else "claude-opus-4-7"
    timeout = repo_context.command_timeout if repo_context else 300

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    mem = Memory(run_id)
    try:
        summary_dict = mem.read("builder_summary")
        builder_summary = _format_builder_summary(summary_dict)
    except KeyError:
        summary_dict = {}
        builder_summary = "No builder summary available."

    # Independent pipeline re-execution (FR-005, FR-009, FR-010)
    if repo_context:
        all_phases = [
            (PipelinePhase.INSTALL, repo_context.install_cmd),
            (PipelinePhase.LINT, repo_context.lint_cmd),
            (PipelinePhase.BUILD, repo_context.build_cmd),
            (PipelinePhase.TEST, repo_context.test_cmd),
        ]
        active_phases = [(p, cmd) for p, cmd in all_phases if cmd.strip()]
        if active_phases:
            pipeline_result = run_pipeline(repo_path, active_phases, timeout)
            if not pipeline_result.passed:
                phase_name = pipeline_result.failed_phase.value
                finding = ReviewerFinding(
                    type="requirement",
                    ref_id="FR-009",
                    verdict="unmet",
                    detail=(
                        f"Reviewer independent pipeline failed at {phase_name} phase: "
                        f"{pipeline_result.failed_output[:500]}"
                    ),
                    remediation=f"Fix the {phase_name} failure before resubmitting.",
                )
                revise_verdict = ReviewerVerdict(
                    verdict="revise",
                    findings=[finding],
                    summary=f"Reviewer independent pipeline failed at {phase_name}.",
                    round=ralph_round,
                )
                return _process_verdict(state, revise_verdict, ralph_round, repo_context)

    # Read changed files from memory scratchpad (FR-006)
    files_changed = summary_dict.get("files_changed", []) if isinstance(summary_dict, dict) else []
    file_contents: dict[str, str] = {}
    pre_findings: list[ReviewerFinding] = []

    if not files_changed:
        pre_findings.append(
            ReviewerFinding(
                type="requirement",
                ref_id="FR-006",
                verdict="unmet",
                detail="No files_changed in builder summary; implementation cannot be verified.",
                remediation="Builder must populate files_changed in memory scratchpad.",
            )
        )
    else:
        for rel_path in files_changed:
            abs_path = Path(repo_path) / rel_path
            if abs_path.exists():
                file_contents[rel_path] = abs_path.read_text(encoding="utf-8")
            else:
                pre_findings.append(
                    ReviewerFinding(
                        type="requirement",
                        ref_id="FR-006",
                        verdict="unmet",
                        detail=f"File {rel_path} listed in files_changed but not found on disk.",
                        remediation="Builder must write all files it lists in files_changed.",
                    )
                )

    if pre_findings and not file_contents:
        # No files available to review at all — revise immediately
        revise_verdict = ReviewerVerdict(
            verdict="revise",
            findings=pre_findings,
            summary="Reviewer could not read any changed files.",
            round=ralph_round,
        )
        return _process_verdict(state, revise_verdict, ralph_round, repo_context)

    try:
        verdict = run_reviewer(
            client=client,
            spec_text=spec_text,
            constitution=review_skill + "\n\n" + constitution if review_skill else constitution,
            builder_summary=builder_summary,
            ralph_round=ralph_round,
            model=model,
            file_contents=file_contents,
        )
    except Exception as exc:
        return _escalate(
            state,
            f"Reviewer failed to produce a verdict: {exc}",
            EscalationReason.BLOCKER,
        )

    # Merge any pre-findings (missing files) into the verdict
    if pre_findings:
        merged_findings = list(verdict.findings) + pre_findings
        if verdict.verdict == "pass":
            verdict = ReviewerVerdict(
                verdict="revise",
                findings=merged_findings,
                summary=verdict.summary + " (some files could not be read)",
                round=ralph_round,
            )
        else:
            verdict = ReviewerVerdict(
                verdict=verdict.verdict,
                findings=merged_findings,
                summary=verdict.summary,
                round=ralph_round,
            )

    return _process_verdict(state, verdict, ralph_round, repo_context)


def _process_verdict(
    state: dict[str, Any],
    verdict: ReviewerVerdict,
    ralph_round: int,
    repo_context: Any,
) -> dict[str, Any]:
    run_id = state["run_id"]
    all_attempts: list[dict] = state.get("build_attempts", [])
    round_attempts = [
        BuildAttempt.model_validate(a) for a in all_attempts if a.get("round") == ralph_round
    ]

    ralph_round_record = RalphRound(
        round=ralph_round,
        build_attempts=round_attempts,
        reviewer_verdict=verdict.verdict,
        reviewer_findings=verdict.findings,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )

    existing_ralph_rounds = list(state.get("ralph_rounds", []))
    existing_ralph_rounds.append(ralph_round_record.model_dump())

    mem = Memory(run_id)
    mem.write("reviewer_findings", [f.model_dump() for f in verdict.findings])

    updated_state = {
        **state,
        "ralph_rounds": existing_ralph_rounds,
        "reviewer_findings": [f.model_dump() for f in verdict.findings],
    }

    if verdict.verdict == "pass":
        events.emit(events.PHASE_COMPLETED, phase=Phase.REVIEWER, verdict="pass")
        events.emit(events.RALPH_COMPLETED, rounds=ralph_round + 1, verdict="pass")
        return {**updated_state, "phase": Phase.PR_CREATE, "_route": "pass"}

    if verdict.verdict == "escalate":
        violations = [f for f in verdict.findings if f.verdict == "violation"]
        detail = violations[0].detail if violations else verdict.summary
        return _escalate(
            updated_state,
            f"Reviewer detected a constitution violation: {detail}",
            EscalationReason.CONSTITUTION_VIOLATION,
        )

    # verdict == "revise"
    max_rounds = repo_context.max_ralph_rounds if repo_context else 3
    if ralph_round >= max_rounds - 1:
        unmet = [f.ref_id for f in verdict.findings if f.verdict == "unmet"]
        return _escalate(
            updated_state,
            f"Ralph Loop exceeded {max_rounds} round(s). Unresolved: {', '.join(unmet)}",
            EscalationReason.RALPH_ROUNDS_EXCEEDED,
        )

    events.emit(events.PHASE_COMPLETED, phase=Phase.REVIEWER, verdict="revise", round=ralph_round)

    return {
        **updated_state,
        "ralph_round": ralph_round + 1,
        "builder_attempts": 0,
        "phase": Phase.BUILDER,
        "_route": "revise",
    }


def _format_builder_summary(summary: dict) -> str:
    lines = [f"## Builder Summary (Round {summary.get('ralph_round', '?')})\n"]
    files = summary.get("files_changed", [])
    if files:
        lines.append("### Files Changed\n")
        lines.extend(f"- {f}" for f in files)
    lines.append("\n### Test Output\n")
    lines.append(summary.get("last_test_output", "(no output)"))
    return "\n".join(lines)


def _escalate(state: dict[str, Any], reason: str, escalation_reason: EscalationReason) -> dict[str, Any]:
    what_needed = (
        "Revise the spec to remove the violating requirement."
        if escalation_reason == EscalationReason.CONSTITUTION_VIOLATION
        else "Review unresolved findings and provide guidance."
    )
    escalation = Escalation(
        run_id=state["run_id"],
        phase=Phase.REVIEWER,
        reason=escalation_reason,
        what_happened=reason,
        what_is_needed=what_needed,
        options=[
            "Revise the spec and resume",
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
