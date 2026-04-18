# Bureau Personas and PR Creation

**Feature Branch**: `002-personas-pr-creation`
**Created**: 2026-04-18
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Planner produces a verified task plan (Priority: P1)

A developer hands bureau an approved spec for a target repo. Bureau's Planner persona reads the spec, analyses the codebase, and produces a dependency-ordered task plan. The plan is verified to be internally consistent with the spec's functional requirements and stored so the Builder can consume it.

**Why this priority**: The Planner is the first real persona in the pipeline and its output gates everything downstream. Without a working Planner there is no Builder, no Critic, and no PR.

**Independent Test**: Given a valid spec and a target repo with a working `.bureau/config.toml`, running bureau through the planner phase produces a structured task plan persisted in the run's memory. The plan references at least one functional requirement from the spec and can be inspected via `bureau show <run-id>`.

**Acceptance Scenarios**:

1. **Given** a valid spec with P1 user stories and functional requirements, **When** the Planner runs, **Then** a task plan is written to run memory containing tasks mapped to functional requirements, and `phase.completed phase=planner` is emitted.
2. **Given** a spec with requirements the Planner cannot resolve against the codebase, **When** the Planner detects an unresolvable ambiguity, **Then** bureau emits a structured escalation with the specific blocker and pauses.
3. **Given** the Planner completes successfully, **When** the Builder phase begins, **Then** the task plan is available to the Builder from run memory.

---

### User Story 2 - Builder implements the plan iteratively until tests pass (Priority: P1)

Bureau's Builder persona reads the Planner's task plan, makes code changes to the target repo, and runs the repo's configured test command. If tests fail, the Builder revises and retries. This inner loop is the Ralph Loop: treat failure as feedback, iterate until external verification (the test suite) passes. When tests pass the Builder marks the phase complete.

**Why this priority**: The Builder is bureau's core value delivery — without it the runtime cannot produce a PR.

**Independent Test**: Given a target repo with a passing test suite and a task plan from the Planner, running bureau through the builder phase results in code changes committed to the feature branch and a passing test run, confirmed by `phase.completed phase=builder` in stdout.

**Acceptance Scenarios**:

1. **Given** a task plan and a target repo, **When** the Builder runs, **Then** it applies changes, runs the configured `test_cmd`, and emits `phase.completed phase=builder` when tests pass.
2. **Given** tests fail after an initial implementation, **When** the Builder detects a failure, **Then** it treats the test output as feedback, revises the implementation, and retries — up to 3 attempts per Ralph Loop round.
3. **Given** the Builder exhausts its retry limit without a passing test run, **When** the retry limit is reached, **Then** bureau emits a structured escalation identifying the failing tests and the last attempted fix.
4. **Given** a `build_cmd` is configured in the repo's config, **When** the Builder runs, **Then** the build step executes before tests.

---

### User Story 3 - Critic audits and approves or blocks the implementation (Priority: P1)

Bureau's Critic persona reviews the Builder's output against the spec's functional requirements, success criteria, and the project constitution. The Critic issues one of three verdicts: `pass` (advance to PR creation), `revise` (return to Builder with specific findings), or `escalate` (constitution violation or unresolvable gap). The Builder-Critic cycle is the outer Ralph Loop: the Critic acts as the architectural judge, the Builder as the generator.

**Why this priority**: The Critic is the verification gate that ensures bureau never opens a PR with non-compliant or incomplete work. It is what makes bureau trustworthy.

**Independent Test**: Given a completed builder output, running bureau through the critic phase produces a structured verdict (`pass` or `revise`) with findings. A `pass` verdict advances to PR creation; a `revise` verdict returns to the Builder with specific remediation instructions.

**Acceptance Scenarios**:

1. **Given** a builder output that satisfies all functional requirements and passes constitution checks, **When** the Critic runs, **Then** it emits `phase.completed phase=critic verdict=pass` and the run advances to PR creation.
2. **Given** a builder output with gaps against the spec's functional requirements, **When** the Critic runs, **Then** it issues a `revise` verdict with specific findings identifying which requirements are unmet and what the Builder must address.
3. **Given** a builder output with a constitution violation, **When** the Critic detects it, **Then** it escalates rather than issuing `revise` — constitution violations are CRITICAL and block PR creation.
4. **Given** the Critic issues a `revise` verdict, **When** the Builder completes a revision, **Then** the Critic re-audits the new output.
5. **Given** the Ralph Loop (Builder + Critic) exceeds 3 rounds, **When** the round limit is reached, **Then** bureau escalates with a structured summary of unresolved findings.

---

### User Story 4 - PR creation opens a pull request with a run summary (Priority: P2)

After the Critic passes the implementation, bureau opens a pull request on the target repo containing the implementation changes and a structured run summary. The run summary documents decisions made, constitution findings, Ralph Loop rounds completed, and the Critic's verdict.

**Why this priority**: PR creation is the terminal output of bureau — the artifact the developer reviews. It is P2 only because a passing Critic already validates completeness; the PR wrapping is delivery.

**Independent Test**: Given a passed Critic verdict and a target repo with a configured GitHub remote, running bureau through the pr_create phase results in an open pull request with a description containing the run ID, spec name, and a summary of Critic findings.

**Acceptance Scenarios**:

1. **Given** a passed Critic verdict, **When** the PR creator runs, **Then** it opens a pull request on the target repo's configured remote and emits `run.completed pr=<url>`.
2. **Given** a PR is created, **Then** the PR description includes: run ID, spec name, list of functional requirements addressed, Critic verdict and key findings, Ralph Loop rounds taken, and a link to the spec.
3. **Given** the target repo has no configured remote or authentication fails, **When** the PR creator attempts to open a PR, **Then** bureau escalates with a clear message identifying the remote configuration issue.

---

### Edge Cases

- What happens when the target repo's test command exits non-zero for reasons unrelated to the Builder's changes (pre-existing failures)?
- How does the system handle a spec with no codebase to build against (empty repo)?
- What happens when the Planner produces a task plan but the Builder determines the plan is unexecutable against the actual codebase?
- How does the constitution check behave when no project-specific constitution exists in the target repo?
- What happens when the configured `install_cmd` fails in the Builder environment?

## Requirements

### Functional Requirements

- **FR-001**: The Planner MUST read the spec's functional requirements and user stories from run memory and produce a dependency-ordered task plan.
- **FR-002**: The Planner MUST map each task in the plan to one or more functional requirements from the spec.
- **FR-003**: The Planner MUST write the task plan to run memory so downstream phases can consume it.
- **FR-004**: The Planner MUST escalate with a structured reason if it cannot produce a plan that covers all P1 functional requirements.
- **FR-005**: The Builder MUST read the task plan from run memory and apply code changes to the target repo.
- **FR-006**: The Builder MUST execute the repo's configured `test_cmd` after each implementation attempt and treat a non-zero exit as feedback for the next Ralph Loop iteration.
- **FR-007**: The Builder MUST retry failed implementations up to 3 attempts per Ralph Loop round; exceeding this triggers escalation.
- **FR-008**: The Builder MUST execute the repo's configured `build_cmd` before tests when the field is non-empty.
- **FR-009**: The Builder MUST write a summary of changes made to run memory for the Critic to consume.
- **FR-010**: The Critic MUST compare the Builder's output against every P1 functional requirement in the spec and produce a finding for each.
- **FR-011**: The Critic MUST check the implementation against the bureau constitution (project-level if present, otherwise bureau's default constitution).
- **FR-012**: The Critic MUST return a verdict of `pass`, `revise`, or `escalate`.
- **FR-013**: The Critic MUST issue a `revise` verdict with specific, actionable findings when requirements are unmet.
- **FR-014**: The Critic MUST escalate (not `revise`) when a constitution violation is detected.
- **FR-015**: The Critic MUST write its findings and verdict to run memory.
- **FR-016**: The Ralph Loop (Builder + Critic rounds) MUST be bounded at 3 rounds by default, configurable via `bureau.toml`; exceeding the limit triggers escalation.
- **FR-017**: The PR creator MUST open a pull request on the target repo's remote after a Critic `pass` verdict.
- **FR-018**: The PR creator MUST include a structured run summary in the PR description: run ID, spec name, functional requirements addressed, Critic verdict, Ralph Loop rounds taken, and a link to the spec file.
- **FR-019**: The PR creator MUST emit `run.completed pr=<url>` on success.
- **FR-020**: The PR creator MUST escalate with a clear message if the remote is not configured or PR creation fails.

### Key Entities

- **TaskPlan**: The Planner's output — an ordered list of tasks, each mapped to one or more functional requirement IDs, with dependency relationships.
- **BuildAttempt**: A record of a single Builder iteration within a Ralph Loop round — changes applied, test command output, pass/fail result.
- **RalphRound**: One complete Builder-Critic cycle — up to 3 Builder attempts followed by a Critic audit.
- **CriticFinding**: A structured finding from the Critic — requirement ID, verdict (`met` / `unmet` / `violation`), and remediation instruction if unmet.
- **CriticVerdict**: The Critic's overall decision — `pass`, `revise`, or `escalate` — with the full set of findings.
- **RunSummary**: The artifact attached to the PR — distilled from run memory, covering the full pipeline execution including Ralph Loop rounds.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Given a well-formed spec and a target repo, bureau completes the full pipeline (Planner → Builder → Critic → PR) without human intervention in the happy path.
- **SC-002**: The Critic correctly identifies at least 90% of functional requirement gaps when tested against a set of intentionally incomplete implementations.
- **SC-003**: The Builder successfully reaches a passing test run within 3 Ralph Loop iterations for tasks that require only additive changes to an existing passing test suite.
- **SC-004**: The PR description produced by bureau contains all required fields (run ID, spec name, requirements addressed, Critic verdict, Ralph Loop rounds) in 100% of successful runs.
- **SC-005**: When bureau escalates from any persona phase, the escalation message identifies the specific blocker in plain language with at least one actionable resolution option.

## Assumptions

- The target repo's `test_cmd` is reliable — pre-existing test failures before bureau runs are out of scope; bureau is not responsible for fixing a broken baseline.
- The target repo has a configured GitHub remote accessible by the environment's `gh` CLI or equivalent; PR creation uses the same authentication available to the shell.
- Bureau's default constitution applies when no project-specific constitution is found at `.bureau/constitution.md` in the target repo.
- The Builder operates on a feature branch created by bureau during the run; it does not modify the repo's default branch directly.
- Ralph Loop defaults: 3 Builder retries per round, 3 Builder-Critic rounds maximum — both configurable via `bureau.toml`.
- Persona implementations use the Anthropic API; valid credentials are available in the environment.
