# Feature Specification: Command Pipeline Formalization and Reviewer Depth

**Feature Branch**: `012-pipeline-reviewer-depth`
**Created**: 2026-04-26
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Builder Runs Full Pipeline as Sequential Gates (Priority: P1)

A developer has configured `lint_cmd` and `build_cmd` in `.bureau/config.toml`. When bureau runs, the builder executes all four command phases in order — prepare, lint, build, test — before each attempt. If lint fails, the builder reports which phase failed and escalates rather than proceeding to a broken build or test run.

**Why this priority**: The pipeline gates exist in the config today but are silently ignored. A lint failure that would be caught immediately is instead masked by a test run that may pass on broken code. Enforcing the full sequence closes this gap and makes build failures actionable.

**Independent Test**: Configure a repo with a `lint_cmd` that fails. Run bureau. Verify the run escalates with the lint phase named as the failure point and no test run is attempted.

**Acceptance Scenarios**:

1. **Given** a repo with `lint_cmd = "ruff check ."` and a linting violation, **When** bureau runs, **Then** the builder stops at the lint gate, reports which phase failed, and does not run the test suite
2. **Given** a repo with `build_cmd = "tsc --noEmit"` and a type error, **When** bureau runs, **Then** the builder stops at the build gate and escalates with the build phase identified
3. **Given** a repo where all four phases pass, **When** bureau runs, **Then** the full pipeline completes in order and the attempt is recorded as passing
4. **Given** `lint_cmd` and `build_cmd` are empty strings, **When** bureau runs, **Then** those phases are skipped and the pipeline proceeds with prepare → test only

---

### User Story 2 — Reviewer Independently Re-Executes the Pipeline (Priority: P1)

After the builder reports success, the reviewer independently re-runs the full command pipeline against the repo — it does not trust the builder's reported test output. If the reviewer's independent run produces a different result than the builder reported, the reviewer issues a revise or escalate verdict.

**Why this priority**: The false positive root cause: the reviewer trusted the builder's self-report. A trivially-passing test suite (no assertions, no imports) will report exit code 0 — the builder passes it on, the reviewer passes it through. Independent execution by the reviewer closes this verification gap entirely.

**Independent Test**: A builder that reports "6 passed" on trivial tests will fail the reviewer's independent pipeline run — the reviewer's re-execution of the test suite will either fail (if tests assert anything meaningful against missing code) or succeed but the reviewer's code review will catch the trivial tests.

**Acceptance Scenarios**:

1. **Given** the builder reports tests passing, **When** the reviewer runs, **Then** the reviewer independently executes `test_cmd` and bases its verdict on that output — not the builder's report
2. **Given** the reviewer's independent pipeline run exits non-zero on any phase, **Then** the reviewer issues a `revise` verdict with the failing phase and output identified
3. **Given** `lint_cmd` is configured, **When** the reviewer runs, **Then** it executes lint as the first gate before running tests

---

### User Story 3 — Reviewer Reads Actual Files and Applies Test Quality Gate (Priority: P2)

The reviewer reads the actual implementation and test files written by the builder (via the memory scratchpad) and performs a code review on their contents. It applies a test quality gate: test files must import the module under test, call functions, and contain assertions — a test file consisting only of `pass` bodies is an automatic revise verdict.

**Why this priority**: Independent pipeline execution catches many false positives, but a builder that writes tests which pass trivially while importing and calling the right module could still slip through. Reading actual file contents allows the reviewer to evaluate whether the tests are meaningful and whether the implementation matches the spec's functional requirements.

**Independent Test**: Provide a builder output where `test_greeting.py` contains only `def test_greet(): pass`. Verify the reviewer issues `revise` with a finding identifying the test as non-asserting.

**Acceptance Scenarios**:

1. **Given** the builder wrote `tests/test_foo.py` containing only `def test_foo(): pass`, **When** the reviewer evaluates it, **Then** the reviewer issues `revise` with a finding identifying the test as non-asserting
2. **Given** the builder wrote a test file with `import foo` and `assert foo.bar() == expected`, **When** the reviewer evaluates it, **Then** the test quality gate passes
3. **Given** the builder's changed files include `src/foo.py`, **When** the reviewer evaluates, **Then** it reads the file contents and checks the implementation against each functional requirement in the spec
4. **Given** a functional requirement is unmet by the implementation (the file does not implement the required behaviour), **When** the reviewer evaluates, **Then** it issues `revise` with the specific FR and gap identified

---

### Edge Cases

- What if `build_cmd` succeeds but produces a binary that `test_cmd` cannot find? The test gate reports failure; the builder escalates normally.
- What if the memory scratchpad contains no `files_changed`? The reviewer skips file reading and issues `revise` with a finding that no files were changed.
- What if a changed file has been deleted before the reviewer reads it? The reviewer notes the missing file as a finding and continues with available files.
- What if `lint_cmd` exits non-zero on pre-existing violations unrelated to the builder's changes? The lint gate still fails — the repo must be in a lint-clean state for bureau to proceed. This is a known constraint documented in assumptions.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The builder MUST execute command phases in strict order: prepare (`install_cmd`) → lint (`lint_cmd`) → build (`build_cmd`) → test (`test_cmd`)
- **FR-002**: The builder MUST skip any phase whose configured command is an empty string
- **FR-003**: The builder MUST stop at the first failing phase and NOT proceed to subsequent phases
- **FR-004**: The builder's escalation MUST identify which pipeline phase failed and include the command output from that phase
- **FR-005**: The reviewer MUST independently execute the full pipeline (prepare → lint → build → test, skipping empty phases) without relying on the builder's reported output
- **FR-006**: The reviewer MUST read the contents of all files listed in the builder's `files_changed` from the memory scratchpad
- **FR-007**: The reviewer MUST apply a test quality gate: any test file that contains no assertions (`assert` statements or assertion method calls) MUST result in a `revise` verdict with a finding identifying the non-asserting test
- **FR-008**: The reviewer MUST evaluate each functional requirement in the spec against the actual implementation file contents and record a finding (met/unmet) for each
- **FR-009**: The reviewer's pipeline execution failure on any phase MUST result in a `revise` verdict with the failing phase and output identified in findings
- **FR-010**: `lint_cmd` and `build_cmd` in `.bureau/config.toml` MUST be treated as active pipeline gates by both the builder and reviewer when non-empty

### Key Entities

- **Pipeline Phase**: One of four ordered steps (prepare, lint, build, test); each has a configured command and a pass/fail result
- **Pipeline Result**: Outcome of executing all phases in sequence; includes which phase failed (if any) and its output
- **Test Quality Finding**: A reviewer finding that identifies a specific test file or function as non-asserting, with remediation guidance

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A repo with a failing lint step produces a bureau escalation identifying the lint phase — 100% of runs, no false negatives
- **SC-002**: A builder that reports passing tests on trivially-asserting test files is caught and reversed by the reviewer — false positive rate from trivial tests drops to 0%
- **SC-003**: The reviewer's independent pipeline execution adds no more than 60 seconds to total run time for a repo with a sub-30-second test suite
- **SC-004**: Every functional requirement in the spec has a corresponding reviewer finding (met or unmet) in the run summary — 100% FR coverage in findings
- **SC-005**: Runs where `lint_cmd` and `build_cmd` are empty strings are unaffected in behaviour and duration compared to current behaviour

## Assumptions

- The target repo is in a lint-clean state before bureau runs; pre-existing lint violations will block the builder at the lint gate regardless of whether the builder introduced them
- `install_cmd` (prepare phase) is run once per ralph round, not once per pipeline phase — this matches current behaviour and is unchanged
- The reviewer reads files from the memory scratchpad written by the builder node; files not listed in `files_changed` are not read
- Test quality is assessed by the presence of assertion statements — the reviewer does not execute static analysis tools to evaluate test quality
- Both builder and reviewer share the same `command_timeout` for all pipeline phases; per-phase timeouts are out of scope
