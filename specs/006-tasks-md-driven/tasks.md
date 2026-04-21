# Tasks: Tasks.md-Driven Execution

**Input**: Design documents from `specs/006-tasks-md-driven/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story. US1 (folder invocation + tasks_loader) is foundational and must complete before US2 (missing/complete escalation) can be tested.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label [US1]–[US2]

---

## Phase 1: Setup

**Purpose**: Extend state and add new escalation reasons before any node implementation begins.

- [x] T001 Add `TASKS_MISSING = "TASKS_MISSING"` and `TASKS_COMPLETE = "TASKS_COMPLETE"` to `EscalationReason` in `bureau/state.py`
- [x] T002 Add `"spec_folder": ""`, `"tasks_path": ""`, and `"plan_text": ""` to the dict returned by `make_initial_state()` in `bureau/state.py`

---

## Phase 2: Foundational — CLI Folder/File Detection (blocks US1 and US2)

**Goal**: `bureau run` accepts either a spec folder path or a spec file path and resolves `spec_folder`, `spec_path`, and `tasks_path` before building the graph state.

**Independent Test**: Run `bureau run specs/006-tasks-md-driven/ --repo <repo>` and assert the run starts (validate_spec fires). Run `bureau run specs/006-tasks-md-driven/spec.md --repo <repo>` and assert same. Both must resolve correctly without error.

- [x] T003 Update `bureau/cli.py` `run` command: change `spec_file: str` argument to `spec: str`; detect `Path(spec).is_dir()`: if dir, set `spec_folder = Path(spec).resolve()`, `spec_path = spec_folder / "spec.md"`, `tasks_path = spec_folder / "tasks.md"`; if file, set `spec_path = Path(spec).resolve()`, `spec_folder = spec_path.parent`, `tasks_path = spec_folder / "tasks.md"`; pass `spec_folder` and `tasks_path` as strings into `make_initial_state()`
- [x] T004 Update `make_initial_state()` signature in `bureau/state.py` to accept `spec_folder: str = ""` and `tasks_path: str = ""` parameters and include them in the returned dict (extends T002's additions to the same function)

---

## Phase 3: User Story 1 — tasks_loader_node (Priority: P1)

**Goal**: After memory node, bureau reads `tasks.md` from the spec folder, parses incomplete tasks into a `TaskPlan`, and passes it to the builder — no LLM planner call.

**Independent Test**: Run `bureau run specs/001-smoke-hello-world/ --repo <bureau-test-python>`. Assert `phase.started phase=planner` does NOT appear in stdout. Assert `phase.started phase=tasks_loader` DOES appear. Assert PR URL in stdout.

- [x] T005 [US1] Create `bureau/nodes/tasks_loader.py` with `tasks_loader_node(state)`: (a) read `tasks_path = state["tasks_path"]`; (b) if file missing → escalate `TASKS_MISSING`; (c) read file, collect lines matching `^- \[ \] `; (d) if no incomplete lines: check for `- [x]` lines → escalate `TASKS_COMPLETE`, else → escalate `TASKS_MISSING`; (e) for each incomplete line strip `- [ ] ` prefix, extract task id via `re.search(r"T\d+", line)` defaulting to `f"T{i+1:03d}"`, build `Task(id=..., description=..., fr_ids=[], done=False)`; (f) read `plan.md` from `state["spec_folder"]` if it exists, store as `plan_text`; (g) build `TaskPlan(tasks=tasks, spec_name=..., fr_coverage=[], created_at=now)`; (h) return `{**state, "task_plan": task_plan.model_dump(), "plan_text": plan_text, "phase": Phase.BUILDER, "_route": "ok"}`; wrap body in `with events.phase(Phase.TASKS_LOADER):`; imports: `re`, `subprocess`, `Path`, `datetime`, `events`, `Phase`, `Escalation`, `EscalationReason`, `Task`, `TaskPlan`
- [x] T006 [US1] Add `Phase.TASKS_LOADER = "tasks_loader"` to the `Phase` StrEnum in `bureau/state.py`
- [x] T007 [US1] **Requires T013 complete first** — Update `bureau/graph.py`: import `tasks_loader_node` from `bureau.nodes.tasks_loader`; add `graph.add_node("tasks_loader", tasks_loader_node)`; add `_route_tasks_loader` router returning `state.get("_route", "ok")`; replace `graph.add_edge("memory", "planner")` with `graph.add_edge("memory", "tasks_loader")`; replace `graph.add_conditional_edges("planner", ...)` with `graph.add_conditional_edges("tasks_loader", _route_tasks_loader, {"ok": "builder", "escalate": "escalate"})`; remove `planner_node` import and `graph.add_node("planner", planner_node)`
- [x] T008 [US1] Update `bureau/nodes/builder.py`: read `plan_text = state.get("plan_text", "")`; pass it to `run_builder_attempt` as an additional `plan_text` parameter so the builder prompt can include it as extra context

---

## Phase 4: User Story 2 — Escalation Paths (Priority: P2)

**Goal**: Missing or fully-complete `tasks.md` produces a structured escalation with `TASKS_MISSING` or `TASKS_COMPLETE` within the first node after memory.

**Independent Test**: Run `bureau run` against a spec folder with no `tasks.md`. Assert `TASKS_MISSING` in stdout. Run against a spec folder where all tasks are `[x]`. Assert `TASKS_COMPLETE` in stdout.

- [x] T009 [US2] Add unit tests in `tests/unit/test_tasks_loader.py`: (a) `test_tasks_missing_no_file` — call `tasks_loader_node` with a `tasks_path` pointing to a non-existent file; assert `_route == "escalate"` and `reason == TASKS_MISSING`; (b) `test_tasks_complete_all_checked` — write a `tasks.md` with only `- [x]` lines to tmp_path; assert `_route == "escalate"` and `reason == TASKS_COMPLETE`; (c) `test_tasks_parsed_correctly` — write a `tasks.md` with 3 `- [ ]` lines containing IDs T001, T002, T003; assert `task_plan["tasks"]` has 3 items and `[t["id"] for t in task_plan["tasks"]] == ["T001", "T002", "T003"]`; (d) `test_plan_text_loaded` — write `tasks.md` and `plan.md` to tmp_path; assert `state["plan_text"]` contains plan.md content; (e) `test_file_with_no_checkboxes` — write `tasks.md` with prose but no checkbox lines; assert `TASKS_MISSING`
- [x] T010 [US2] Add integration tests in `tests/integration/test_graph_run.py`: (a) `test_tasks_missing_escalates` — create target repo with `.bureau/config.toml` and a spec folder containing only `spec.md` (no `tasks.md`); run bureau; assert `TASKS_MISSING` in stdout; (b) `test_tasks_complete_escalates` — create spec folder with `tasks.md` containing only `- [x]` lines; run bureau; assert `TASKS_COMPLETE` in stdout; (c) `test_file_path_invocation_resolves_tasks` — create spec folder with valid `tasks.md`; invoke bureau with `spec_folder/spec.md` (file path not folder); assert run starts and `TASKS_MISSING` does NOT appear (tasks resolved from parent dir); (d) `test_malformed_tasks_escalates` — create spec folder with `tasks.md` containing prose but no `- [ ]` lines; run bureau; assert `TASKS_MISSING` in stdout

---

## Phase 3b: Constitution Update (prerequisite for T007)

**Must complete before T007.** Removing the Planner from the graph while the constitution mandates it would create a CRITICAL constitution violation.

- [x] T013 Update `.specify/memory/constitution.md`: in the Development Workflow section, replace "Planner → Builder → Critic → PR Creation" with "Tasks Loader → Builder → Critic → PR Creation" and update the Agent Personas table to remove Planner row and add "Tasks Loader | Reads tasks.md from spec folder; builds task list | Task list for Builder"; bump version to 1.1.0 with PATCH bump comment

---

## Phase 5: Polish & Cleanup

- [x] T011 [P] Delete `bureau/nodes/planner.py` and `bureau/personas/planner.py`
- [x] T012 [P] Update `bureau/nodes/builder.py` `_format_task_plan` to include `plan_text` in the prompt context if non-empty: prepend `## Implementation Plan\n{plan_text}\n\n` before the task list

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (uses new state keys)
- **US1 (Phase 3)**: Depends on Phase 1+2; T005→T006→T007→T008 sequential
- **US2 (Phase 4)**: Depends on T005 (tasks_loader_node must exist to test escalation)
- **Polish (Phase 5)**: Depends on all phases

### Within Each Phase

- T001 → T002 (both state.py, sequential)
- T003 → T004 (cli.py then state.py signature, sequential)
- T005 → T006 → **T013** → T007 → T008 (sequential: node, enum, constitution update, graph, builder)
- T009 and T010 parallel (different test files, both depend on T005)
- T011, T012 parallel (different files); T013 promoted to Phase 3 prerequisite for T007

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: state.py additions (T001–T002)
2. Complete Phase 2: CLI folder detection (T003–T004)
3. Complete Phase 3: tasks_loader_node + constitution update + graph wiring (T005, T006, T013, T007, T008)
4. **STOP and VALIDATE**: Run E2E smoke test — assert no `phase=planner`, PR URL present
5. E2E smoke test should show `phase.started phase=tasks_loader`

### Incremental Delivery

1. Phase 1+2 → CLI and state ready
2. Phase 3 → Happy-path E2E works without planner
3. Phase 4 → Escalation paths verified
4. Phase 5 → Dead code removed, constitution updated

---

## Notes

- `Phase.PLANNER` stays in the enum — removing it could break stored checkpoint state
- `bureau/personas/planner.py` and `bureau/nodes/planner.py` are safe to delete: no other callers
- T013 (constitution update) is promoted to Phase 3b — it MUST precede T007 to avoid a mid-implementation constitution violation (the Critic would flag removing the Planner without the constitution amendment)
- The builder's `_format_task_plan` already handles the `task_plan` dict — no schema change needed
- bureau-test-python needs a `tasks.md` in `specs/001-smoke-hello-world/` for E2E to pass; add it as part of T007 validation or as a separate prerequisite step
