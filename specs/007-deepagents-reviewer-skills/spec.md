# Feature Specification: deepagents Builder Integration, Critic Renamed to Reviewer, and Skills Vendoring

**Feature Branch**: `007-deepagents-reviewer-skills`
**Created**: 2026-04-21
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Builder Powered by deepagents (Priority: P1)

A developer submits a spec with tasks.md to bureau. The Builder phase uses deepagents under the hood to implement the tasks. The Builder has access to file operations, shell commands, and a library of named skills via the skills directory. The Builder's output (work done, errors encountered) is captured and handed back to the Reviewer for review.

**Why this priority**: The deepagents integration is the core architectural change in v2. It replaces the current hand-rolled 50-turn loop with a well-maintained library that provides file access, shell execution, skill discovery, context summarisation, and prompt caching out of the box. This is the highest-risk change and must land first.

**Independent Test**: Run `bureau run <spec-folder> --repo <path>` with a tasks.md that requires creating a file. Confirm the Builder completes without error and the file appears in the repo. Verify the run log contains at least one `ralph.attempt` event with `result=pass` or `result=fail`.

**Acceptance Scenarios**:

1. **Given** a clean spec folder with tasks.md and a target git repo, **When** bureau runs, **Then** the Builder phase starts, executes each task using deepagents, and produces a `BuildAttempt` record in the run state.
2. **Given** a build that fails all attempts, **When** the maximum retry limit is reached, **Then** bureau escalates with a structured `BuildAttempt` history rather than hanging or crashing.
3. **Given** tasks.md referencing skill names (e.g., `read_file`, `run_command`), **When** the Builder runs, **Then** skills are resolved from the skills directory and available to the agent without manual tool wiring.

---

### User Story 2 - Critic Renamed to Reviewer Throughout (Priority: P2)

Every reference to "Critic" in the codebase — node names, persona files, phase enum values, test identifiers, log output strings, and event keys — is renamed to "Reviewer". The Reviewer's behaviour is unchanged; only its name changes. Downstream tooling (log parsers, event consumers, test assertions) that currently match "critic" must be updated to match "reviewer".

**Why this priority**: The rename is a prerequisite for clear documentation alignment between the codebase and the pair-programmer framing (Builder = coder, Reviewer = reviewer). Doing it as a discrete, behaviour-free change makes it safe to land before or alongside the deepagents work. No logic changes required.

**Independent Test**: Run the full test suite after the rename. Grep the entire codebase for the word "critic" (case-insensitive). Zero matches remaining (excluding comments referencing prior terminology for historical context) signals completion.

**Acceptance Scenarios**:

1. **Given** the renamed codebase, **When** a bureau run completes, **Then** all emitted log lines and event keys use "reviewer" where they previously used "critic".
2. **Given** the renamed Phase enum, **When** a run reaches the review step, **Then** the phase is recorded as `Phase.REVIEWER` (or equivalent) in the checkpoint.
3. **Given** all test files updated, **When** the test suite runs, **Then** no test fails due to mismatched phase name or event key.

---

### User Story 3 - Vendored Default Skills Available to Builder (Priority: P3)

A curated set of SKILL.md files from the `addyosmani/agent-skills` open-source collection is copied into `bureau/skills/default/`. When the Builder starts, these skills are discoverable by the skills middleware without any per-run configuration. The developer does not need to author skills from scratch to get a functional Builder.

**Why this priority**: Skills extend what the Builder can do without code changes. Vendoring a baseline set ensures the Builder is immediately capable beyond bare file I/O. This is lower risk than the deepagents core integration and can ship alongside or after it.

**Independent Test**: After vendoring, start a bureau run and confirm the Builder's system prompt (or tool list) includes at least one skill sourced from the `bureau/skills/default/` directory. Alternatively, confirm the skills middleware loads from that path without error.

**Acceptance Scenarios**:

1. **Given** skills in `bureau/skills/default/`, **When** the Builder initialises, **Then** the skills are loaded and available as named tools without any additional configuration.
2. **Given** a task that requires running a shell command, **When** the Builder invokes the relevant skill, **Then** the command executes and output is returned to the agent.
3. **Given** a malformed or missing SKILL.md file in the directory, **When** the Builder initialises, **Then** bureau logs a warning for that skill and continues loading the remaining valid skills.

---

### User Story 4 - ASDLC Phase Skills Wired to Builder and Reviewer (Priority: P4)

The Builder agent is pre-configured with the `/build`, `/test`, and `/ship` skills from the ASDLC skill set, mapping to the BUILD → VERIFY → SHIP phases of the software delivery lifecycle. The Reviewer agent is pre-configured with the `/review` skill, covering the REVIEW gate. When bureau runs, each agent receives only the skills appropriate to its role — the Builder does not have access to review skills, and the Reviewer does not have access to build or ship skills.

**Why this priority**: Skill assignment defines what each agent is *allowed* to do, not just what it *can* do. Giving the Builder build/test/ship and the Reviewer review creates a clear separation of concerns that mirrors the ASDLC phase model. This enforces the pair-programmer contract at the capability level and prevents agents from drifting outside their lane.

**Independent Test**: Inspect the Builder's resolved skill list at startup and confirm it includes `build`, `test`, and `ship` but not `review`. Inspect the Reviewer's resolved skill list and confirm it includes `review` but not `build`, `test`, or `ship`. A bureau run that successfully implements tasks and passes review without either agent invoking out-of-role skills confirms the wiring.

**Acceptance Scenarios**:

1. **Given** bureau is configured with ASDLC default skills, **When** the Builder initialises, **Then** its skill set includes `build`, `test`, and `ship` and excludes `review`.
2. **Given** bureau is configured with ASDLC default skills, **When** the Reviewer initialises, **Then** its skill set includes `review` and excludes `build`, `test`, and `ship`.
3. **Given** a run that reaches the Reviewer phase, **When** the Reviewer invokes the `review` skill, **Then** it performs a structured quality-gate check against the constitution and the build output, and returns a pass or escalation decision.
4. **Given** a run where the Builder attempts to call a skill outside its assigned set, **When** the skills middleware receives the request, **Then** it rejects the call and logs a warning rather than executing it.

---

### Edge Cases

- What happens when deepagents raises an unhandled exception mid-task? Bureau should catch it, record it in the `BuildAttempt`, and retry up to the configured maximum.
- What happens when a Reviewer-phase event is emitted during a run that was checkpointed with the old "critic" phase name? Runs started before the rename cannot be resumed; the user must start a new run.
- What happens if deepagents version conflicts with existing LangGraph version? Dependency resolution fails at install time with a clear error; bureau does not start.
- What happens if a required ASDLC skill (`build`, `test`, `ship`, or `review`) is missing from `bureau/skills/default/`? Bureau escalates at initialisation time with a clear message identifying the missing skill rather than starting a run that will fail mid-way.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Builder phase MUST use deepagents as its execution engine, replacing the current hand-rolled inner loop and tool definitions.
- **FR-002**: The Builder MUST accept tasks from the `task_plan` in bureau's run state and execute them via the deepagents agent.
- **FR-003**: The Builder MUST translate deepagents output (completed messages, tool results) into a `BuildAttempt` record compatible with bureau's existing run state schema.
- **FR-004**: The Builder MUST wire at minimum a file-access skill set and a shell-execution skill set via the deepagents skills middleware.
- **FR-005**: The Builder MUST wire a memory middleware layer that sources context from the run's `plan_text` and any per-repo context files.
- **FR-006**: Every occurrence of "Critic" in node names, persona identifiers, phase enum values, event keys, log strings, and test assertions MUST be replaced with "Reviewer".
- **FR-007**: The Reviewer node's behaviour (constitution checking, build review, escalation logic) MUST remain unchanged by the rename.
- **FR-008**: ASDLC SKILL.md files compatible with the `addyosmani/agent-skills` format MUST be present in `bureau/skills/default/` and committed to the repository.
- **FR-009**: The skills middleware MUST be configured to discover skills from `bureau/skills/default/` at Builder initialisation time.
- **FR-010**: A malformed skill file MUST produce a logged warning and be skipped; it MUST NOT prevent other skills from loading.
- **FR-011**: The deepagents library MUST be added as a declared dependency of bureau with a minimum version constraint.
- **FR-012**: All existing integration and unit tests MUST pass after all three changes are applied.
- **FR-013**: The Builder agent MUST be initialised with the `build`, `test`, and `ship` ASDLC skills and MUST NOT have access to the `review` skill.
- **FR-014**: The Reviewer agent MUST be initialised with the `review` ASDLC skill and MUST NOT have access to the `build`, `test`, or `ship` skills.
- **FR-015**: Skill assignment per agent MUST be declarative and configurable (e.g., via a skills manifest or node configuration), not hard-coded inline.

### Key Entities

- **BuildAttempt**: A record of one Builder execution cycle — tasks attempted, tools used, outcome (pass/fail), and error details if applicable.
- **Skill**: A named capability definition (SKILL.md file) that the Builder can invoke at runtime; has a name, description, and invocation contract.
- **Phase**: An enum of bureau's execution phases; "CRITIC" renamed to "REVIEWER".
- **RunState**: Bureau's LangGraph state dict; extended to reference the deepagents agent instance indirectly via the state bridge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bureau run with a valid spec and tasks.md completes end-to-end (from `tasks_loader` through `reviewer` to `git_commit`) without regression, in the same wall-clock time range as the current implementation (±20%).
- **SC-002**: Zero occurrences of the string "critic" (case-insensitive) remain in production source files after the rename; test files may reference "critic" only in historical comments.
- **SC-003**: The four ASDLC skills (`build`, `test`, `ship`, `review`) are present in `bureau/skills/default/` on a fresh install with no additional configuration, and each is assigned to the correct agent on every run.
- **SC-004**: The full test suite (unit + integration) passes with no new failures introduced by any of the three changes.
- **SC-005**: deepagents context summarisation activates automatically when the Builder's message history exceeds the configured threshold, preventing token-limit errors on long-running tasks.

## Assumptions

- deepagents 0.5.3 or later is compatible with the LangGraph version currently used by bureau; any conflicts will be surfaced at dependency resolution time.
- The `addyosmani/agent-skills` SKILL.md format is compatible with deepagents' `SkillsMiddleware` `FilesystemBackend` discovery without modification.
- The Reviewer node (after rename) will continue to use the existing Anthropic SDK directly, not deepagents; deepagents is scoped to the Builder only.
- The ~30-line state bridge translating deepagents `AgentState` into `BuildAttempt` + `RunState` is sufficient; no deep schema changes to `RunState` are needed.
- `bureau/skills/default/` will be tracked in version control; skills are not downloaded at runtime.
- Existing checkpoint data using "critic" phase names is not migrated; only new runs use "reviewer".
- The `build`, `test`, `ship`, and `review` ASDLC skill names in `bureau/skills/default/` match the canonical names expected by the agent wiring configuration; no aliasing layer is needed.
