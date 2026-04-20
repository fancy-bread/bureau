# Tasks: Builder Git Workflow

**Input**: Design documents from `specs/005-builder-git-workflow/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story. US1 (happy-path PR) is foundational and must complete before US2 (git failure escalation) can be tested meaningfully.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label [US1]–[US2]

---

## Phase 1: Setup

**Purpose**: Extend state and add new escalation reasons before any node implementation begins.

- [x] T001 Add `Phase.GIT_COMMIT = "git_commit"` to the `Phase` StrEnum in `bureau/state.py`
- [x] T002 Add three new values to `EscalationReason` in `bureau/state.py`: `DIRTY_REPO = "DIRTY_REPO"`, `GIT_PUSH_FAILED = "GIT_PUSH_FAILED"`, `GIT_BRANCH_EXISTS = "GIT_BRANCH_EXISTS"`
- [x] T003 Add `"branch_name": ""` to the dict returned by `make_initial_state()` in `bureau/state.py`

---

## Phase 2: Foundational — Dirty Repo Check (blocks US1 and US2)

**Goal**: Bureau escalates with `DIRTY_REPO` before doing any work if the target repo has uncommitted changes or untracked files.

**Independent Test**: Run `bureau run <spec> --repo <dirty-repo>` where dirty-repo has an untracked file. Assert `run.escalated` with `DIRTY_REPO` in stdout. Run `bureau run <spec> --repo <clean-repo>`. Assert no `DIRTY_REPO` escalation.

- [x] T004 Add dirty repo check to `bureau/nodes/repo_analysis.py` immediately after `parse_repo_config()` succeeds: run `subprocess.run(["git", "-C", repo_path, "status", "--porcelain"], capture_output=True, text=True)`; if stdout is non-empty, collect the file list and call `_escalate(state, f"Target repo has uncommitted changes:\n{output}", EscalationReason.DIRTY_REPO)` with `what_is_needed="Commit, stash, or discard changes in the target repo before running bureau."` and options `["git stash && bureau resume <run-id>", "git checkout . && git clean -fd to discard all changes", "bureau abort <run-id>"]`; add `import subprocess` to imports

**Checkpoint**: `pytest tests/integration/test_graph_run.py -k dirty` passes (test added in Polish phase).

---

## Phase 3: User Story 1 — Happy-Path Git Workflow (Priority: P1)

**Goal**: After Critic passes, bureau creates `feat/<spec-name>-<run-id-prefix>` branch, stages all changes, commits with structured message, pushes, and `pr_create` opens a PR from that branch.

**Independent Test**: Run E2E smoke test against bureau-test. Assert exit code 0, `[bureau] phase.started phase=git_commit` and `phase.completed phase=git_commit` in stdout, `https://github.com/` URL in stdout, and that a branch named `feat/smoke-hello-world-<run-id-prefix>` exists in bureau-test remote.

- [x] T005 [US1] Create `bureau/nodes/git_commit.py` with `git_commit_node(state)` function: (a) derive `spec_name` from `state.get("spec").name` if available, else `Path(state["spec_path"]).stem`, lowercased, non-alphanumeric chars replaced with `-`, truncated to 40 chars; (b) derive `run_id_prefix` as first 8 chars of `state["run_id"]` with leading `"run-"` stripped; (c) compute `branch_name = f"feat/{spec_name}-{run_id_prefix}"`; (d) attempt `git -C repo_path checkout -b branch_name` up to 3 times, appending `-2` and `-3` on collision (non-zero exit where stderr contains "already exists"); (e) on 3 failures escalate with `EscalationReason.GIT_BRANCH_EXISTS`; (f) run `git -C repo_path add -A`; (g) run `git -C repo_path commit -m f"feat: {spec_name} [bureau/{run_id_prefix}]"`; (h) run `git -C repo_path push origin branch_name`; on non-zero push exit escalate with `EscalationReason.GIT_PUSH_FAILED`; (i) on success return `{**state, "branch_name": branch_name, "phase": Phase.PR_CREATE, "_route": "ok"}`; wrap entire body in `with events.phase(Phase.GIT_COMMIT):`; import `subprocess`, `Path`, `events`, `Phase`, `Escalation`, `EscalationReason`, `datetime`, `timezone`
- [x] T006 [US1] Wire `git_commit_node` into `bureau/graph.py`: import `git_commit_node` from `bureau.nodes.git_commit`; add `graph.add_node("git_commit", git_commit_node)`; add `_route_git_commit` router returning `state.get("_route", "ok")`; replace `"pass": "pr_create"` in critic conditional edges with `"pass": "git_commit"`; add `graph.add_conditional_edges("git_commit", _route_git_commit, {"ok": "pr_create", "escalate": "escalate"})`
- [x] T007 [US1] Update `bureau/nodes/pr_create.py`: replace `branch = spec.branch if spec else f"bureau/{run_id[:8]}"` with `branch = state.get("branch_name") or (spec.branch if spec else f"feat/unknown-{run_id[:8]}")`

**Checkpoint**: `pytest tests/e2e/ -k test_smoke_hello_world` passes with `phase.started phase=git_commit` and PR URL in stdout.

---

## Phase 4: User Story 2 — Git Failure Escalation (Priority: P2)

**Goal**: Any git failure (branch creation, push) produces a structured escalation that identifies the operation and provides recovery instructions — not a silent failure or unhandled exception.

**Independent Test**: Point bureau at a repo with no git remote. Assert `run.escalated` in stdout and `GIT_PUSH_FAILED` in the escalation reason. Verify the escalation message names the failed operation.

- [x] T008 [US2] Add unit test `test_push_failure_escalation` to `tests/unit/test_git_commit_node.py`: mock `subprocess.run` so that the `git push` call returns exit code 1 with stderr `"fatal: 'origin' does not appear to be a git repository"`; assert the returned state has `"_route": "escalate"`; assert the escalation `what_happened` contains `"git push"` and the stderr text; assert `reason == EscalationReason.GIT_PUSH_FAILED`

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T009 [P] Add integration test `test_dirty_repo_escalates` to `tests/integration/test_graph_run.py`: create `target_repo` fixture with a valid `.bureau/config.toml` and an untracked file `dirty.txt`; run `bureau run <spec> --repo <target_repo>`; assert `"DIRTY_REPO"` in `result.stdout`
- [x] T010 [P] Add unit tests in `tests/unit/test_git_commit_node.py`: (a) `test_branch_name_derivation` — assert `feat/smoke-hello-world-deaaf184` from spec path `specs/001-smoke-hello-world/spec.md` and run_id `run-deaaf184`; (b) `test_branch_name_truncation` — assert branch name does not exceed 60 chars total for a long spec name; (c) `test_spec_name_kebab_case` — assert spaces and underscores in spec name become hyphens; (d) `test_pr_failed_escalation_intact` — call `pr_create_node` with a state where `gh pr create` returns non-zero; assert `PR_FAILED` escalation fires (verifies T007 refactor didn't break existing escalation path)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (uses `EscalationReason.DIRTY_REPO`)
- **US1 (Phase 3)**: Depends on Phase 1 (uses `Phase.GIT_COMMIT`) — Phase 2 can run in parallel
- **US2 (Phase 4)**: Depends on T005 (git_commit_node must exist to test its escalation paths)
- **Polish (Phase 5)**: Depends on all phases

### Within Each Phase

- T001 → T002 → T003 (all state.py, sequential)
- T004 (repo_analysis.py, after T002)
- T005 → T006 → T007 (sequential: node before graph wiring before pr_create update)
- T008 (unit test for push failure escalation — depends on T005)
- T009 and T010 are parallel (different test files)

### Parallel Opportunities

```bash
# After T003:
T004 (repo_analysis dirty check) can start
T005 (git_commit_node) can start in parallel with T004
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: state.py additions (T001–T003)
2. Complete Phase 2: dirty repo check in repo_analysis (T004)
3. Complete Phase 3: git_commit_node + graph wiring + pr_create update (T005–T007)
4. **STOP and VALIDATE**: Run `pytest tests/e2e/ -k test_smoke_hello_world`
5. E2E smoke test should now show `phase.started phase=git_commit` and a real PR URL

### Incremental Delivery

1. Phase 1+2 → dirty repo protection in place
2. Phase 3 → full happy-path E2E works
3. Phase 4 → escalation paths verified
4. Phase 5 → unit + integration test coverage

---

## Notes

- T008 is a unit test for push failure — mock subprocess and assert escalation fields; written after T005 creates the node
- The dirty repo check in T004 uses `git status --porcelain` which outputs one line per changed/untracked file; any non-empty output means dirty
- Branch name max length: Git allows 255 chars but GitHub UI truncates at ~60; the 40-char spec name truncation + 8-char run prefix + `feat/` prefix + `-` separator = ~54 chars max — safe
- `git add -A` stages everything including deletions; this is intentional — Builder may delete files as part of a refactor
