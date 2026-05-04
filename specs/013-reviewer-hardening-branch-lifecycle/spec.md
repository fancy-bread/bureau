# Feature Specification: Reviewer Hardening and Branch Lifecycle

**Feature Branch**: `013-reviewer-hardening-branch-lifecycle`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "Reviewer hallucination guards, branch lifecycle prepare/complete split, and dotnet e2e infrastructure"

## User Scenarios & Testing

### User Story 1 — Reviewer Produces Only Valid Findings (Priority: P1)

A bureau operator runs a spec against a target repo. When the Reviewer evaluates the Builder's output, every finding references a functional requirement that actually exists in the spec. No spurious or hallucinated FR IDs block the run or cause phantom loops.

**Why this priority**: Hallucinated FR IDs are a show-stopper — they create unresolvable findings that loop until `RALPH_ROUNDS_EXCEEDED`, failing every run where the LLM invents a reference. This is the highest-risk correctness defect in the review pipeline.

**Independent Test**: Run bureau against a spec with FR-001 through FR-008. Intercept the Reviewer's LLM response and inject a finding with `ref_id="FR-099"`. Verify FR-099 does not appear in the final findings and the run concludes correctly.

**Acceptance Scenarios**:

1. **Given** the Reviewer LLM returns a finding with a `ref_id` that does not appear in the spec's FR list, **When** bureau processes the verdict, **Then** that finding is silently stripped and the verdict is recalculated from the remaining valid findings.
2. **Given** all LLM findings reference valid spec FRs, **When** bureau processes the verdict, **Then** no findings are stripped and the verdict is unchanged.
3. **Given** a finding has `type="constitution"`, **When** bureau processes the verdict, **Then** it is never stripped regardless of its `ref_id`.

---

### User Story 2 — Builder Escalation Is Never Overwritten by the Reviewer (Priority: P1)

When the Builder fails at a pre-flight step (e.g., `install_cmd` fails because the target directory does not yet exist), bureau escalates immediately. The Reviewer does not run and does not overwrite the escalation with a `revise` verdict.

**Why this priority**: The unconditional `builder → reviewer` edge in the pipeline means any builder-set escalation flows into the Reviewer by default. Without a pass-through guard, the Reviewer overwrites `_route: "escalate"` with `_route: "revise"`, masking the real failure and looping until round exhaustion.

**Independent Test**: Configure `install_cmd` to a command that will always fail. Run bureau. Verify `run.escalated` is emitted immediately with the builder's reason rather than looping through `max_rounds` reviewer rounds.

**Acceptance Scenarios**:

1. **Given** the Builder's `install_cmd` fails (non-zero exit), **When** state flows to the Reviewer node, **Then** the Reviewer detects the existing escalation, returns state unchanged, and the run routes to the escalate node.
2. **Given** the Builder completes normally, **When** state flows to the Reviewer node, **Then** the Reviewer runs its full evaluation as usual.

---

### User Story 3 — Feature Branch Opens Before Any Builder Work (Priority: P2)

When bureau picks up a spec, it creates the feature branch immediately after loading tasks — before the Builder writes a single file. All commits made by the Builder during execution land on the feature branch from the start, mirroring how a developer opens a branch before beginning work.

**Why this priority**: Without upfront branch creation, the Builder's phase-checkpoint commits land on whatever branch the target repo was on (typically `main`). The feature branch is then created after the fact by cutting from that HEAD — technically correct but semantically wrong and leaving main polluted locally.

**Independent Test**: Run bureau against a spec. After `tasks_loader` completes and before the Builder writes any file, inspect the target repo's current branch. Verify it is the feature branch, not `main`.

**Acceptance Scenarios**:

1. **Given** `tasks_loader` completes successfully, **When** bureau advances to the next node, **Then** the target repo has been switched to a new `feat/<spec-name>-<run-id>` branch.
2. **Given** the Builder makes incremental commits during a run, **When** the run completes, **Then** all commits appear on the feature branch, not on `main`.
3. **Given** a branch collision occurs (branch already exists), **When** bureau retries up to 3 times with a numeric suffix, **Then** it either finds a unique name and continues, or escalates with `GIT_BRANCH_EXISTS`.

---

### User Story 4 — Reviewer Activity Is Visible in Run Output (Priority: P2)

An operator watching a bureau run in real time can see what the Reviewer did — whether its independent pipeline passed, which FRs were evaluated, and what the verdict was — without waiting for the PR.

**Why this priority**: The Reviewer was previously a black box: a single `phase.completed verdict=pass` line with no indication of what was checked. Operators could not distinguish a thorough review from a rubber-stamp.

**Independent Test**: Run bureau against a passing spec. Verify `reviewer.pipeline` and `reviewer.verdict` events appear in stdout between `ralph.attempt result=pass` and `phase.completed phase=reviewer`.

**Acceptance Scenarios**:

1. **Given** the Reviewer's independent pipeline runs, **When** all phases pass, **Then** a `reviewer.pipeline` event is emitted with `passed=true` and the list of phases run.
2. **Given** the Reviewer's independent pipeline fails at a phase, **When** the failure is detected, **Then** a `reviewer.pipeline` event is emitted with `passed=false` and `failed_phase` identifying the failing phase.
3. **Given** the Reviewer's LLM evaluation completes, **When** a verdict is produced, **Then** a `reviewer.verdict` event is emitted containing the verdict, round, summary, and per-FR finding list.

---

### User Story 5 — Dotnet Repos Can Be Tested End-to-End (Priority: P3)

A bureau developer can trigger an end-to-end run against a .NET target repo from the command line locally or via a dedicated GitHub Actions workflow, with the same structure as the existing Python and TypeScript e2e tests.

**Why this priority**: Dotnet is the third supported language. Without e2e infrastructure, dotnet support is unverified in CI and untestable locally without manual steps.

**Independent Test**: Run `make test-kafka-smoke-dotnet` with a running Kafka instance and `BUREAU_TEST_REPO_DOTNET` set. Verify a PR is created in `bureau-test-dotnet`.

**Acceptance Scenarios**:

1. **Given** `BUREAU_TEST_REPO_DOTNET` is set and Kafka is running, **When** `make test-kafka-smoke-dotnet` is executed, **Then** bureau runs against the dotnet spec and produces a PR or escalates with a structured reason.
2. **Given** `BUREAU_TEST_REPO_DOTNET` is not set, **When** `pytest tests/e2e/test_bureau_e2e_dotnet.py` is run, **Then** all dotnet tests are skipped with `BUREAU_TEST_REPO_DOTNET not set`.
3. **Given** the `e2e-dotnet.yml` workflow is dispatched, **When** the job runs, **Then** it checks out `bureau-test-dotnet`, sets up the .NET SDK, and runs the dotnet e2e test file exclusively.

---

### Edge Cases

- What happens when the Reviewer LLM returns only hallucinated FR IDs and no valid findings remain after stripping? (Verdict recalculates to `pass` if no unmet findings survive.)
- What happens when `install_cmd` is empty and the builder fails during implementation? (Pass-through guard only fires when `_route: "escalate"` is already set with escalations present; normal builder failure routes normally.)
- What happens when a branch name collision persists across all 3 retry attempts? (Escalates with `GIT_BRANCH_EXISTS`.)
- What if the target repo has uncommitted changes when `prepare_branch` runs? (Bureau does not check for dirty state at branch creation; dirty repo detection is a separate gate.)

## Requirements

### Functional Requirements

- **FR-001**: The Reviewer MUST strip any LLM finding whose `ref_id` matches `FR-\d+` but does not appear in the spec's functional requirements list, before applying routing logic.
- **FR-002**: After stripping invalid findings, the Reviewer MUST recalculate the overall verdict (`pass` / `revise` / `escalate`) from the surviving findings.
- **FR-003**: Constitution findings (`type="constitution"`) MUST never be stripped regardless of their `ref_id`.
- **FR-004**: If the Builder has already set `_route: "escalate"` with at least one escalation, the Reviewer node MUST return state unchanged without running any evaluation.
- **FR-005**: Internal Reviewer findings (pipeline failure, missing files, test quality) MUST use `type="pipeline"` with non-FR ref_ids (`PIPELINE`, `FILES-MISSING`, `TEST-QUALITY`) that cannot collide with spec FR IDs.
- **FR-006**: A `prepare_branch` node MUST execute between `tasks_loader` and `builder`, creating the feature branch before any builder work begins.
- **FR-007**: The feature branch name MUST follow the pattern `feat/<spec-name>-<run-id-prefix>` and be stored in state as `branch_name`.
- **FR-008**: The `complete_branch` node (formerly `git_commit`) MUST read `branch_name` from state rather than creating the branch itself.
- **FR-009**: A `reviewer.pipeline` event MUST be emitted after the Reviewer's independent pipeline runs, carrying `passed`, `phases`, and `failed_phase` fields.
- **FR-010**: A `reviewer.verdict` event MUST be emitted after the Reviewer produces a verdict, carrying `verdict`, `round`, `summary`, and a `findings` list with `ref_id`, `verdict`, and `type` per finding.
- **FR-011**: A dotnet e2e test file, conftest fixture, Makefile target, and GitHub Actions workflow MUST exist with the same structural pattern as the Python and TypeScript equivalents.
- **FR-012**: The dotnet e2e workflow MUST install the .NET SDK and run only `test_bureau_e2e_dotnet.py`, with a 60-minute job timeout.

### Key Entities

- **Reviewer Finding**: A structured evaluation result. Key attributes: `type` (`requirement` | `constitution` | `pipeline`), `ref_id` (spec FR ID or internal sentinel), `verdict` (`met` | `unmet` | `violation`), `detail`, `remediation`.
- **Reviewer Verdict**: The aggregate output of a Reviewer evaluation. Key attributes: `verdict` (`pass` | `revise` | `escalate`), `findings` list, `summary`, `round`.
- **Feature Branch**: The git branch created for a bureau run. Pattern: `feat/<spec-name>-<run-id-prefix>`. Created by `prepare_branch`, pushed by `complete_branch`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A run against a spec with FR-001–FR-008 where the LLM returns a hallucinated FR-009 finding completes without escalating on FR-009.
- **SC-002**: A run where `install_cmd` fails escalates in round 0 without consuming any reviewer rounds.
- **SC-003**: After `tasks_loader` completes, the target repo is on a `feat/` branch before the first builder tool call.
- **SC-004**: Every bureau run output includes at least one `reviewer.pipeline` event and one `reviewer.verdict` event when the Reviewer executes.
- **SC-005**: The dotnet e2e test runs end-to-end and produces a PR against `bureau-test-dotnet` within the 60-minute workflow timeout.
- **SC-006**: All unit and integration tests pass with the new node names and guards in place.

## Assumptions

- The speckit constitution path convention (`.specify/memory/constitution.md`) is in place; no `constitution` field is needed in `.bureau/config.toml`.
- `planner_model` has been removed from `BureauConfig` and `RepoContext`; only `builder_model` and `reviewer_model` are configurable.
- The `bureau-test-dotnet` repo has a pre-seeded solution scaffold (`src/`) so that `install_cmd = "dotnet restore src/"` succeeds at run start; greenfield (scaffold-from-scratch) scenarios require empty `install_cmd`.
- The dotnet SDK version in use is .NET 10; the base image is `mcr.microsoft.com/dotnet/sdk:10`.
- Phase names `prepare_branch` and `complete_branch` replace `git_branch` and `git_commit` throughout state, events, and tests.
