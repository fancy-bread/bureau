# Feature Specification: Artifact Support for Bureau Runs

**Feature Branch**: `011-artifact-support`
**Created**: 2026-04-26
**Status**: Draft

## Overview

Bureau runs are ephemeral on CI runners and produce no persistent trace beyond the PR body summary. Operators and downstream tools currently have no way to inspect what happened inside a run after the fact. This spec adds two complementary artifacts:

1. **Run report** — a structured JSON summary written to the run directory at completion or escalation, capturing what bureau did and why.
2. **Build audit artifact** — the full bureau stdout log uploaded as a CI artifact after each e2e run, making runs inspectable post-hoc even when the runner is gone.

These artifacts are independent: the run report is written by the bureau process itself and is useful locally; the build audit artifact is a CI concern and uploads whatever stdout bureau produced.

---

## User Scenarios & Testing

### User Story 1 — Run Report at Completion or Escalation (Priority: P1)

After a bureau run completes or escalates, an operator or downstream tool can read a structured summary of what happened — how many review loops ran, what the reviewer found, which files changed, how long each attempt took, and the final verdict — without parsing raw log output.

**Why this priority**: The run report is pure bureau-internal work, has no external dependencies, and is the foundation the build audit artifact builds on. It also unlocks downstream agent consumption of run data.

**Independent Test**: Run bureau against a spec; confirm `run-summary.json` exists in the run directory with correct fields for both a passing and an escalating run.

**Acceptance Scenarios**:

1. **Given** a bureau run completes successfully, **When** the run finishes, **Then** `run-summary.json` is written to the run directory containing `run_id`, `status`, `spec_path`, `ralph_rounds`, `reviewer_findings`, `files_changed`, `attempt_durations`, and `final_verdict: pass`.
2. **Given** a bureau run escalates, **When** the escalation is emitted, **Then** `run-summary.json` is written with `final_verdict: escalated` and the escalation question included.
3. **Given** a bureau run fails with an unhandled error, **Then** `run-summary.json` is written with `status: failed` and `final_verdict: failed`.
4. **Given** `run-summary.json` already exists for a run (e.g., resumed run), **When** the run completes, **Then** the report is overwritten with the final state.

---

### User Story 2 — Build Audit Artifact on CI (Priority: P2)

After each e2e CI run, the full bureau stdout log is uploaded as a downloadable artifact named after the run, allowing any team member to inspect exactly what bureau produced — which events fired, in what order, with what data — without re-running.

**Why this priority**: Depends on the e2e workflow and external CI infrastructure; independent of US1. Useful for debugging CI failures and validating bureau behaviour, but the run report (US1) is the richer source of truth.

**Independent Test**: Trigger the e2e workflow; confirm a downloadable artifact appears in the GitHub Actions run with the correct name and contains the bureau event stream.

**Acceptance Scenarios**:

1. **Given** the e2e CI workflow runs and bureau completes, **When** the workflow finishes, **Then** a CI artifact named `bureau-run-<run-id>.ndjson` (CloudEvents mode) or `bureau-run-<run-id>.log` (text mode) is available for download.
2. **Given** the e2e tests fail after bureau ran, **When** the workflow finishes, **Then** the artifact is still uploaded (upload runs regardless of test outcome).
3. **Given** multiple bureau runs occur in one workflow execution, **Then** each produces a separately named artifact.
4. **Given** bureau stdout contains no `run.started` event (unusual error path), **Then** the artifact is still uploaded with a fallback name.

---

### Edge Cases

- What if bureau produces no stdout at all (crash before first event)? Upload an empty or minimal artifact with a fallback name; do not fail the upload step.
- What if the run directory already has a `run-summary.json` from a previous attempt? Overwrite it at the end of each run.
- What if `reviewer_findings` or `files_changed` are not available (e.g., run failed before reviewer ran)? Include empty lists; do not omit the fields.

---

## Requirements

### Functional Requirements

- **FR-001**: Bureau MUST write `run-summary.json` to the run directory at run completion (status: complete or failed) and at escalation (status: paused).
- **FR-002**: `run-summary.json` MUST contain: `run_id`, `status`, `spec_path`, `ralph_rounds` (integer count), `reviewer_findings` (list of finding objects), `files_changed` (list of file paths), `attempt_durations` (list of durations in seconds), `final_verdict` (one of: `pass`, `failed`, `escalated`).
- **FR-003**: `run-summary.json` MUST be written atomically — a partial write must not leave a corrupt file.
- **FR-004**: Writing `run-summary.json` MUST NOT crash a run; errors are logged to stderr and silently suppressed.
- **FR-005**: The e2e CI workflow MUST upload the bureau stdout log as a CI artifact after every run, including when tests fail.
- **FR-006**: The artifact MUST be named `bureau-run-<run-id>.ndjson` when bureau output is in CloudEvents format, or `bureau-run-<run-id>.log` otherwise.
- **FR-007**: The run-id used for artifact naming MUST be extracted from the bureau stdout event stream (from the `run.started` event); a static fallback name MUST be used if extraction fails.
- **FR-008**: CI artifacts MUST be retained for 7 days.

### Key Entities

- **Run Report** (`run-summary.json`): Structured summary of a single bureau run. Fields: `run_id` (string), `status` (string), `spec_path` (string), `ralph_rounds` (integer), `reviewer_findings` (list of finding objects with `severity`, `category`, `message`), `files_changed` (list of strings), `attempt_durations` (list of floats), `final_verdict` (string: pass/failed/escalated), `completed_at` (ISO timestamp).
- **Build Audit Artifact**: The raw bureau stdout captured during an e2e CI run, stored as a named CI artifact for post-hoc inspection.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: After every bureau run (complete, failed, or escalated), `run-summary.json` is present in the run directory within 1 second of the run ending.
- **SC-002**: `run-summary.json` is valid JSON and contains all required fields in 100% of runs.
- **SC-003**: After every e2e CI workflow execution, at least one downloadable artifact is available, regardless of whether the tests passed or failed.
- **SC-004**: A team member can identify the cause of a bureau run outcome by reading `run-summary.json` alone, without parsing raw log output.

---

## Assumptions

- The existing `RunRecord` and `ReviewerFinding` models in bureau state are stable and will not change structure during this spec's implementation.
- The e2e CI workflow captures bureau stdout to a file or variable that can be passed to the artifact upload step; if not, a capture step will be added.
- CI artifact storage is provided by GitHub Actions and requires no additional infrastructure.
- `ralph_rounds` is tracked in LangGraph state and accessible at run completion; if not currently exposed, it will be added as part of this spec.
- `files_changed` refers to files modified in the target repository during the build phase, as reported by the builder node.
- The run report is not intended to replace the PR body summary; it complements it with machine-readable detail.
