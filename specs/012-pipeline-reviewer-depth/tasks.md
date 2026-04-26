# Tasks: Command Pipeline Formalization and Reviewer Depth

**Input**: Design documents from `/specs/012-pipeline-reviewer-depth/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story. US1 and US2 are P1; US3 is P2. All user stories share the foundational pipeline utility.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: This is an extension to an existing codebase — no project scaffold needed. The only setup is verifying the target module directories exist and reviewing the existing `execute_shell_tool` entrypoint before implementing `run_pipeline`.

- [X] T001 Review `bureau/tools/shell_tools.py` `execute_shell_tool` signature and confirm the call convention for `run_pipeline` wrapper (no file changes — reading only)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `PipelinePhase`, `PipelineResult`, and `run_pipeline()` are shared by US1 (builder) and US2 (reviewer). Both stories are blocked until this phase is complete.

**⚠️ CRITICAL**: US1 and US2 cannot be implemented until T002 and T003 are complete.

- [X] T002 [P] Add `PipelinePhase` StrEnum (INSTALL, LINT, BUILD, TEST) and `PipelineResult` Pydantic model (fields: `passed: bool`, `failed_phase: Optional[PipelinePhase]`, `failed_output: str`, `phases_run: list[PipelinePhase]`) to `bureau/models.py`
- [X] T003 [P] Create `bureau/tools/pipeline.py` with `run_pipeline(repo_path: str, phases: list[tuple[PipelinePhase, str]], timeout: int) -> PipelineResult` — iterates phases in order, calls `execute_shell_tool("run_command", {"command": cmd}, repo_path, timeout)`, stops on first non-zero exit, truncates `failed_output` to 2000 chars

**Checkpoint**: `PipelinePhase`, `PipelineResult`, and `run_pipeline` importable — US1 and US2 can now proceed in parallel.

---

## Phase 3: User Story 1 — Builder Runs Full Pipeline as Sequential Gates (Priority: P1) 🎯 MVP

**Goal**: Builder executes lint and build as sequential gates before the test phase within each attempt. A failing lint or build gate stops the attempt immediately and escalates with the failing phase identified.

**Independent Test**: Configure a repo with `lint_cmd = "exit 1"` in `.bureau/config.toml`. Run bureau. Verify the escalation contains "lint" as the failed phase and that `test_cmd` was never executed.

### Implementation for User Story 1

- [X] T004 [US1] Update `bureau/nodes/builder.py`: inside the attempt loop (before `run_builder_attempt`), build the active phase list from `repo_context.lint_cmd` and `repo_context.build_cmd` (skip empty), call `run_pipeline(repo_path, active_phases, timeout)`, and if `not result.passed` return `_escalate` with message identifying `result.failed_phase.value` and `result.failed_output` — covers FR-001, FR-002, FR-003, FR-004
- [X] T005 [P] [US1] Write integration tests for builder pipeline gates in `tests/integration/test_builder_node.py`: (a) lint failure stops builder and escalates with phase "lint", (b) build failure stops builder and escalates with phase "build", (c) empty `lint_cmd` and `build_cmd` are skipped and run proceeds to test normally — covers SC-001, SC-005

**Checkpoint**: US1 fully functional. A repo with a failing lint step now escalates with the lint phase named.

---

## Phase 4: User Story 2 — Reviewer Independently Re-Executes the Pipeline (Priority: P1)

**Goal**: Reviewer independently runs the full pipeline (all four phases in order, skipping empty commands) before its LLM review call. A non-zero exit on any phase results in a `revise` verdict with the failing phase identified.

**Independent Test**: Builder reports "tests passed" — reviewer re-runs the pipeline independently. If the test suite exits non-zero during the reviewer's run, the reviewer issues `revise` regardless of the builder's report.

### Implementation for User Story 2

- [X] T006 [US2] Update `bureau/nodes/reviewer.py`: after reading `builder_summary` from memory and before calling `run_reviewer`, build all four phases from `repo_context` (install, lint, build, test — skip empty), call `run_pipeline(repo_path, active_phases, timeout)`, and if `not result.passed` return an immediate `revise` verdict (bypass LLM) with a `ReviewerFinding` identifying `result.failed_phase.value` and `result.failed_output` — covers FR-005, FR-009, FR-010
- [X] T007 [P] [US2] Write integration tests for reviewer independent pipeline in `tests/integration/test_reviewer_node.py`: (a) reviewer runs pipeline independently and issues `revise` when test_cmd exits non-zero, (b) reviewer pipeline runs in order (lint before build before test), (c) empty lint/build phases are skipped — covers SC-002

**Checkpoint**: US2 fully functional. Reviewer now re-executes the pipeline independently regardless of builder's self-report.

---

## Phase 5: User Story 3 — Reviewer Reads Actual Files and Applies Test Quality Gate (Priority: P2)

**Goal**: Reviewer reads the contents of all files listed in `files_changed` from the memory scratchpad and performs LLM code review on actual file contents. Test files with no assertions trigger an automatic `revise` verdict.

**Independent Test**: Builder writes `tests/test_foo.py` containing only `def test_foo(): pass` and lists it in `files_changed`. Reviewer reads the file, detects zero assertions, and issues `revise` with a finding referencing FR-007.

### Implementation for User Story 3

- [X] T008 [US3] Update `bureau/nodes/reviewer.py`: after reading `builder_summary`, iterate `files_changed`, read each file from `repo_path / relative_path` (skip missing files with a note), collect `{path: content}` dict; if `files_changed` is empty or absent, build a finding that no files were changed and prepare to issue `revise` — covers FR-006 and the "no files_changed" edge case
- [X] T009 [US3] Update `bureau/personas/reviewer.py`: add `file_contents: dict[str, str]` parameter to `run_reviewer`; implement `has_assertions(content: str) -> bool` (detects `assert ` keyword, `self.assert` prefix, `pytest.raises`, `pytest.approx`); for each test file (path matches `test_*.py` or `*_test.py`) with `has_assertions() == False`, add a `TestQualityFinding` to the findings list and force `verdict = "revise"`; inject all file contents into the LLM system prompt for FR-008 code review against spec FRs — covers FR-007, FR-008
- [X] T010 [P] [US3] Write unit tests for `has_assertions()` in `tests/unit/test_pipeline.py`: (a) file with `assert` keyword returns True, (b) file with `self.assertEqual` returns True, (c) file with `pytest.raises` returns True, (d) file with only `pass` bodies returns False, (e) file with no test functions returns False — covers SC-002

**Checkpoint**: All three user stories complete. Reviewer reads actual files, catches trivially-passing tests, and evaluates FRs against real implementation.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify empty-command behaviour, run full CI, and confirm no regressions.

- [X] T011 Run `make ci` to execute the full lint + unit + integration test suite and confirm all tests pass — covers SC-005 (empty `lint_cmd`/`build_cmd` unaffected) and SC-003 (no excessive overhead)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — read-only review, start immediately
- **Foundational (Phase 2)**: Depends on Setup — T002 and T003 BLOCK all user stories
- **US1 (Phase 3)**: Depends on Foundational (T002, T003)
- **US2 (Phase 4)**: Depends on Foundational (T002, T003); can run in parallel with US1
- **US3 (Phase 5)**: Depends on US2 (T006 modifies `reviewer_node`; T008 extends that same function)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Foundational complete → independent
- **US2 (P1)**: Foundational complete → independent of US1 (different nodes)
- **US3 (P2)**: US2 complete → extends reviewer_node built in US2

### Within Each User Story

- Implementation task before its test task (tests verify implemented behaviour)
- T004 before T005; T006 before T007; T008 before T009 (same pattern)

### Parallel Opportunities

- T002 and T003 (foundational models and utility): different files, fully parallel
- T004 (builder node) and T006 (reviewer node): different files, can proceed in parallel once T002/T003 complete
- T005 and T007 (integration tests): different test files, parallel
- T010 (unit tests): separate file, parallel with T008/T009

---

## Parallel Example: Foundational Phase

```
# Run in parallel (different files, no dependencies):
T002: Add PipelinePhase + PipelineResult to bureau/models.py
T003: Create bureau/tools/pipeline.py with run_pipeline()
```

## Parallel Example: US1 + US2 (after Foundational)

```
# Run in parallel (different nodes):
T004: Update bureau/nodes/builder.py  →  T005: tests/integration/test_builder_node.py
T006: Update bureau/nodes/reviewer.py →  T007: tests/integration/test_reviewer_node.py
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: US1 (T004, T005)
4. **STOP and VALIDATE**: Builder now enforces lint + build gates — SC-001 satisfied
5. Proceed to US2 for false-positive prevention

### Incremental Delivery

1. T001 → T002+T003 → Foundation ready
2. T004+T005 → Builder gates enforced → SC-001 ✅
3. T006+T007 → Reviewer independent pipeline → SC-002 (partial) ✅
4. T008+T009+T010 → Reviewer file reading + test quality gate → SC-002 (full) ✅
5. T011 → Full CI green ✅

---

## Notes

- `run_pipeline` must NOT call `install_cmd` — the caller (builder node, reviewer node) passes whichever phases apply
- The builder node already calls `install_cmd` once per round before the attempt loop; the reviewer node calls it as phase 1 of its independent pipeline run
- `files_changed` paths in memory are relative to `repo_path`; use `Path(repo_path) / relative_path` to read them
- Empty or whitespace-only command strings MUST be excluded before calling `run_pipeline`; the function trusts its input list
- `has_assertions` must only be applied to files whose names match `test_*.py` or `*_test.py`; implementation files should not be checked for assertions
