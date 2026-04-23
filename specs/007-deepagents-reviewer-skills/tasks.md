# Tasks: deepagents Builder Integration, Reviewer Rename, and Skills Vendoring

**Input**: Design documents from `/specs/007-deepagents-verifier-skills/`
**Prerequisites**: spec.md ✅ plan.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

---

## Phase 1: Setup

**Purpose**: Add the deepagents dependency and create the skills directory skeleton.

- [x] T001 Add `deepagents>=0.5.3` to `dependencies` list in `pyproject.toml`
- [x] T002 Create placeholder files `bureau/skills/default/build/.gitkeep`, `bureau/skills/default/test/.gitkeep`, `bureau/skills/default/ship/.gitkeep`, `bureau/skills/default/review/.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Rename the core data types and enum values that both US1 and US2 depend on. Must complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Update `bureau/state.py` — rename `Phase.CRITIC = "critic"` → `Phase.REVIEWER = "reviewer"`; rename `RepoContext.critic_model` → `reviewer_model`; rename key `"critic_findings"` → `"reviewer_findings"` in `make_initial_state()`
- [x] T004 Update `bureau/models.py` — rename `CriticFinding` → `ReviewerFinding`, `CriticVerdict` → `ReviewerVerdict`; rename `RalphRound` fields `critic_verdict` → `reviewer_verdict` and `critic_findings` → `reviewer_findings`; rename `RunSummary` fields `critic_verdict` → `reviewer_verdict` and `critic_findings` → `reviewer_findings`
- [x] T005 Update `bureau/config.py` — rename `critic_model: str = "claude-opus-4-7"` field to `reviewer_model`

**Checkpoint**: Core types renamed — user story implementation can now proceed.

---

## Phase 3: User Story 1 — Builder Powered by deepagents (Priority: P1) 🎯 MVP

**Goal**: Replace the 50-turn Anthropic SDK loop, FILE_TOOLS, and SHELL_TOOLS in the Builder persona with a `create_deep_agent`-backed adapter. The Builder still produces a `BuildAttempt` record; the state bridge is the only interface change.

**Independent Test**: Run `bureau run <spec-folder> --repo <path>` with a tasks.md that creates a file. Confirm `ralph.attempt` events appear in stdout and the target file exists in the repo after the run.

- [x] T006 [US1] Rewrite `bureau/personas/builder.py` — replace the entire body of `run_builder_attempt()` with a deepagents adapter: construct `create_deep_agent(model=model, system_prompt=system, middleware=(FilesystemMiddleware(backend=FilesystemBackend(root_dir=repo_path)), SummarizationMiddleware(model=model, backend=FilesystemBackend(), keep=("messages", 20))))` and `.invoke({"messages": [HumanMessage(content=user_content)]})`; implement a `_extract_build_attempt()` state bridge (~30 lines) that walks `AgentState.messages` to collect `files_changed` from `write_file` tool calls and `test_exit_code`/`test_output` from `run_command` tool results; remove all `FILE_TOOLS`, `SHELL_TOOLS`, and `anthropic` imports
- [x] T007 [US1] Update `bureau/nodes/builder.py` — route `phase=Phase.REVIEWER` (not `Phase.CRITIC`) on success; derive `skills_root = Path(__file__).parent.parent / "skills" / "default"` and pass it through to `run_builder_attempt()`
- [x] T008 [US1] Update `tests/unit/test_persona_builder.py` — replace tool-dispatch mocks with a `create_deep_agent` mock that returns a fake `AgentState`; assert the state bridge produces a valid `BuildAttempt` with correct `passed`, `files_changed`, and `test_exit_code` fields

**Checkpoint**: Builder uses deepagents; produces `BuildAttempt`; routes to Reviewer on pass.

---

## Phase 4: User Story 2 — Critic Renamed to Reviewer Throughout (Priority: P2)

**Goal**: Zero occurrences of "critic" in production Python source. Behaviour unchanged. All tests pass.

**Independent Test**: After this phase, run `grep -ri "critic" bureau/ tests/ --include="*.py"` — zero matches in production files signals completion. Full test suite passes.

- [x] T009 [P] [US2] Create `bureau/nodes/reviewer.py` from `bureau/nodes/critic.py` — rename function `critic_node` → `reviewer_node`; import `ReviewerFinding`, `ReviewerVerdict` from `bureau.models`; update memory write key `"critic_findings"` → `"reviewer_findings"`; update all event emissions and `_escalate` calls to use `Phase.REVIEWER`
- [x] T010 [P] [US2] Create `bureau/personas/reviewer.py` from `bureau/personas/critic.py` — rename function `run_critic` → `run_reviewer`; import `ReviewerVerdict`, `ReviewerFinding` instead of `CriticVerdict`, `CriticFinding`; update JSON schema string in `_SYSTEM_TEMPLATE` to match renamed models
- [x] T011 [US2] Delete `bureau/nodes/critic.py` and `bureau/personas/critic.py` (after T009 and T010 complete)
- [x] T012 [US2] Update `bureau/graph.py` — replace `from bureau.nodes.critic import critic_node` with `from bureau.nodes.reviewer import reviewer_node`; change `graph.add_node("critic", critic_node)` → `graph.add_node("reviewer", reviewer_node)`; rename `_route_critic` → `_route_reviewer`; update conditional edge map `{"pass": "git_commit", "revise": "builder", "escalate": "escalate"}` source from `"critic"` → `"reviewer"`
- [x] T013 [P] [US2] Update `bureau/nodes/pr_create.py` — rename all `state.get("critic_findings")` / `state["critic_findings"]` accesses to `reviewer_findings`; update `RunSummary` field name in construction call
- [x] T014 [P] [US2] Rename `tests/unit/test_persona_critic.py` → `tests/unit/test_persona_reviewer.py`; update `from bureau.personas.reviewer import run_reviewer`; update all assertions referencing `CriticVerdict` → `ReviewerVerdict` and `CriticFinding` → `ReviewerFinding`
- [x] T015 [P] [US2] Rename `tests/integration/test_critic_node.py` → `tests/integration/test_reviewer_node.py`; update `from bureau.nodes.reviewer import reviewer_node`; update all phase string assertions `"critic"` → `"reviewer"`; update state key assertions `critic_findings` → `reviewer_findings`
- [x] T016 [P] [US2] Update `tests/integration/test_graph_run.py` — replace any `"critic"` phase string in assertions with `"reviewer"`
- [x] T017 [P] [US2] Update `tests/e2e/test_bureau_e2e.py` — update `expected_phases` list in `_assert_phase_order()`: `"critic"` → `"reviewer"`
- [x] T018 [US2] Amend `.specify/memory/constitution.md` — bump version `1.1.0` → `1.2.0`; add PATCH Sync Impact Report (HTML comment) at top; replace "Critic" with "Reviewer" in Principle III body text and the Agent Personas table row

**Checkpoint**: Zero "critic" references in production code; all tests pass.

---

## Phase 5: User Story 3 — Vendored Default Skills Available to Builder (Priority: P3)

**Goal**: Four ASDLC SKILL.md files committed under `bureau/skills/default/`; skills are bundled in the installed package and discoverable by `SkillsMiddleware` without any runtime configuration.

**Independent Test**: After this phase, import `SkillsMiddleware` in a Python REPL, point it at `bureau/skills/default/build/`, and confirm at least one skill loads without error.

- [x] T019 [P] [US3] Write `bureau/skills/default/build/SKILL.md` — YAML frontmatter: `name: build`, `description: Implement tasks from the task plan by writing and modifying source files in the target repository`; body: step-by-step ASDLC build instructions (read existing code first, implement in task order, run test command after each significant change, report files changed)
- [x] T020 [P] [US3] Write `bureau/skills/default/test/SKILL.md` — YAML frontmatter: `name: test`, `description: Execute the configured test suite and interpret results, retrying on failure`; body: ASDLC test instructions (run `test_cmd`, parse exit code, extract failing test names, locate and fix root causes, re-run until exit code 0 or max attempts reached)
- [x] T021 [P] [US3] Write `bureau/skills/default/ship/SKILL.md` — YAML frontmatter: `name: ship`, `description: Verify all tasks are complete and implementation is ready for handoff to the Reviewer`; body: ASDLC ship protocol (confirm all tasks.md items are addressed, run final test pass, produce a structured implementation summary listing files changed and test result)
- [x] T022 [P] [US3] Write `bureau/skills/default/review/SKILL.md` — YAML frontmatter: `name: review`, `description: Review the Builder's implementation against spec functional requirements and the bureau constitution`; body: ASDLC review protocol (evaluate each FR as met/unmet, check for constitution violations, output structured verdict: pass/revise/escalate with per-finding detail and remediation)
- [x] T023 [US3] Update `pyproject.toml` `[tool.setuptools.package-data]` — change `bureau = ["data/*.md", "data/env.example"]` to `bureau = ["data/*.md", "data/env.example", "skills/**/*.md"]`; delete the four `.gitkeep` placeholder files created in T002

**Checkpoint**: Four SKILL.md files present and loadable; bundled in package install.

---

## Phase 6: User Story 4 — ASDLC Phase Skills Wired to Builder and Reviewer (Priority: P4)

**Goal**: Builder gets build/test/ship skills only; Reviewer gets review skill only. Missing required skills escalate at node init before any attempt.

**Independent Test**: Start a bureau run with skills present; inspect Builder's resolved middleware and confirm `SkillsMiddleware.sources` contains only build/test/ship paths. Inspect Reviewer system prompt and confirm it contains the review skill body. Remove a required skill and confirm bureau escalates with `BLOCKER` at init time rather than mid-run.

- [x] T024 [US4] Update `bureau/personas/builder.py` — add `SkillsMiddleware(backend=FilesystemBackend(root_dir=str(skills_root)), sources=[str(skills_root / "build"), str(skills_root / "test"), str(skills_root / "ship")])` to the `middleware` tuple in `create_deep_agent`; add `MemoryMiddleware(backend=FilesystemBackend(root_dir=str(context_dir)), sources=[str(context_dir)])` where `context_dir` is a `tempfile.mkdtemp()` directory written with `plan_text` at function entry; add pre-flight check that each of `build/`, `test/`, `ship/` has at least one `.md` file — raise `ValueError(f"Required skill directory empty: {path}")` if any are missing
- [x] T025 [US4] Update `bureau/nodes/reviewer.py` — add `_load_review_skill(skills_root: Path) -> str` helper that reads all `.md` files in `skills_root / "review"` and returns concatenated content; call it at top of `reviewer_node` and prepend result to the system template string passed to `run_reviewer()`; add pre-flight check: if `review/` has no `.md` files, return `_escalate(state, "review skill missing from bureau/skills/default/review/", EscalationReason.BLOCKER)`
- [x] T026 [US4] Update `bureau/nodes/builder.py` — wrap the `run_builder_attempt()` call in a `try/except ValueError` block; on `ValueError` (skills pre-flight failure) return `_escalate(state, str(exc), EscalationReason.BLOCKER)` with structured message

**Checkpoint**: Each agent constrained to its role's skills; missing skills escalate cleanly.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T027 Run `pytest tests/` from repo root and fix any import errors or assertion failures introduced by the rename (T009–T018) and deepagents refactor (T006–T008)
- [x] T028 Run `grep -ri "critic" bureau/ tests/ --include="*.py"` and verify zero matches in production source; fix any stragglers
- [x] T029 Update `CLAUDE.md` `## Recent Changes` section — add entry for `007-deepagents-verifier-skills` summarising: deepagents>=0.5.3 added; Builder replaced with create_deep_agent adapter; Critic renamed to Reviewer throughout; ASDLC skills vendored to `bureau/skills/default/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 (needs Phase.REVIEWER)
- **US2 (Phase 4)**: Depends on Phase 2 (needs ReviewerVerdict, ReviewerFinding); T011 depends on T009+T010; T012 depends on T011
- **US3 (Phase 5)**: Depends on Phase 1 (directory structure); independent of US1 and US2
- **US4 (Phase 6)**: Depends on US1 (bureau/personas/builder.py exists), US2 (bureau/nodes/reviewer.py exists), and US3 (SKILL.md files present)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2 or US3
- **US2 (P2)**: Can start after Phase 2 — no dependency on US1 or US3; T009/T010 are parallel
- **US3 (P3)**: Can start after Phase 1 — fully independent of US1 and US2; T019–T022 are all parallel
- **US4 (P4)**: Requires US1 + US2 + US3 complete

### Parallel Opportunities

Within Phase 4 (US2): T009, T010, T013, T014, T015, T016, T017 can all run in parallel (different files).
Within Phase 5 (US3): T019, T020, T021, T022 can all run in parallel (different files).
US3 can run concurrently with US1 and US2.

---

## Parallel Example: User Story 2 (Rename)

```
# These can all start simultaneously after T011 (old files deleted):
T013 — update pr_create.py
T014 — rename test_persona_critic.py
T015 — rename test_critic_node.py
T016 — update test_graph_run.py
T017 — update test_bureau_e2e.py
```

## Parallel Example: User Story 3 (Skills)

```
# All four skill files can be written simultaneously:
T019 — bureau/skills/default/build/SKILL.md
T020 — bureau/skills/default/test/SKILL.md
T021 — bureau/skills/default/ship/SKILL.md
T022 — bureau/skills/default/review/SKILL.md
```

---

## Implementation Strategy

### MVP First (US1 + US2 only)

1. Phase 1: Setup
2. Phase 2: Foundational (rename state types)
3. Phase 3: US1 — deepagents Builder
4. Phase 4: US2 — Critic → Reviewer rename
5. **STOP and VALIDATE**: run full test suite; verify zero "critic" matches; run smoke e2e

### Incremental Delivery

1. Setup + Foundational → typed foundation ready
2. US1 → deepagents Builder working → validate with a real spec run
3. US2 → rename complete → validate test suite passes
4. US3 → skills vendored → validate skill loading
5. US4 → role-scoped skills wired → validate isolation and escalation
6. Polish → clean grep, full test suite green

---

## Notes

- `[P]` = different files, no blocking dependency on an incomplete sibling task
- Tasks T009 and T010 must complete before T011 (delete old files)
- `skills_root` is always derived as `Path(__file__).parent.parent / "skills" / "default"` inside bureau package — never an absolute user path
- The deepagents `AgentState.messages` list contains `HumanMessage`, `AIMessage`, and `ToolMessage` objects; the state bridge filters by type and tool name to extract BuildAttempt fields
- constitution.md amendment (T018) requires a Sync Impact Report HTML comment per governance rules
