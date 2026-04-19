# Tasks: Bureau E2E Test Suite

**Input**: Design documents from `specs/004-e2e-test-suite/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story — US5 (API key isolation) is foundational and must complete before any E2E test can run meaningfully.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label [US1]–[US5]

---

## Phase 1: Setup

**Purpose**: Add new dependencies and create the e2e test directory before any implementation begins.

- [ ] T001 Add `python-dotenv>=1.0` to `[project.dependencies]` in `pyproject.toml`
- [ ] T002 Add `pytest-timeout>=2.3` to `[project.optional-dependencies] dev` in `pyproject.toml`
- [ ] T003 Create `tests/e2e/__init__.py` (empty package init)

---

## Phase 2: Foundational — User Story 5: API Key Isolation (Priority: P1)

**Goal**: Bureau loads `ANTHROPIC_API_KEY` from `~/.bureau/.env` at startup so developers can keep bureau's Anthropic billing separate from Claude Code's Pro subscription credentials.

**Independent Test**: Start a shell where `ANTHROPIC_API_KEY` is NOT exported. Place a valid key in `~/.bureau/.env`. Run `bureau run --help`. Bureau starts without error. Run `tests/unit/test_dotenv_loading.py` — all pass.

**⚠️ CRITICAL**: Blocks all E2E user story phases — without dotenv loading, E2E tests can only run if the key is already in the shell environment.

- [ ] T004 [US5] Add `from dotenv import load_dotenv` and `load_dotenv(Path.home() / ".bureau" / ".env", override=False)` at the top of the CLI entrypoint callback in `bureau/cli.py`, before any subcommand executes; import `Path` from `pathlib`
- [ ] T005 [US5] Add key-presence guard in `bureau/cli.py`: in the Typer root callback (decorated with `@app.callback(invoke_without_command=True)`), after `load_dotenv`, check `os.environ.get("ANTHROPIC_API_KEY")`; if absent AND `ctx.invoked_subcommand in ("run", "resume")`, print `"[bureau] error: ANTHROPIC_API_KEY not set — add it to ~/.bureau/.env or export it in your shell"` and `raise typer.Exit(1)`; guard MUST NOT fire for `bureau --help`, `bureau list`, or `bureau abort`
- [ ] T006 [P] [US5] Create `bureau/data/env.example` with `ANTHROPIC_API_KEY=sk-ant-api03-your-key-here` and explanatory comment per `specs/004-e2e-test-suite/contracts/env-example.md`
- [ ] T007 [P] [US5] Add unit tests in `tests/unit/test_dotenv_loading.py` — test: (a) key loaded from `.env` file when not in shell env, (b) shell env value takes precedence over file value, (c) missing `.env` file does not raise, (d) missing key on a persona-invoking command prints human-readable error and exits 1; use `tmp_path` and `monkeypatch` to isolate `os.environ` and file system

**Checkpoint**: `pytest tests/unit/test_dotenv_loading.py` passes. `bureau --help` works with no key set. Bureau exits with clean error when key is absent and a persona node would be called.

---

## Phase 3: User Story 4 — Test Infrastructure (Priority: P1)

**Goal**: Provide the session-scoped fixtures, skip guards, and helper that all E2E tests depend on.

**Independent Test**: Run `pytest tests/e2e/ -v` with `BUREAU_TEST_REPO` absent — all tests skip with a clear message. Run with `ANTHROPIC_API_KEY` absent — all tests skip. Both produce exit code 0.

- [ ] T008 [US4] Create `tests/e2e/conftest.py` with: (a) module-level skip constants: `SKIP_NO_REPO = pytest.mark.skipif(not os.environ.get("BUREAU_TEST_REPO"), reason="BUREAU_TEST_REPO not set")` and `SKIP_NO_KEY = pytest.mark.skipif(not (os.environ.get("ANTHROPIC_API_KEY") or (Path.home()/".bureau/".env").exists() and "ANTHROPIC_API_KEY" in dotenv_values(Path.home()/".bureau/".env")), reason="ANTHROPIC_API_KEY not set in shell or ~/.bureau/.env")` — the key check MUST read from both `os.environ` and `~/.bureau/.env` via `dotenv_values()` since load_dotenv runs in the bureau subprocess, not the test process; (b) session-scoped `bureau_test_repo` fixture that reads `BUREAU_TEST_REPO`, asserts the path exists, runs `git -C <path> checkout main && git -C <path> pull` before `yield path`, then runs `git -C <path> checkout main` again in teardown (after yield) to leave the repo clean; (c) `run_bureau(spec_path: str, repo_path: str) -> subprocess.CompletedProcess` helper using `subprocess.run([bureau_exe(), "run", spec_path, "--repo", repo_path], capture_output=True, text=True, timeout=600)` — note: 600s subprocess timeout; use `@pytest.mark.timeout(650)` on tests for a 50s pytest-level safety net
- [ ] T009 [US4] Create `tests/e2e/test_bureau_e2e.py` skeleton — module-level `pytestmark` applying both skip conditions from conftest; import fixtures; no test functions yet (added in subsequent phases)

**Checkpoint**: `pytest tests/e2e/ -v` with missing env vars → all skipped, exit 0.

---

## Phase 4: User Story 1 — Smoke Test: Happy-Path Run (Priority: P1)

**Goal**: Assert that bureau completes a full run against `specs/001-smoke-hello-world/spec.md` in bureau-test, emitting `run.completed` and a PR URL.

**Independent Test**: `pytest tests/e2e/ -k test_smoke_hello_world -v` passes with env vars set.

- [ ] T010 [US1] Implement `test_smoke_hello_world` in `tests/e2e/test_bureau_e2e.py` with `@pytest.mark.timeout(650)`: run bureau against `specs/001-smoke-hello-world/spec.md`; assert exit code 0; assert `"[bureau] run.completed"` in stdout; assert a `https://github.com/` URL appears in stdout

**Checkpoint**: Smoke test asserts completion and PR URL.

---

## Phase 5: User Story 2 — Phase Events Structured and Ordered (Priority: P1)

**Goal**: Assert that all six phase events appear in pipeline order and that `ralph.attempt`, `run.completed` carry the required fields.

**Independent Test**: The assertions extend `test_smoke_hello_world` — no additional API call needed.

- [ ] T011 [US2] Add `_assert_phase_order(stdout: str)` helper in `tests/e2e/test_bureau_e2e.py` — extracts all `[bureau] phase.started phase=X` and `phase.completed phase=X` lines; asserts the six phases appear in order `validate_spec → repo_analysis → planner → builder → critic → pr_create`; asserts each `started` precedes its matching `completed`
- [ ] T012 [US2] Extend `test_smoke_hello_world` to call `_assert_phase_order(result.stdout)`; assert at least one `ralph.attempt` line contains `round=` `attempt=` and `result=pass`; assert `run.completed` line contains both `pr=` and `duration=` fields

**Checkpoint**: `test_smoke_hello_world` now validates completion, PR URL, phase order, ralph events, and run.completed fields.

---

## Phase 6: User Story 3 — Escalation Path (Priority: P2)

**Goal**: Assert that bureau emits `run.escalated` and no PR URL when run against `specs/004-escalation-missing-schema/spec.md`.

**Independent Test**: `pytest tests/e2e/ -k test_escalation_missing_artifact -v` — passes (or xfails) with env vars set.

- [ ] T013 [US3] Implement `test_escalation_missing_artifact` in `tests/e2e/test_bureau_e2e.py` with `@pytest.mark.timeout(650)` and `@pytest.mark.xfail(strict=False, reason="Planner may complete spec 004 instead of escalating — AI behaviour is non-deterministic")`: run bureau against `specs/004-escalation-missing-schema/spec.md`; assert `"[bureau] run.escalated"` in stdout; assert no `"https://github.com/"` URL in stdout; assert escalation output contains `"What happened"` and `"What's needed"`

**Checkpoint**: Escalation test runs and either passes or xfails gracefully.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T014 [P] Create `.github/workflows/e2e.yml` — `on: workflow_dispatch`; jobs: checkout bureau to `.`, checkout `fancy-bread/bureau-test` to `bureau-test/`; `pip install -e ".[dev]"`; `pytest tests/e2e/ -v --timeout=650` with `env: ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}`, `BUREAU_TEST_REPO: ${{ github.workspace }}/bureau-test`, `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`
- [ ] T015 [P] Update `README.md` — add "Credential Setup" section explaining `~/.bureau/.env` for local dev, `ANTHROPIC_API_KEY` shell env for CI, and reference to `bureau/data/env.example` as the canonical variable list

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational US5 (Phase 2)**: Depends on Phase 1 — BLOCKS all E2E phases (E2E tests need dotenv loading to work correctly)
- **US4 Test Infra (Phase 3)**: Depends on Phase 2 — conftest skip guards check key resolution after dotenv
- **US1 Smoke (Phase 4)**: Depends on Phase 3 — needs conftest fixtures
- **US2 Events (Phase 5)**: Depends on Phase 4 — extends the same test function
- **US3 Escalation (Phase 6)**: Depends on Phase 3 — uses same conftest, independent of US1/US2
- **Polish (Phase 7)**: Depends on all phases — CI workflow needs all tests to exist

### User Story Dependencies

- **US5 → US1, US2, US3**: Dotenv loading must be in place before E2E tests meaningfully test the key-from-file scenario
- **US4 → US1, US2, US3**: conftest.py fixtures are prerequisites for all test functions
- **US1 → US2**: US2 assertions extend the US1 test function
- **US3**: Independent of US1/US2 once US4 is complete

### Within Each User Story

- T004 (dotenv load) before T005 (key guard) — guard reads from env after load
- T008 (conftest) before T009 (test skeleton) before T010–T013 (test functions)
- T011 (helper) before T012 (assertion extension)

### Parallel Opportunities

- T006 (env.example) and T007 (unit tests) can run in parallel with T004/T005
- T014 (CI workflow) and T015 (README) can run in parallel

---

## Parallel Example: US5 (Foundational)

```bash
# After T004 is complete, these can run in parallel:
Task T006: "Create bureau/data/env.example"
Task T007: "Add unit tests in tests/unit/test_dotenv_loading.py"
```

---

## Implementation Strategy

### MVP First (US5 + US4 + US1)

1. Complete Phase 1: Setup (deps, e2e dir)
2. Complete Phase 2: US5 dotenv loading (T004–T007)
3. Complete Phase 3: US4 test infrastructure (T008–T009)
4. Complete Phase 4: US1 smoke test (T010)
5. **STOP and VALIDATE**: Run `pytest tests/e2e/ -k test_smoke_hello_world` against bureau-test
6. This is T027 from spec 002 — the first real E2E validation of bureau

### Incremental Delivery

1. Setup + US5 + US4 → dotenv works, test infra skips cleanly
2. Add US1 → smoke test passes → **T027 complete**
3. Add US2 → phase event assertions
4. Add US3 → escalation path tested
5. Add Polish → CI workflow, README

---

## Notes

- US5 is listed as a separate user story but functions as foundational infrastructure — treat it with Phase 2 urgency
- `test_smoke_hello_world` is a real API call (~2–5 min); run with `-s` to see live bureau output during development
- The xfail on `test_escalation_missing_artifact` is intentional — do not change to `strict=True` until bureau's escalation on missing artifacts is confirmed reliable
- E2E tests do NOT mock anything — if they're slow or expensive that is expected and correct
