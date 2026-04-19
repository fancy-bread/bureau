# Feature Specification: Bureau E2E Test Suite

**Feature Branch**: `004-e2e-test-suite`
**Created**: 2026-04-18
**Status**: Draft
**Input**: Replace the two skipped stub-era E2E tests with a real pytest suite that drives bureau against the `fancy-bread/bureau-test` target repo and asserts on structured stdout events. Includes isolated API key loading from `~/.bureau/.env` so bureau's Anthropic credentials are separate from Claude Code's Pro subscription auth.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Smoke Test: Bureau Completes a Happy-Path Run (Priority: P1)

A developer runs the E2E suite pointing at a local clone of `bureau-test`. Bureau runs against `specs/001-smoke-hello-world/spec.md`, completes without escalation, opens a PR, and the suite asserts `run.completed` appeared in stdout.

**Why this priority**: This is the foundational gate. If bureau cannot complete the simplest spec in bureau-test, all other E2E assertions are meaningless.

**Independent Test**: `pytest tests/e2e/ -k test_smoke_hello_world` passes when `BUREAU_TEST_REPO` points to a clean clone of `fancy-bread/bureau-test` with `ANTHROPIC_API_KEY` and `gh` auth in the environment.

**Acceptance Scenarios**:

1. **Given** a clean clone of `bureau-test` and valid env vars, **When** `bureau run specs/001-smoke-hello-world/spec.md --repo <clone>` is executed, **Then** stdout contains `[bureau] run.completed` and a PR URL, and the process exits 0
2. **Given** a completed run, **When** stdout is parsed for phase events, **Then** all six phases appear: `validate_spec`, `repo_analysis`, `planner`, `builder`, `critic`, `pr_create`
3. **Given** a completed run, **When** the PR is inspected via `gh pr view`, **Then** the PR body contains the run ID and at least one FR entry

---

### User Story 2 — All Phase Events Are Structured and Ordered (Priority: P1)

The suite captures bureau's stdout and asserts that every required phase event appears in the correct order with the correct format. This verifies the event contract independently of implementation correctness.

**Why this priority**: The event stream is bureau's external contract. A run that emits correctly structured events in order is a run that other tools (CI, dashboards, `bureau resume`) can rely on.

**Independent Test**: Parse the captured stdout line by line; assert each `phase.started`/`phase.completed` pair appears in dependency order before the next phase begins.

**Acceptance Scenarios**:

1. **Given** a completed bureau run, **When** stdout lines beginning with `[bureau]` are extracted, **Then** each `phase.started phase=X` is followed by `phase.completed phase=X` before any `phase.started phase=Y` where Y comes after X in the pipeline
2. **Given** a completed bureau run, **When** the `run.completed` line is parsed, **Then** it contains a `pr=<url>` field and a `duration=` field
3. **Given** a completed bureau run, **When** `ralph.attempt` events are parsed, **Then** each contains `round=`, `attempt=`, and `result=pass|fail` fields

---

### User Story 3 — Escalation Path: Bureau Escalates on Missing Artifact (Priority: P2)

The suite runs `specs/004-escalation-missing-schema/spec.md` against bureau-test and asserts that bureau emits a structured escalation and does NOT open a PR.

**Why this priority**: The escalation path is as important as the happy path. A bureau that never escalates is a bureau that guesses — which is a constitution violation.

**Independent Test**: `pytest tests/e2e/ -k test_escalation_missing_artifact` captures stdout and asserts `run.escalated` is present and no PR URL appears.

**Acceptance Scenarios**:

1. **Given** `specs/004-escalation-missing-schema/spec.md` and a bureau-test clone where `docs/report-schema.md` does not exist, **When** bureau is run, **Then** stdout contains `[bureau] run.escalated` before the process exits
2. **Given** a `run.escalated` event, **When** the escalation output is read, **Then** it contains `What happened`, `What's needed`, `Options`, and a `Resume:` command
3. **Given** a `run.escalated` event, **When** stdout is scanned for a PR URL, **Then** no URL matching `https://github.com/` appears

**Note**: If bureau's Planner completes the spec instead of escalating (spec 004 gap documented in harness assessment), this test is marked `xfail` with a note rather than causing the suite to fail hard.

---

### User Story 4 — Test Infrastructure: Suite Is Isolated and Repeatable (Priority: P1)

Each test run works against a fresh branch in bureau-test, leaving the repo in a clean state for the next run. The suite can be run repeatedly in CI without manual cleanup.

**Why this priority**: An E2E suite that leaves dangling branches or merged PRs pollutes future runs and makes failure diagnosis unreliable.

**Independent Test**: Run the suite twice in sequence against the same bureau-test clone; both runs produce distinct run IDs and distinct branch names with no conflicts.

**Acceptance Scenarios**:

1. **Given** a bureau-test clone, **When** the suite runs, **Then** each test checks out a clean branch derived from `main` before invoking bureau, and restores `main` after
2. **Given** a completed test, **When** the PR created by bureau is inspected, **Then** its branch name is unique per run (bureau generates run-ID-derived branch names)
3. **Given** suite configuration, **When** `BUREAU_TEST_REPO` env var is absent, **Then** the suite skips all E2E tests with a clear skip message rather than failing

---

### User Story 5 — API Key Isolation: Bureau Loads Its Own Credentials (Priority: P1)

A developer runs bureau alongside Claude Code in the same shell. Bureau's Anthropic API calls are billed to a separate Console account, not to the developer's Pro subscription. Bureau reads its API key from `~/.bureau/.env` so the two credential contexts never collide.

**Why this priority**: Without isolation, developers must export `ANTHROPIC_API_KEY` into their shell profile, which either overwrites Claude Code's auth or requires constant switching. This makes bureau unusable in a standard Claude Code development environment.

**Independent Test**: Start a shell where `ANTHROPIC_API_KEY` is NOT set. Place a valid key in `~/.bureau/.env`. Run `bureau run <spec> --repo <path>`. Bureau completes without error — the key was loaded from the file, not the environment.

**Acceptance Scenarios**:

1. **Given** `ANTHROPIC_API_KEY` is not in the shell environment and `~/.bureau/.env` contains `ANTHROPIC_API_KEY=sk-ant-...`, **When** any bureau command that calls the Anthropic API is run, **Then** the call succeeds using the key from the file
2. **Given** both `~/.bureau/.env` and the shell environment contain different values for `ANTHROPIC_API_KEY`, **When** bureau runs, **Then** the shell environment value takes precedence (env var wins over file)
3. **Given** neither `~/.bureau/.env` nor the shell environment contains `ANTHROPIC_API_KEY`, **When** bureau runs a persona node, **Then** bureau exits with a clear error message identifying the missing key — it does not emit an Anthropic SDK error traceback
4. **Given** `~/.bureau/.env` does not exist, **When** bureau starts, **Then** bureau starts normally and falls back to the shell environment (missing file is not an error)

---

### Edge Cases

- If `ANTHROPIC_API_KEY` is not set in either the shell or `~/.bureau/.env`, all E2E tests must skip (not fail) with a clear message identifying the missing credential.
- If `gh` CLI is not authenticated, the `run.completed` assertion may not apply — document expected failure mode.
- Bureau-test must be on `main` at the start of each test; the fixture must `git checkout main && git pull` before running.
- If a previous bureau run left a branch open (from an interrupted test), the fixture must not fail — it should log a warning and proceed from a fresh state.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An E2E test module MUST exist at `tests/e2e/test_bureau_e2e.py`
- **FR-002**: The suite MUST read the bureau-test repo path from the `BUREAU_TEST_REPO` environment variable; if absent all tests MUST skip via `pytest.mark.skipif`
- **FR-003**: The suite MUST skip all tests if `ANTHROPIC_API_KEY` is not resolvable (neither shell environment nor `~/.bureau/.env`)
- **FR-004**: Each test MUST reset bureau-test to `main` before running (`git checkout main`) and leave it on `main` after
- **FR-005**: A `run_bureau(spec_path, repo_path) -> subprocess.CompletedProcess` helper MUST capture stdout and stderr with a timeout of 600 seconds
- **FR-006**: `test_smoke_hello_world` MUST assert `run.completed` in stdout and exit code 0
- **FR-007**: `test_smoke_hello_world` MUST assert all six phase events appear in stdout in pipeline order
- **FR-008**: `test_smoke_hello_world` MUST assert at least one `ralph.attempt` event appears with `result=pass`
- **FR-009**: `test_escalation_missing_artifact` MUST assert `run.escalated` in stdout and no `https://github.com/` PR URL in stdout
- **FR-010**: `test_escalation_missing_artifact` MUST be marked `pytest.mark.xfail(strict=False, reason="Planner may complete instead of escalating")` to allow for spec 004 ambiguity
- **FR-011**: A `conftest.py` MUST provide a `bureau_test_repo` session-scoped fixture that validates the path and exposes it to all tests
- **FR-012**: The suite MUST NOT depend on any mock or patch — all Anthropic API calls and `gh` CLI calls are real
- **FR-013**: Bureau MUST load `~/.bureau/.env` at startup using `python-dotenv` (or equivalent), before any persona node instantiates an Anthropic client; shell environment variables MUST take precedence over file values
- **FR-014**: If `~/.bureau/.env` does not exist, bureau MUST start normally with no error or warning
- **FR-015**: If `ANTHROPIC_API_KEY` is not resolvable after loading `~/.bureau/.env`, bureau MUST exit with a human-readable error message (e.g. `"ANTHROPIC_API_KEY not set — add it to ~/.bureau/.env or export it in your shell"`) rather than propagating an Anthropic SDK exception
- **FR-016**: `python-dotenv` MUST be added to bureau's runtime dependencies in `pyproject.toml`
- **FR-017**: Bureau MUST ship a `bureau/data/env.example` file listing all supported environment variables with placeholder values and a one-line comment per var explaining its purpose; this file MUST be referenced in bureau's README as the canonical credential setup guide
- **FR-018**: The CI workflow (`.github/workflows/e2e.yml`) MUST read `ANTHROPIC_API_KEY` from a GitHub Actions secret and export it as an environment variable — no `.env` file is written in CI; the `~/.bureau/.env` mechanism is a local-dev convenience only

### Non-Functional Requirements

- Each individual E2E test has a timeout of 600 seconds (bureau's full run budget)
- The suite MUST be runnable with `pytest tests/e2e/ -v` with no additional flags beyond env vars

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `pytest tests/e2e/ -v` exits 0 (or with only `xfail` marks) when env vars are set
- **SC-002**: `pytest tests/e2e/ -v` exits 0 with all tests skipped when `BUREAU_TEST_REPO` is absent
- **SC-003**: `pytest tests/e2e/ -v` exits 0 with all tests skipped when `ANTHROPIC_API_KEY` is absent from both shell and `~/.bureau/.env`
- **SC-004**: The smoke test captures a `run.completed` event within 600 seconds
- **SC-005**: The escalation test captures a `run.escalated` event within 600 seconds

## Assumptions

- `bureau-test` is cloned locally before running the suite; the suite does not clone it
- `gh` CLI is installed and authenticated in the environment where the suite runs
- `ANTHROPIC_API_KEY` is set in either the shell environment or `~/.bureau/.env`; bureau loads the file automatically so it does not need to be in the shell profile
- Python 3.12+ is the test execution environment (matches bureau's own runtime)
- bureau is installed as a CLI in the active virtual environment (`pip install -e .`)
- bureau-test's `main` branch is the baseline; the suite does not merge PRs it creates
