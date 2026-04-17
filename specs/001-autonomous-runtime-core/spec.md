# Feature Specification: Bureau CLI Foundation

**Feature Branch**: `001-autonomous-runtime-core`
**Created**: 2026-04-16
**Status**: Draft
**Input**: PRD.md, TDD.md, HLA.md — projects/software/bureau (Obsidian vault)

## Clarifications

### Session 2026-04-16

- Q: What does "lay the foundation" mean in terms of deliverable? → A: CLI + LangGraph scaffold with stub personas — graph wired up, SqliteSaver checkpointing working, stub persona nodes, run manager
- Q: Which graph nodes should be real implementations vs stubs? → A: Structural nodes real (`validate_spec`, `repo_analysis`, `escalate`); `planner`, `builder`, `critic`, `pr_create` are stubs
- Q: Should `bureau init` be in scope for this foundation feature? → A: Yes — scaffolds `.bureau/config.toml` in the target repo; makes the foundation end-to-end testable
- Q: How much of the Memory node should be built now? → A: Scaffold only — `Memory` class with `write`/`read`/`summary` interface wired into graph; rolling summary stub returning empty string
- Q: What is the acceptance bar for the foundation? → A: E2E stub run — `bureau run <spec> --repo <path>` completes the full graph with real validation/repo-analysis + stub personas emitting placeholder events; `bureau resume` works from checkpoint

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Run the Foundation End-to-End (Priority: P1)

A developer runs `bureau run <spec-file> --repo <path>` against a target repo that has a
`.bureau/config.toml`. Bureau validates the spec, reads the repo config, executes the
graph through stub Planner, Builder, and Critic nodes, and completes the run — emitting
structured events to the terminal at each phase transition. No PR is opened (stub); the
run completes with a summary of what would have been produced.

**Why this priority**: This is the definition of "done" for the foundation. If this works,
the architecture is validated and every subsequent feature (real personas, PR creation,
skill loading) has a working skeleton to build on.

**Independent Test**: Run `bureau run <spec-file> --repo <path>` where the spec is valid
and `.bureau/config.toml` exists. Verify structured events appear for each phase, the run
completes without error, and a run ID is assigned.

**Acceptance Scenarios**:

1. **Given** a valid spec file (no `[NEEDS CLARIFICATION]` markers, all required sections present) and a target repo with `.bureau/config.toml`, **When** `bureau run <spec-file> --repo <path>` is invoked, **Then** the graph executes all nodes in order and the run completes
2. **Given** a run in progress, **When** each phase node transitions, **Then** a structured event is printed to terminal (e.g., `[bureau] phase.started phase=planner`)
3. **Given** a spec with `[NEEDS CLARIFICATION]` markers in functional requirements, **When** `bureau run` is invoked, **Then** the run is rejected before graph execution with a clear error identifying the markers
4. **Given** a target repo missing `.bureau/config.toml`, **When** `bureau run` is invoked, **Then** the run fails immediately at repo analysis with a CONFIG_MISSING message and instructions to run `bureau init`

---

### User Story 2 — Resume an Interrupted Run (Priority: P2)

A developer's run is interrupted mid-graph (process killed, timeout). They run
`bureau resume <run-id>` and the graph continues from the last completed checkpoint
node — it does not restart from the beginning.

**Why this priority**: Resumability is a first-class architectural requirement. If checkpointing
is wired incorrectly in the foundation, every feature built on top of it will be affected.
Validating it now is cheaper than fixing it later.

**Independent Test**: Start a run, interrupt it mid-graph (e.g., after `validate_spec`
completes but before `repo_analysis`), then run `bureau resume <run-id>`. Verify execution
continues from `repo_analysis` and the run completes without replaying `validate_spec`.

**Acceptance Scenarios**:

1. **Given** a run that was interrupted after a node completed, **When** `bureau resume <run-id>` is invoked, **Then** the graph continues from the next node after the last checkpoint — not from the beginning
2. **Given** an unknown or malformed run ID, **When** `bureau resume <run-id>` is invoked, **Then** a clear error is returned identifying the run as not found

---

### User Story 3 — Scaffold a Target Repo with `bureau init` (Priority: P2)

A developer wants to make an existing repo bureau-runnable. They run `bureau init` from
within the repo (or with `--repo <path>`). Bureau creates `.bureau/config.toml` with
sensible defaults that they can edit before running bureau against it.

**Why this priority**: `repo_analysis` is a real node that fails immediately without
`.bureau/config.toml`. `bureau init` makes the foundation testable without requiring
the developer to manually author the config file.

**Independent Test**: Run `bureau init --repo <path>` in a directory without
`.bureau/config.toml`. Verify the file is created with all required fields populated
with defaults.

**Acceptance Scenarios**:

1. **Given** a target repo without `.bureau/config.toml`, **When** `bureau init --repo <path>` is run, **Then** `.bureau/config.toml` is created with `[runtime]` and `[bureau]` sections populated with defaults
2. **Given** a target repo that already has `.bureau/config.toml`, **When** `bureau init` is run, **Then** the existing file is not overwritten; a warning is shown instead

---

### Edge Cases

- Run interrupted between nodes (not within a node) — resume continues from the next node
- Run interrupted within a node — resume re-executes the interrupted node from the start (node-level atomicity; partial node output is not persisted)
- `bureau run` invoked while another run for the same spec is already in progress — second invocation is rejected with a clear message identifying the in-progress run ID
- Spec file path does not exist or is not readable — rejected immediately before graph execution
- `.bureau/config.toml` exists but is missing required fields — `repo_analysis` fails with a structured error identifying the missing fields

## Requirements *(mandatory)*

### Functional Requirements

**CLI Structure**

- **FR-001**: Bureau MUST provide a CLI with the following commands: `run`, `resume`, `list`, `show`, `abort`, `init`
- **FR-002**: `bureau run <spec-file>` MUST accept `--repo <path>` (target repository path) and `--config <path>` (operator config, defaults to `bureau.toml` in working directory)
- **FR-003**: `bureau resume <run-id>` MUST accept `--response "<text>"` for providing a response to a paused escalation
- **FR-004**: `bureau init` MUST accept `--repo <path>` to scaffold `.bureau/config.toml` in a target repo; MUST NOT overwrite an existing config

**Graph & Execution**

- **FR-005**: Bureau MUST wire a LangGraph graph with nodes in order: `validate_spec` → `repo_analysis` → `memory` → `planner` → `builder` → `critic` → `pr_create`; with `escalate` reachable from `validate_spec`, `planner`, and `critic`
- **FR-006**: Bureau MUST checkpoint run state after every node using persistent storage so that an interrupted run can be resumed
- **FR-007**: Bureau MUST emit a structured terminal event at each phase transition: `run.started`, `phase.started`, `phase.completed`, `run.escalated`, `run.completed`, `run.failed`
- **FR-008**: Each run MUST be assigned a unique run ID at start; all terminal events and log entries MUST reference this ID

**Real Nodes**

- **FR-009**: `validate_spec` MUST verify: all required sections present (User Scenarios, Requirements, Success Criteria), at least one P1 user story, all FRs numbered and non-empty, no `[NEEDS CLARIFICATION]` markers in functional requirements, `.bureau/config.toml` path is readable
- **FR-010**: `repo_analysis` MUST read `.bureau/config.toml` from the target repo, parse `[runtime]` and `[bureau]` sections, write a `RepoContext` to the Memory store, and fail immediately with CONFIG_MISSING if the file is absent or unparseable
- **FR-011**: `escalate` MUST print a structured escalation to terminal (run ID, phase, what happened, what is needed, options, resume command) and pause the graph

**Stub Nodes**

- **FR-012**: `planner`, `builder`, `critic`, and `pr_create` MUST be stub nodes that emit a `phase.started` and `phase.completed` event, write a placeholder output to memory, and pass to the next node — no LLM calls

**Memory**

- **FR-013**: Bureau MUST provide a `Memory` class with `write(key, value)`, `read(key)`, and `summary()` methods; `summary()` MUST return an empty string in this foundation release
- **FR-014**: The Memory store MUST be wired into the graph; all nodes (real and stub) MUST be able to read from and write to it within a run

**Configuration**

- **FR-015**: Bureau MUST load operator config from `bureau.toml` at run start; required fields: GitHub token source, model routing defaults, `max_retries`
- **FR-016**: `.bureau/config.toml` in the target repo MUST define `[runtime]` fields: `language`, `base_image`, `install_cmd`, `test_cmd`, `build_cmd`

### Key Entities

- **Run**: Top-level execution unit. Has a unique run ID, references a spec file and target repo, tracks current phase, accumulated decisions, and escalations. Persisted via checkpoint store.
- **Spec**: The parsed input contract read from the spec file. Contains user stories (with priorities), functional requirements, and success criteria. A spec with unresolved `[NEEDS CLARIFICATION]` markers in requirements is invalid and blocks execution.
- **RepoContext**: Derived from `.bureau/config.toml` in the target repo. Contains language, base image, and build/test/lint commands. Required — run fails immediately if absent.
- **Memory**: Shared scratchpad for a run. Keyed string store with a `summary()` method. In this foundation release, `summary()` returns empty string; full LLM-based rolling summary is deferred.
- **Escalation**: Structured record of a blocker surfaced to the operator. Contains run ID, phase, what was attempted, what is needed, and available options. Pauses the graph until the operator responds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `bureau run <spec-file> --repo <path>` on a valid spec with a valid `.bureau/config.toml` completes a full stub run and emits structured events for every phase without error
- **SC-002**: A run interrupted mid-graph resumes from the last completed node when `bureau resume <run-id>` is invoked — confirmed by observing that completed nodes do not re-execute
- **SC-003**: A spec containing `[NEEDS CLARIFICATION]` markers in functional requirements is rejected before any graph node executes
- **SC-004**: A target repo missing `.bureau/config.toml` causes `repo_analysis` to fail immediately with a CONFIG_MISSING message and `bureau init` instructions
- **SC-005**: `bureau init` produces a `.bureau/config.toml` with all required fields; running `bureau run` against that repo no longer fails at `repo_analysis`

## Assumptions

- This feature delivers the CLI foundation only; real Planner, Builder, and Critic LLM implementations are separate features built on top of this scaffold
- PR creation (real GitHub integration) is out of scope; `pr_create` is a stub in this feature
- The skill loading system is out of scope for the foundation; persona stubs do not invoke skills
- Docker Agent and containerized Builder execution are out of scope; the Builder stub runs on the host
- Memory rolling summary (LLM-based) is deferred; `Memory.summary()` returns empty string in this release
- Parallel runs are out of scope; a single run executes one spec at a time
- GitHub is the only supported git hosting provider; authentication is via the `gh` CLI on the host
- Docker daemon availability is not required for this foundation feature
- `bureau.toml` operator config must exist in the working directory when `bureau run` is invoked; bureau does not create it automatically
