# Feature Specification: Builder Git Workflow

**Feature Branch**: `005-builder-git-workflow`
**Created**: 2026-04-19
**Status**: Draft
**Input**: User description: "Implement git workflow in bureau's Builder and PR creation phases — the Builder currently writes files to the target repo but never creates a branch, stages, commits, or pushes. Before pr_create calls `gh pr create`, bureau must: create a feature branch named from the run ID, stage all changes, commit with a structured message, and push to the remote. The branch name and commit message should reference the spec name and run ID for traceability."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bureau completes a run and opens a real PR (Priority: P1)

A developer runs bureau against a spec. Bureau produces a working implementation in the target repo, commits it to a new branch with a traceable message, pushes the branch, and opens a pull request. The developer receives a PR URL in their terminal and can immediately review and merge.

**Why this priority**: Without branch creation, commit, and push, `gh pr create` has nothing to work from — no PR is opened regardless of how well the Builder performed. This is the blocking gap that prevents any successful bureau run from completing.

**Independent Test**: Run bureau against `specs/001-smoke-hello-world/spec.md` in bureau-test. Assert exit code 0, a GitHub PR URL in stdout, and that the PR exists in the bureau-test repo with a branch named after the run ID.

**Acceptance Scenarios**:

1. **Given** a target repo with no uncommitted changes on `main`, **When** bureau completes a successful build, **Then** a new branch named `feat/<spec-name>-<run-id-prefix>` exists in the remote repo, contains the Builder's changes, and a PR is open against `main`
2. **Given** a successful run, **When** the PR is opened, **Then** the commit message references the spec name and run ID
3. **Given** a successful run, **When** the developer views the PR, **Then** the PR title matches the spec name and the body contains the bureau run summary

---

### User Story 2 - Git failure escalates cleanly (Priority: P2)

Bureau attempts to create a branch or push but the operation fails — remote unreachable, insufficient permissions, branch already exists. Rather than silently producing no PR, bureau escalates with a clear message explaining what failed and what the developer needs to do.

**Why this priority**: Silent failure is worse than a failed run. The developer must know whether implementation succeeded and only git failed, so they can manually push if needed.

**Independent Test**: Run bureau against a repo with no git remote configured. Assert `run.escalated` in stdout with a message that identifies the git operation that failed.

**Acceptance Scenarios**:

1. **Given** a target repo with no remote configured, **When** bureau attempts to push, **Then** bureau escalates with `GIT_PUSH_FAILED` and the escalation message names the missing remote
2. **Given** a branch name collision (branch already exists in remote), **When** bureau attempts to create the branch, **Then** bureau uses a unique branch name (appending attempt counter) or escalates if retries are exhausted
3. **Given** a git failure after a successful build, **When** the escalation fires, **Then** the escalation message includes the implementation output location so the developer can recover manually

---

### Edge Cases

- What happens if the target repo has uncommitted changes before bureau starts? Bureau must not clobber existing work — it escalates with `DIRTY_REPO` and tells the developer to stash or discard before rerunning.
- What if the branch already exists remotely from a previous aborted run? Bureau generates a unique name (e.g., `feat/<spec-name>-<run-id-prefix>-2`) rather than failing.
- What if `git push` succeeds but `gh pr create` fails? The escalation must distinguish between git success and PR creation failure so the developer knows the branch is already pushed.
- What if the target repo has no commits (empty repo)? Bureau must handle this gracefully — either fail fast with a clear error or create an initial commit.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bureau MUST create a new branch in the target repo before any changes are committed; the branch name MUST follow the pattern `feat/<spec-name>-<run-id-prefix>` where `spec-name` is the kebab-case spec name and `run-id-prefix` is the first 8 characters of the run ID after stripping the `run-` prefix
- **FR-002**: Bureau MUST stage all changes produced by the Builder before committing
- **FR-003**: Bureau MUST create a commit with a structured message that includes the spec name and run ID; format: `feat: <spec-name> [bureau/<run-id-prefix>]`
- **FR-004**: Bureau MUST push the branch to the configured remote before calling `gh pr create`
- **FR-005**: The PR title MUST match the spec name
- **FR-006**: Bureau MUST emit a structured escalation if any git operation fails (branch create, stage, commit, push), identifying which operation failed
- **FR-007**: Bureau MUST NOT modify `main` or any existing branch — all changes go to the new bureau branch
- **FR-008**: Bureau MUST check for uncommitted changes in the target repo before starting; if found, bureau MUST escalate with `DIRTY_REPO` rather than proceeding
- **FR-009**: If a branch with the target name already exists, bureau MUST generate a unique alternative (e.g., `feat/<spec-name>-<run-id-prefix>-2`, `-3`) up to 3 attempts before escalating

### Key Entities

- **Bureau Branch**: The feature branch created per run; named `feat/<spec-name>-<run-id-prefix>`; scoped to a single run; deleted after PR merge is out of scope
- **Run Commit**: The single commit produced by a bureau run; contains all Builder output; message references spec name and run ID
- **Git Operation Result**: Success/failure state of each git step (branch, stage, commit, push); used to produce structured escalations

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bureau run that completes successfully always produces a PR URL in stdout — 100% of successful runs result in an openable PR
- **SC-002**: The PR branch is traceable to its run — given a PR, a developer can identify the run ID and spec within 10 seconds by reading the branch name or commit message
- **SC-003**: Git failures produce actionable escalations — a developer can identify what failed and recover (manually push, fix permissions) without reading bureau source code
- **SC-004**: Bureau never corrupts the target repo's `main` branch — zero incidents of bureau commits landing on `main`

## Assumptions

- The target repo has at least one commit on `main` (not an empty repo); empty repo support is out of scope
- The target repo has a configured git remote named `origin`
- The `gh` CLI is authenticated and has push access to the remote repo
- Bureau runs one build per run — there is one branch and one commit per successful run; multi-commit builds are out of scope
- The remote is GitHub; other git hosts are out of scope for this feature
