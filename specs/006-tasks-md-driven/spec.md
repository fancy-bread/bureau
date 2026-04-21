# Feature Specification: Tasks.md-Driven Execution

**Feature Branch**: `006-tasks-md-driven`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "Replace bureau's internal Planner persona with direct consumption of the speckit tasks.md."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bureau executes a developer-authored task plan (Priority: P1)

A developer has run the full speckit pipeline and has an approved spec folder containing `tasks.md`. They invoke bureau pointing at the spec folder. Bureau reads `tasks.md` directly, hands the ordered task list to the Builder, and proceeds to build, review, commit, and open a PR — without re-deriving any tasks at runtime.

**Why this priority**: The Planner persona duplicates work the developer has already done with higher context. Removing it shortens the run, reduces cost, and produces better-aligned output because the Builder works from the developer's intent rather than an LLM re-interpretation.

**Independent Test**: Run `bureau run specs/001-smoke-hello-world/` (folder, not file) against bureau-test-python. Assert `phase.started phase=planner` does NOT appear in stdout. Assert `ralph.started phase=builder round=0` DOES appear in stdout. Assert a PR URL is in stdout.

**Acceptance Scenarios**:

1. **Given** a spec folder with a valid `tasks.md`, **When** bureau is invoked with the folder path, **Then** bureau reads tasks from `tasks.md` and passes them to the Builder without invoking any LLM planner
2. **Given** a spec folder with a valid `tasks.md`, **When** the run completes successfully, **Then** the Builder receives a `task_plan` containing all incomplete tasks from `tasks.md` in line order, and the PR body references each task ID
3. **Given** bureau is invoked with a spec folder, **When** the run starts, **Then** `spec.md`, `tasks.md`, and `plan.md` (if present) are all loaded and available to downstream nodes

---

### User Story 2 - Bureau escalates when tasks.md is missing (Priority: P2)

A developer invokes bureau against a spec folder that has `spec.md` but no `tasks.md`. Bureau escalates immediately with a clear message explaining that tasks must be generated first, rather than silently falling back to re-deriving them.

**Why this priority**: Fail-fast with a clear error is better than silent degradation. The developer needs to know to run `/speckit-tasks` before invoking bureau.

**Independent Test**: Run `bureau run` against a spec folder containing only `spec.md`. Assert `run.escalated` in stdout with `TASKS_MISSING` in the reason.

**Acceptance Scenarios**:

1. **Given** a spec folder with `spec.md` but no `tasks.md`, **When** bureau is invoked, **Then** bureau escalates with reason `TASKS_MISSING` and instructs the developer to run `/speckit-tasks`
2. **Given** a `tasks.md` where all tasks are already checked off, **When** bureau is invoked, **Then** bureau escalates with `TASKS_COMPLETE` indicating there is nothing left to build

---

### Edge Cases

- What if bureau is invoked with a file path instead of a folder? If the argument is a file, look for `tasks.md` in the same directory — backwards compatible with current CLI usage.
- What if `tasks.md` has no unchecked tasks (all `[x]`)? Escalate with `TASKS_COMPLETE`.
- What if `plan.md` exists alongside `tasks.md`? Load it as additional context for the Builder but do not require it.
- What if `tasks.md` is malformed (no checklist items parseable)? Escalate with `TASKS_MISSING`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bureau MUST accept a spec folder path as its primary input and locate `spec.md` and `tasks.md` within it
- **FR-002**: Bureau MUST parse `tasks.md` and extract all incomplete tasks (lines matching `- [ ]`) as the ordered task list for the Builder
- **FR-003**: Bureau MUST remove the Planner LLM persona and its associated graph node — no LLM call may be made to re-derive tasks at runtime
- **FR-004**: Bureau MUST escalate with reason `TASKS_MISSING` if `tasks.md` does not exist or contains no parseable task items
- **FR-005**: Bureau MUST escalate with reason `TASKS_COMPLETE` if `tasks.md` exists but all tasks are already checked off
- **FR-006**: Bureau MUST remain backwards-compatible with a spec file path argument by searching for `tasks.md` in the parent directory of the given file
- **FR-007**: Bureau MUST make `plan.md` content available to the Builder as additional context when it exists in the spec folder

### Key Entities

- **Spec Folder**: The directory produced by the speckit pipeline containing `spec.md`, `tasks.md`, and optionally `plan.md`, `contracts/`, `research.md`
- **Task Item**: A single incomplete checklist line from `tasks.md` (`- [ ] TXXX ...`); the atomic unit of work passed to the Builder
- **Task List**: The ordered sequence of incomplete Task Items extracted from `tasks.md` at run start

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bureau run against a spec folder with `tasks.md` produces no `phase.started phase=planner` event — 100% of runs skip the Planner persona
- **SC-002**: The Builder receives tasks in the same order they appear in `tasks.md` — order fidelity is 100%
- **SC-003**: A missing or empty `tasks.md` always produces a structured escalation within the first 3 seconds of a run — zero silent failures
- **SC-004**: Existing runs that pass a spec file path continue to work without modification — zero breaking changes to current CLI usage

## Assumptions

- The developer always runs the full speckit pipeline (specify → plan → tasks) before invoking bureau; bureau does not scaffold missing artifacts
- `tasks.md` uses the standard speckit checklist format (`- [ ]` for incomplete, `- [x]` for complete)
- The Builder can accept a flat ordered list of task descriptions and work through them sequentially
- `plan.md` is optional context; its absence does not block a run
- bureau-test-python already has a `tasks.md` in its spec folder for E2E testing, or one will be added as part of this feature
