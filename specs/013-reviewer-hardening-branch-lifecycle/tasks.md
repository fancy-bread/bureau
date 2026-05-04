---
description: "Task list for Reviewer Hardening and Branch Lifecycle"
---

# Tasks: Reviewer Hardening and Branch Lifecycle

**Input**: Design documents from `specs/013-reviewer-hardening-branch-lifecycle/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Note**: Retrospective tasks.md — all work is already implemented on `main`. Tasks are marked complete.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in all task descriptions

## Path Conventions

- Source: `bureau/` (Python package)
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Workflows: `.github/workflows/`

---

## Phase 1: Setup

**Purpose**: Add shared constants and Phase enum values that all user stories depend on.

- [x] T001 Add `REVIEWER_PIPELINE` and `REVIEWER_VERDICT` event constants to `bureau/events.py`
- [x] T002 Add `Phase.PREPARE_BRANCH = "prepare_branch"` and `Phase.COMPLETE_BRANCH = "complete_branch"` to `bureau/state.py`; remove `Phase.PLANNER`
- [x] T003 Builder verifies: run `make ci` to confirm existing 184 tests still pass before proceeding

---

## Phase 2: Foundational

**Purpose**: Fix hardcoded FR ref_ids in bureau's own code — prerequisite for the FR whitelist to work correctly (a sentinel that matches `FR-\d+` would itself be stripped by the whitelist).

**⚠️ CRITICAL**: Must complete before US1 (whitelist) is implemented.

- [x] T004 [P] Replace `ref_id="FR-009"`, `type="requirement"` with `ref_id="PIPELINE"`, `type="pipeline"` in `bureau/nodes/reviewer.py` (pipeline failure finding)
- [x] T005 [P] Replace `ref_id="FR-006"`, `type="requirement"` with `ref_id="FILES-MISSING"`, `type="pipeline"` in `bureau/nodes/reviewer.py` (missing files findings — both instances)
- [x] T006 [P] Replace `ref_id="FR-007"`, `type="requirement"` with `ref_id="TEST-QUALITY"`, `type="pipeline"` in `bureau/personas/reviewer.py` (test quality gate finding)
- [x] T007 Update `tests/integration/test_reviewer_node.py`: assertions on `FR-009` → `PIPELINE`, `FR-006` → `FILES-MISSING`
- [x] T008 Builder verifies: run `make ci` — 184 tests pass with updated ref_ids

---

## Phase 3: User Stories 1 & 2 — Reviewer Correctness (Priority: P1) 🎯 MVP

**Goal**: The Reviewer never routes on hallucinated FR IDs, and a builder escalation cannot be overwritten by the Reviewer.

**Independent Test**: Run bureau against a spec with FR-001–FR-008; inject a hallucinated FR-009 finding from the LLM; verify the run completes without escalating on FR-009. Separately, configure a failing `install_cmd`; verify `run.escalated` fires in round 0 without consuming any reviewer rounds.

### Implementation for US1 — FR Whitelist

- [x] T009 [US1] In `bureau/personas/reviewer.py`: after extracting `fr_lines`, build `_known_fr_ids` set using `re.search(r"FR-\d{3}", line)` for each line
- [x] T010 [US1] After `verdict = ReviewerVerdict.model_validate(...)` in `bureau/personas/reviewer.py`: filter findings where `_fr_ref.match(ref_id)` and `ref_id not in _known_fr_ids`; recalculate verdict from surviving findings
- [x] T011 [US1] Add `test_run_reviewer_strips_hallucinated_fr_ids` to `tests/unit/test_persona_reviewer.py`: LLM returns FR-001 (met) + FR-009 (unmet); assert FR-009 absent, verdict recalculates to `pass`

### Implementation for US2 — Builder Pass-Through Guard

- [x] T012 [US2] At entry of `reviewer_node` in `bureau/nodes/reviewer.py`: add guard `if state.get("_route") == "escalate" and state.get("escalations"): return state`
- [x] T013 [US2] Add `test_reviewer_node_passes_through_builder_escalation` to `tests/integration/test_reviewer_node.py`: state with `_route="escalate"` and a builder escalation; assert reviewer returns unchanged state

- [x] T014 Builder verifies: run `make ci` — tests pass with whitelist and pass-through in place

---

## Phase 4: User Story 3 — Branch Lifecycle (Priority: P2)

**Goal**: Feature branch is created before the Builder starts; `prepare_branch` and `complete_branch` express the branch lifecycle clearly.

**Independent Test**: After `tasks_loader` completes, the target repo is on a `feat/` branch. All builder commits appear on that branch, not on `main`.

- [x] T015 [US3] Create `bureau/nodes/prepare_branch.py`: extract `_derive_branch_name()` helper from `git_commit_node`; implement `prepare_branch_node` using `events.phase(Phase.PREPARE_BRANCH)`; store `branch_name` in state; handle collision retries (up to 3, `-2`/`-3` suffix); escalate `GIT_BRANCH_EXISTS` on exhaustion
- [x] T016 [US3] Update `bureau/nodes/git_commit.py` → rename to `bureau/nodes/complete_branch.py`: remove branch creation logic; read `branch_name` from `state["branch_name"]`; rename function to `complete_branch_node`; use `Phase.COMPLETE_BRANCH`
- [x] T017 [US3] Update `bureau/graph.py`: import `prepare_branch_node` from `bureau.nodes.prepare_branch`, `complete_branch_node` from `bureau.nodes.complete_branch`; add `"prepare_branch"` node between `tasks_loader` and `builder`; route `tasks_loader → prepare_branch → builder`; route `reviewer pass → complete_branch`; add `_route_prepare_branch` and `_route_complete_branch` routing functions
- [x] T018 [US3] Create `tests/unit/test_prepare_branch_node.py`: branch name derivation from spec path, truncation, kebab-case, state output (`branch_name`, `_route="ok"`), collision retry, 3-collision escalation
- [x] T019 [US3] Rename `tests/unit/test_git_commit_node.py` → `tests/unit/test_complete_branch_node.py`: remove branch creation tests (moved to T018); update to read `branch_name` from state; assert commit message and push use the state branch name
- [x] T020 [US3] Update e2e test `_assert_phase_order` lists in `tests/e2e/test_bureau_e2e_python.py`, `test_bureau_e2e_typescript.py`, `test_bureau_e2e_dotnet.py`: replace `"git_commit"` with `"complete_branch"`; add `"prepare_branch"` between `"tasks_loader"` and `"complete_branch"`
- [x] T021 Builder verifies: run `make ci` — 191 tests pass with new node structure

---

## Phase 5: User Story 4 — Reviewer Observability Events (Priority: P2)

**Goal**: Every run output includes `reviewer.pipeline` and `reviewer.verdict` events so the Reviewer is no longer a black box.

**Independent Test**: Run bureau against a passing spec; verify both events appear in stdout between `ralph.attempt result=pass` and `phase.completed phase=reviewer`.

- [x] T022 [US4] In `bureau/nodes/reviewer.py`, after `pipeline_result = run_pipeline(...)`: emit `events.REVIEWER_PIPELINE` with `passed`, `phases` (list of phase values), `failed_phase` (value or None); extract `failed` to a local variable to keep line length within lint limits
- [x] T023 [US4] In `bureau/nodes/reviewer.py` `_process_verdict()`, before routing: emit `events.REVIEWER_VERDICT` with `verdict`, `round`, `summary`, condensed `findings` list (`ref_id`, `verdict`, `type` per finding)
- [x] T024 Builder verifies: run `make ci` — 191 tests pass; no new test needed (event emission is integration-level, validated by e2e)

---

## Phase 6: User Story 5 — Dotnet E2E Infrastructure (Priority: P3)

**Goal**: Dotnet target repos can be tested end-to-end with the same structure as Python and TypeScript.

**Independent Test**: `BUREAU_TEST_REPO_DOTNET=../bureau-test-dotnet make test-kafka-smoke-dotnet` with Kafka running produces a PR in `bureau-test-dotnet`.

- [x] T025 [US5] Add `SKIP_NO_DOTNET_REPO` skip marker and `_bureau_test_dotnet_repo_path` / `bureau_test_dotnet_repo` fixtures to `tests/e2e/conftest.py` (same pattern as Python and TypeScript)
- [x] T026 [US5] Create `tests/e2e/test_bureau_e2e_dotnet.py`: `@pytest.mark.timeout(1800)` smoke test targeting `specs/001-kafka-observability-dashboard/spec.md`; assert `run.completed`, PR URL, phase order, at least one `ralph.attempt result=pass`, `pr.created`
- [x] T027 [US5] Add `test-kafka-smoke-dotnet` target to `Makefile`; add to `.PHONY`; uses `BUREAU_KAFKA_BOOTSTRAP_SERVERS=localhost:9092` and `../bureau-test-dotnet` repo path
- [x] T028 [US5] Create `.github/workflows/e2e-dotnet.yml`: `workflow_dispatch` trigger; `timeout-minutes: 60`; checkout `bureau-test-dotnet` with `BUREAU_TEST_PAT`; `actions/setup-dotnet@v4` with `dotnet-version: "10.x"`; run `tests/e2e/test_bureau_e2e_dotnet.py` exclusively; upload artifacts
- [x] T029 Builder verifies: run `make ci` — 191 tests pass; e2e test skips cleanly without `BUREAU_TEST_REPO_DOTNET` set

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T030 [P] Update Obsidian docs (`projects/software/bureau/TDD.md`, `HLA.md`): pipeline sequence, node names, reviewer guards, config examples, dotnet status
- [x] T031 [P] Update event schema in Obsidian (`projects/bureau/event-schema-v1.md`): phase names, new reviewer events, future events cleanup
- [x] T032 Run `make ci` — full suite passes at 191 tests, 1 warning

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS US1 (whitelist must not strip its own sentinels)
- **US1 & US2 (Phase 3)**: Depends on Phase 2 completion
- **US3 (Phase 4)**: Depends on Phase 1 (Phase enum); independent of US1/US2
- **US4 (Phase 5)**: Depends on Phase 1 (event constants); independent of US2/US3
- **US5 (Phase 6)**: Independent of all other user stories; depends only on Phase 1
- **Polish (Phase 7)**: Depends on all implementation phases

### Within Each Phase

- T004, T005, T006 (sentinel ref_id fixes) can run in parallel — different locations in the same file sections
- T009, T010 (whitelist filter) must be sequential — T010 uses `_known_fr_ids` built in T009
- T012 (pass-through guard) is independent of T009/T010
- T015, T016 can run in parallel — different files
- T017 depends on T015 and T016
- T022 and T023 are independent — different call sites

### Parallel Opportunities

- T004, T005, T006: All sentinel ref_id fixes
- T015, T016: `prepare_branch.py` and `complete_branch.py` in parallel
- T025, T026, T027, T028: All dotnet e2e artifacts in parallel
- T030, T031: Documentation updates in parallel

---

## Implementation Strategy

### MVP (US1 + US2 Only)

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Foundational sentinel fixes)
3. Complete Phase 3 (FR whitelist + builder pass-through)
4. **STOP and VALIDATE**: `make ci` passes; hallucination test added and passing

### Full Delivery

1. MVP above
2. Phase 4 (branch lifecycle)
3. Phase 5 (reviewer events)
4. Phase 6 (dotnet e2e)
5. Phase 7 (polish)
