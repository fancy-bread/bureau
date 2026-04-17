---
description: "Task list for Bureau CLI Foundation"
---

# Tasks: Bureau CLI Foundation

**Input**: Design documents from `specs/001-autonomous-runtime-core/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Parallelizable (different files, no incomplete dependencies)
- **[Story]**: Maps to user story (US1, US2, US3)
- File paths are relative to repo root (`bureau/`)

---

## Phase 1: Setup

**Purpose**: Project scaffold — pyproject.toml, package structure, Docker stub

- [ ] T001 Create `bureau/pyproject.toml` with dependencies: `langgraph>=0.2`, `langgraph-checkpoint-sqlite`, `typer`, `pydantic>=2`, `pytest`, `pytest-cov`; define `[project.scripts] bureau = "bureau.cli:app"`
- [ ] T002 Create `bureau/bureau/__init__.py`, `bureau/bureau/nodes/__init__.py`, `bureau/tests/__init__.py`, `bureau/tests/integration/__init__.py`, `bureau/tests/unit/__init__.py`
- [ ] T003 [P] Create `bureau/Dockerfile` scaffold: `FROM python:3.12-slim`; `WORKDIR /workspace`; no further implementation (not used in this feature)
- [ ] T004 [P] Create `bureau/bureau.toml.example` with all fields from `contracts/bureau-toml.md`, fully commented

**Checkpoint**: Package installable with `pip install -e .`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types, config loading, event emission, and run lifecycle — required by all user story phases

⚠️ **CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Create `bureau/bureau/state.py`: `Phase` (StrEnum), `RunStatus` (StrEnum), `RunState` (TypedDict with `run_id`, `spec_path`, `repo_path`, `phase`, `spec`, `repo_context`, `escalations`, `decisions`, `messages`), `RunRecord` dataclass — per `data-model.md`
- [ ] T006 [P] Create `bureau/bureau/config.py`: `BureauConfig` dataclass; `load_bureau_config(path: str | None) -> BureauConfig` reads `bureau.toml` via `tomllib`; returns defaults when file absent — per `contracts/bureau-toml.md`
- [ ] T007 [P] Create `bureau/bureau/events.py`: `emit(event: str, **kwargs)` prints `[bureau] <event>  <k>=<v> ...` to stdout; define constants for all event names from `contracts/terminal-events.md`
- [ ] T008 Create `bureau/bureau/memory.py`: `Memory` class with `write(key, value)`, `read(key)`, `summary() -> str` (returns `""`); backed by JSON file at `~/.bureau/runs/<run-id>/memory.json` — per `data-model.md`
- [ ] T009 [P] Create `bureau/bureau/run_manager.py` with `create_run(spec_path, repo_path, config) -> RunRecord`; `write_run_record(record: RunRecord)`; `get_run(run_id) -> RunRecord`; `list_runs(status_filter) -> list[RunRecord]`; `abort_run(run_id)` — stores records at `~/.bureau/runs/<run-id>/run.json`

**Checkpoint**: Foundation types importable; `BureauConfig` loads correctly with and without `bureau.toml`

---

## Phase 3: User Story 1 — Run Foundation End-to-End (Priority: P1) 🎯 MVP

**Goal**: `bureau run <spec> --repo <path>` executes the full stub graph and emits structured events for every phase

**Independent Test**: `bureau run specs/001-autonomous-runtime-core/spec.md --repo .` completes without error and emits `run.started`, one `phase.started`/`phase.completed` pair per node, and `run.completed`

### Implementation for User Story 1

- [ ] T010 [P] [US1] Create `bureau/bureau/spec_parser.py`: `parse_spec(path: str) -> Spec`; extracts `Spec`, `UserStory`, `FunctionalRequirement` dataclasses by scanning `## ` and `### ` headings and `FR-\d{3}` patterns; raises `SpecParseError` on missing required sections — per `data-model.md`
- [ ] T011 [P] [US1] Create `bureau/bureau/repo_analyser.py`: `parse_repo_config(repo_path: str) -> RepoContext`; reads `<repo_path>/.bureau/config.toml` via `tomllib`; raises `ConfigMissingError` if absent; raises `ConfigInvalidError` if required fields missing — per `data-model.md` and `contracts/bureau-config-toml.md`
- [ ] T012 [P] [US1] Create `bureau/bureau/nodes/validate_spec.py`: real node; calls `parse_spec(state["spec_path"])`; checks ≥1 P1 story, all FRs numbered, no `[NEEDS CLARIFICATION]` in FR text; on failure emits `run.escalated` and returns routing key `"escalate"`; on success writes `spec_summary` to memory, emits `phase.started`/`phase.completed` — per `contracts/terminal-events.md`
- [ ] T013 [P] [US1] Create `bureau/bureau/nodes/repo_analysis.py`: real node; calls `parse_repo_config(state["repo_path"])`; on `ConfigMissingError` emits `run.escalated` and returns `"escalate"`; on success writes `repo_context` to memory, emits `phase.started`/`phase.completed`
- [ ] T014 [P] [US1] Create `bureau/bureau/nodes/memory_node.py`: scaffold node; initialises `Memory(run_id)` and attaches to state; emits `phase.started`/`phase.completed`
- [ ] T015 [P] [US1] Create `bureau/bureau/nodes/planner.py`: stub node; emits `phase.started phase=planner stub=true`; writes `"[STUB] planner output — real implementation pending"` to memory keys `plan`, `task_list`, `constitution_self_check`; emits `phase.completed stub=true`
- [ ] T016 [P] [US1] Create `bureau/bureau/nodes/builder.py`: stub node; emits `phase.started phase=builder stub=true`; writes `"[STUB] builder output — real implementation pending"` to memory key `implementation_notes`; emits `phase.completed stub=true`
- [ ] T017 [P] [US1] Create `bureau/bureau/nodes/critic.py`: stub node; emits `phase.started phase=critic stub=true`; writes `"[STUB] critic findings — real implementation pending"` to memory key `critic_findings`; returns routing key `"pass"`; emits `phase.completed stub=true`
- [ ] T018 [P] [US1] Create `bureau/bureau/nodes/pr_create.py`: stub node; emits `phase.started phase=pr_create stub=true`; logs `"[STUB] PR URL — real implementation pending"`; emits `phase.completed stub=true`
- [ ] T019 [P] [US1] Create `bureau/bureau/nodes/escalate.py`: real node; prints structured escalation block to stdout per `contracts/terminal-events.md`; updates `run.json` status to `paused`; graph exits via `interrupt_before`
- [ ] T020 [US1] Create `bureau/bureau/graph.py`: `build_graph(run_id, config) -> CompiledGraph`; registers all 8 nodes; wires conditional edges (`validate_spec` → `ok`/`escalate`, `critic` → `pass`/`escalate`); compiles with `SqliteSaver.from_conn_string("~/.bureau/runs/<run-id>/checkpoint.db")` and `interrupt_before=["escalate"]` — per `data-model.md` LangGraph design (depends on T010–T019)
- [ ] T021 [US1] Create `bureau/bureau/cli.py`: Typer `app`; implement `bureau run <spec_file> [--repo] [--config]`; calls `create_run`, `build_graph`, invokes graph; emits `run.started` and `run.completed`/`run.failed` — depends on T009, T020
- [ ] T022 [US1] Add integration test `tests/integration/test_graph_run.py`: assert `bureau run` on `specs/001-autonomous-runtime-core/spec.md` completes with exit code 0; assert all 8 `phase.started`/`phase.completed` event pairs appear in stdout; assert `run.json` status is `complete` — depends on T021

**Checkpoint**: `bureau run specs/001-autonomous-runtime-core/spec.md --repo .` completes and emits all phase events; US1 independently testable

---

## Phase 4: User Story 2 — Resume an Interrupted Run (Priority: P2)

**Goal**: `bureau resume <run-id>` continues from the last completed checkpoint node without replaying earlier nodes

**Independent Test**: Interrupt a run after `validate_spec` completes; run `bureau resume <run-id>`; confirm `validate_spec` does not re-execute and run completes from `repo_analysis` forward

### Implementation for User Story 2

- [ ] T023 [P] [US2] Add `resume_run(run_id: str, response: str) -> None` to `bureau/bureau/run_manager.py`: loads `RunRecord`; raises `RunNotFoundError` if absent; raises `RunNotPausedError` if status is not `paused`; reinitialises graph with same `thread_id` so `SqliteSaver` continues from last checkpoint
- [ ] T024 [US2] Add `bureau resume <run_id> [--response]` command to `bureau/bureau/cli.py`; calls `resume_run`; emits `run.started` (resume); handles `RunNotFoundError` and `RunNotPausedError` with clear user-facing errors — depends on T023
- [ ] T025 [US2] Add resume tests to `bureau/tests/integration/test_graph_run.py`: assert resume continues from checkpoint (node execution count); assert `bureau resume unknown-id` exits with code 1 and clear error — depends on T024

**Checkpoint**: Interrupted run resumes from last checkpoint; US2 independently testable alongside US1

---

## Phase 5: User Story 3 — Scaffold a Target Repo (Priority: P2)

**Goal**: `bureau init --repo <path>` creates `.bureau/config.toml` with scaffold defaults; does not overwrite existing file

**Independent Test**: Run `bureau init --repo /tmp/test-repo`; assert `.bureau/config.toml` created with `[runtime]` and `[bureau]` sections; run again and assert file not overwritten

### Implementation for User Story 3

- [ ] T026 [P] [US3] Add `init_repo(repo_path: str) -> str` to `bureau/bureau/run_manager.py`: creates `<repo_path>/.bureau/` directory; writes `.bureau/config.toml` with scaffold defaults from `contracts/bureau-config-toml.md`; returns `"exists"` without writing if file already present
- [ ] T027 [US3] Add `bureau init [--repo]` command to `bureau/bureau/cli.py`; calls `init_repo`; prints created file path on success; prints warning and exits 0 if file exists — depends on T026
- [ ] T028 [US3] Add integration test `bureau/tests/integration/test_init_cmd.py`: assert `bureau init --repo <tmpdir>` creates `.bureau/config.toml` with all required fields; assert running again prints warning and does not overwrite — depends on T027

**Checkpoint**: All three user stories independently testable; `bureau run`, `bureau resume`, and `bureau init` all work

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Remaining CLI commands and unit test coverage

- [ ] T029 [P] Add `bureau list [--status]` command to `bureau/bureau/cli.py`; calls `list_runs`; prints one run per line: `<run-id>  <status>  <started-at>  <spec-path>`
- [ ] T030 [P] Add `bureau show <run_id>` command to `bureau/bureau/cli.py`; calls `get_run`; prints all `RunRecord` fields as `key: value`
- [ ] T031 [P] Add `bureau abort <run_id>` command to `bureau/bureau/cli.py`; calls `abort_run`; prints confirmation; exits 1 with error if run not found
- [ ] T032 [P] Add unit tests `bureau/tests/unit/test_spec_parser.py`: test valid spec parses correctly; test spec with `[NEEDS CLARIFICATION]` sets `needs_clarification=True`; test missing required section raises `SpecParseError`
- [ ] T033 [P] Add unit tests `bureau/tests/unit/test_repo_analyser.py`: test valid `.bureau/config.toml` parses to `RepoContext`; test missing file raises `ConfigMissingError`; test missing required field raises `ConfigInvalidError`
- [ ] T034 Run quickstart.md validation end-to-end: install bureau, run `bureau init`, run `bureau run`, verify all events emitted, verify resume works from checkpoint

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational completion; T020 (graph.py) depends on T010–T019 all complete
- **US2 (Phase 4)**: Depends on US1 completion (graph.py and cli.py must exist)
- **US3 (Phase 5)**: Depends on Foundational completion only — independent of US1/US2
- **Polish (Phase 6)**: Depends on US1, US2, US3 completion

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies
- **US2 (P2)**: After US1 — requires `graph.py` and `cli.py` to exist
- **US3 (P2)**: After Foundational — independent of US1 and US2

### Critical Path Within US1

T010, T011 (parsers) → T012, T013 (nodes that use them) → T014–T019 (remaining nodes, parallel) → T020 (graph.py, depends on all nodes) → T021 (cli.py) → T022 (integration test)

### Parallel Opportunities

All `[P]` tasks within a phase can run concurrently. Key parallel sets:

```
Phase 2 parallel:  T005, T006, T007, T008, T009
US1 parallel:      T010, T011 (then unblocks T012–T019 which are also parallel)
                   T012, T013, T014, T015, T016, T017, T018, T019
Phase 6 parallel:  T029, T030, T031, T032, T033
```

---

## Implementation Strategy

### MVP: User Story 1 Only

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (T010–T022)
4. **VALIDATE**: Run `bureau run specs/001-autonomous-runtime-core/spec.md --repo .` end-to-end
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + Phase 2 → foundation types and lifecycle
2. US1 (Phase 3) → runnable graph, all phase events ✅
3. US2 (Phase 4) → resumability verified ✅
4. US3 (Phase 5) → `bureau init` working ✅
5. Phase 6 → full CLI surface + unit tests ✅

---

## Notes

- `[P]` tasks = different files, no incomplete dependencies — safe to run in parallel
- `[Story]` label maps each task to its user story for traceability
- Tests are included per plan.md (tests/ directory specified)
- Stub nodes (T015–T019) are intentionally minimal — no LLM calls, no external dependencies
- All paths relative to `bureau/` repo root; absolute paths used in `~/.bureau/` references
