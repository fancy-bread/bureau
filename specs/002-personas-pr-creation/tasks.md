# Tasks: Bureau Personas and PR Creation

**Input**: Design documents from `specs/002-personas-pr-creation/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story — each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label [US1]–[US4]
- File paths relative to repo root

---

## Phase 1: Setup (New Packages)

**Purpose**: Create the `bureau/personas/` and `bureau/tools/` package directories before any implementation begins.

- [x] T001 Create `bureau/personas/__init__.py` (empty package init)
- [x] T002 Create `bureau/tools/__init__.py` (empty package init)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data types, state extension, config extension, tool executors, and escalation codes that all four personas depend on. No user story work begins until this phase is complete.

**⚠️ CRITICAL**: Blocks all user story phases.

- [x] T003 Create `bureau/models.py` — Pydantic model classes `Task`, `TaskPlan`, `BuildAttempt`, `RalphRound`, `CriticFinding`, `CriticVerdict`, `RunSummary` per `specs/002-personas-pr-creation/data-model.md`
- [x] T004 Extend `bureau/state.py` `RunState` TypedDict with new keys: `task_plan`, `ralph_round`, `builder_attempts`, `build_attempts`, `ralph_rounds`, `critic_findings`, `run_summary` (all JSON-serialisable; see data-model.md Extended Types)
- [x] T005 Extend `bureau/config.py` `BureauConfig` with Ralph Loop limits (`max_builder_attempts=3`, `max_ralph_rounds=3`, `command_timeout=300`) and model selection fields (`planner_model`, `builder_model`, `critic_model`); verify `anthropic>=0.25` in `pyproject.toml`
- [x] T006 Update `bureau/nodes/repo_analysis.py` to parse `[ralph_loop]` and `[bureau]` TOML sections from `.bureau/config.toml` into new `BureauConfig` fields
- [x] T007 Add `bureau/data/constitution.md` (bureau's bundled default constitution — the six ASDLC principles) and a `load_constitution(repo_path, config) -> str` helper in `bureau/config.py` that returns the project-specific constitution if present at `config.constitution`, otherwise the bundled default
- [x] T008 [P] Implement `bureau/tools/file_tools.py` — `read_file`, `write_file`, `list_directory`: Anthropic tool JSON schemas (matching `contracts/persona-tool-interface.md`) and executor functions; `write_file` must validate path is within `repo_path`
- [x] T009 [P] Implement `bureau/tools/shell_tools.py` — `run_command`: Anthropic tool JSON schema and executor using `subprocess.run(cwd=repo_path, timeout=command_timeout, capture_output=True)`; truncate stdout/stderr to 4000 chars (most recent retained); return `{"stdout": ..., "stderr": ..., "exit_code": ...}`
- [x] T010 Extend `bureau/nodes/escalate.py` to handle all new `EscalationReason` codes (`PLAN_INCOMPLETE`, `RALPH_EXHAUSTED`, `RALPH_ROUNDS_EXCEEDED`, `CONSTITUTION_VIOLATION`, `PR_FAILED`) with structured `What happened / What's needed / Options` output per `contracts/terminal-events.md`

**Checkpoint**: Foundation ready — all four user story phases can now proceed in dependency order.

---

## Phase 3: User Story 1 — Planner produces a verified task plan (Priority: P1) 🎯 MVP

**Goal**: Replace the planner stub with a real Claude-powered Planner that reads the spec, analyses the repo, and produces a dependency-ordered TaskPlan written to run memory.

**Independent Test**: Given a valid spec and a `.bureau/config.toml`, running `bureau run <spec>` through the planner phase produces a `task_plan` dict in run state, `phase.completed phase=planner` in stdout, and `bureau show <run-id>` reflects the plan.

- [x] T011 [US1] Implement `bureau/personas/planner.py` — `build_planner_messages(spec, constitution, config) -> list`: system prompt (constitution + spec content with `cache_control` on last static block), user turn; `run_planner(client, messages, tools, config) -> TaskPlan`: Anthropic tool-use loop with `read_file` and `list_directory` tools until model stops calling tools, parse final assistant text as `TaskPlan` JSON via `TaskPlan.model_validate(json.loads(...))`
- [x] T012 [US1] Replace stub `bureau/nodes/planner.py` — read spec text and config from state, load constitution via `load_constitution()`, call `run_planner()`, validate `uncovered_frs` is empty for P1 FRs (escalate `PLAN_INCOMPLETE` if not), serialise `TaskPlan` to dict and write to `state["task_plan"]`, emit `phase.started`/`phase.completed phase=planner` events
- [x] T013 [P] [US1] Add unit tests in `tests/unit/test_persona_planner.py` — mock `anthropic.Anthropic` client, verify `build_planner_messages` includes spec content and `cache_control`, verify `TaskPlan` parsed from fixture JSON response, verify escalation when P1 FR not in `fr_coverage`
- [x] T014 [US1] Add integration test in `tests/integration/test_planner_node.py` — inject fixture spec and `BureauConfig` into `RunState`, run planner node via the LangGraph graph, verify `state["task_plan"]` contains at least one task with a `fr_ids` entry matching a FR from the spec

**Checkpoint**: `bureau run` through planner phase completes with task plan in state.

---

## Phase 4: User Story 2 — Builder implements the plan iteratively until tests pass (Priority: P1)

**Goal**: Replace the builder stub with a real Claude-powered Builder that applies code changes to the target repo, runs tests, and retries on failure — the Ralph Loop inner loop.

**Independent Test**: Given a state with a valid `task_plan`, running bureau through the builder phase produces code changes on the feature branch and `phase.completed phase=builder` in stdout (with at least one `ralph.attempt` event).

- [x] T015 [US2] Implement `bureau/personas/builder.py` — `build_builder_messages(spec, task_plan, constitution, previous_attempts, config) -> list`: system prompt (constitution + spec + task plan with `cache_control` on last static block, prior `BuildAttempt` summaries in user turn); `run_builder_attempt(client, messages, tools, repo_path, config) -> BuildAttempt`: tool-use loop dispatching all four tools (`read_file`, `write_file`, `list_directory`, `run_command`), record `files_changed`, `test_output`, `test_exit_code`, `passed`; return `BuildAttempt`
- [x] T016 [US2] Replace stub `bureau/nodes/builder.py` — Ralph Loop inner: run `install_cmd` once at the start of each round, loop calling `run_builder_attempt` up to `max_builder_attempts`, run `build_cmd` before `test_cmd` when non-empty, emit `ralph.started round=N` and `ralph.attempt round=N attempt=M result=pass|fail` per `contracts/terminal-events.md`, append `BuildAttempt` dicts to `state["build_attempts"]`, write Builder change summary to `state["memory"]` for Critic; escalate `RALPH_EXHAUSTED` when all attempts fail
- [x] T017 [P] [US2] Add unit tests in `tests/unit/test_persona_builder.py` — mock Anthropic API and `subprocess.run`, verify tool dispatcher routes `read_file`/`write_file`/`run_command` calls correctly, verify `BuildAttempt.passed=True` on exit code 0, verify attempt loop terminates early on first pass, verify `files_changed` list populated from `write_file` calls
- [x] T018 [US2] Add integration test in `tests/integration/test_builder_node.py` — inject fixture `task_plan` and `BureauConfig` into `RunState` with a minimal fixture repo, run builder node, verify `build_attempts` appended to state with correct `round`/`attempt` indices and `ralph.attempt` events captured from stdout

**Checkpoint**: `bureau run` through builder phase produces code changes and passing tests.

---

## Phase 5: User Story 3 — Critic audits and approves or blocks the implementation (Priority: P1)

**Goal**: Replace the critic stub with a real Claude-powered Critic that audits the Builder's output against the spec's FRs and the constitution, issues a structured verdict, and drives Ralph Loop routing.

**Independent Test**: Given a state with a builder change summary, running bureau through the critic phase produces a `CriticVerdict` with findings in state, `phase.completed phase=critic verdict=pass|revise|escalate` in stdout, and correct routing to `pr_create`, `builder`, or `escalate`.

- [x] T019 [US3] Implement `bureau/personas/critic.py` — `build_critic_messages(spec_frs, constitution, builder_summary, previous_findings, config) -> list`: system prompt (spec FRs + constitution with `cache_control`, builder summary and previous round findings in user turn); `run_critic(client, messages, config) -> CriticVerdict`: single Anthropic call requesting structured JSON output per `CriticVerdict` schema, parse via `CriticVerdict.model_validate(json.loads(...))`, if any `CriticFinding.verdict == "violation"` force `verdict = "escalate"`
- [x] T020 [US3] Replace stub `bureau/nodes/critic.py` — load constitution, call `run_critic()`, construct `RalphRound` from current `ralph_round` index, `BuildAttempt` list for this round, and `CriticVerdict`; append serialised `RalphRound` to `state["ralph_rounds"]`, write `critic_findings` to state, reset `builder_attempts` to 0 in state, emit `phase.started`/`phase.completed phase=critic duration=... verdict=<verdict>` events
- [x] T021 [US3] Update `_route_critic` conditional edge in `bureau/graph.py` — read `state["critic_findings"]` verdict and `state["ralph_round"]` vs `state["config"]["max_ralph_rounds"]`; route: `pass` → `pr_create`; `escalate` → `escalate` node with reason `CONSTITUTION_VIOLATION`; `revise` + `ralph_round < max_ralph_rounds` → `builder` (increment `ralph_round`, reset `builder_attempts`); `revise` + `ralph_round >= max_ralph_rounds` → `escalate` node with reason `RALPH_ROUNDS_EXCEEDED`
- [x] T022 [P] [US3] Add unit tests in `tests/unit/test_persona_critic.py` — mock Anthropic API, verify `build_critic_messages` includes all P1 FR IDs and constitution text, verify `CriticVerdict` JSON parsed from fixture responses for all three verdicts, verify constitution violation in any finding forces `verdict="escalate"`, verify `CriticFinding` fields (`type`, `ref_id`, `verdict`, `remediation`)
- [x] T023 [US3] Add integration test in `tests/integration/test_critic_node.py` — inject fixture builder summary and spec FRs into `RunState`, run critic node, verify one `RalphRound` appended to `state["ralph_rounds"]` with correct `round` index and `critic_findings` populated in state

**Checkpoint**: Full Ralph Loop (`builder → critic → builder → critic → pr_create`) routes correctly in the LangGraph graph.

---

## Phase 6: User Story 4 — PR creation opens a pull request with a run summary (Priority: P2)

**Goal**: Replace the pr_create stub with a real implementation that builds a `RunSummary`, renders the PR body, and calls `gh pr create`.

**Independent Test**: Given a state with a `pass` Critic verdict, running bureau through pr_create emits `run.completed pr=<url>` and opens a PR with a description containing all required fields (FR-018).

- [x] T024 [US4] Replace stub `bureau/nodes/pr_create.py` — construct `RunSummary` from state fields (`run_id`, `spec_name`, `spec_path`, `branch`, `ralph_rounds` count, `frs_addressed` from final `RalphRound`, `critic_verdict`, `critic_findings` from final round, `duration_seconds`, `completed_at`); render PR body Markdown including all FR-018 required fields; call `gh pr create --title "<spec_name>" --body "<rendered>"` via `subprocess.run`; write `pr_url` to `state["run_summary"]`; emit `run.completed pr=<url> duration=...`; escalate `PR_FAILED` on non-zero exit or subprocess error
- [x] T025 [US4] Add integration test in `tests/integration/test_pr_create_node.py` — mock `subprocess.run` to return exit code 0 with a fake PR URL, inject complete fixture state (including `ralph_rounds` list and `critic_findings`), run pr_create node, verify PR body contains `run_id`, `spec_name`, FR IDs, `critic_verdict`, ralph rounds count, and `run.completed` event captured from stdout

**Checkpoint**: `bureau run` completes end-to-end with a PR URL in output.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T026 [P] Run `ruff check .` and fix any linting issues in `bureau/personas/`, `bureau/tools/`, `bureau/models.py`, and updated node files
- [x] T027 Verify quickstart.md Scenario 1 (happy path) end-to-end against a test repo: confirm `run.started` → `phase.completed phase=planner` → `ralph.attempt round=0 attempt=0 result=pass` → `phase.completed phase=critic verdict=pass` → `run.completed pr=<url>`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 Planner (Phase 3)**: Depends on Phase 2 — no dependency on US2/US3/US4
- **US2 Builder (Phase 4)**: Depends on Phase 2 — depends on US1 (Planner writes task_plan; Builder reads it)
- **US3 Critic (Phase 5)**: Depends on Phase 2 and US2 — Builder must write summary for Critic to audit
- **US4 PR Creation (Phase 6)**: Depends on US3 — Critic `pass` verdict gates pr_create
- **Polish (Phase 7)**: Depends on all phases complete

### User Story Dependencies

- **US1 → US2**: Builder reads `task_plan` from state written by Planner
- **US2 → US3**: Critic reads Builder change summary from state/memory
- **US3 → US4**: PR creation requires Critic `pass` verdict and `ralph_rounds` history
- **US2 ↔ US3**: Ralph Loop routing in `graph.py` (T021) must be in place before end-to-end testing

### Within Each User Story

- Persona implementation (e.g. T011) → node replacement (T012) → tests (T013, T014)
- Persona and node tasks are sequential; test tasks [P] can run in parallel with each other

### Parallel Opportunities

- T001 and T002 can run together
- T008 and T009 can run together (different files)
- T013 (planner unit test) and T014 (planner integration test) can run together once T011+T012 are done
- T017 and T018 can run together once T015+T016 are done
- T022 and T023 can run together once T019+T020+T021 are done
- T026 can run in parallel with T027

---

## Parallel Example: Phase 2 Foundational

```bash
# After T003-T007 complete sequentially:
Task: "Implement bureau/tools/file_tools.py"    # T008
Task: "Implement bureau/tools/shell_tools.py"   # T009
# These touch different files — run in parallel
```

---

## Implementation Strategy

### MVP (P1 stories only — US1 + US2 + US3)

1. Phase 1: Setup (T001–T002)
2. Phase 2: Foundational (T003–T010)
3. Phase 3: US1 Planner (T011–T014)
4. Phase 4: US2 Builder (T015–T018)
5. Phase 5: US3 Critic (T019–T023)
6. **STOP and VALIDATE**: Run bureau end-to-end through planner→builder→critic, confirm `phase.completed phase=critic verdict=pass`

### Incremental Delivery

1. Foundation → Planner → verify task plan output (bureau show)
2. Add Builder → verify code changes and passing tests
3. Add Critic → verify verdict and Ralph Loop routing
4. Add PR Creation → verify PR opened with full run summary
5. Each increment is independently verifiable via `bureau show <run-id>` and stdout events

---

## Notes

- [P] tasks = different files, no dependencies on each other
- All state values MUST be JSON-serialisable dicts (not dataclass instances) — LangGraph checkpoint requirement
- Prompt caching: apply `cache_control: {"type": "ephemeral"}` to the last static `text` block in each persona's system prompt
- Critic constitution violations MUST produce `escalate` verdict regardless of `ralph_round` — no exceptions
- Builder's `install_cmd` runs once per Ralph Loop round (not per attempt) — round starts in node, not persona
- `gh pr create` is the only PR mechanism — no Python GitHub library
