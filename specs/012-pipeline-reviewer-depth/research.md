# Research: Command Pipeline Formalization and Reviewer Depth

**Date**: 2026-04-26 | **Feature**: [spec.md](spec.md)

## Research Questions

1. How should pipeline phase execution be structured to avoid code duplication between builder and reviewer?
2. How does the reviewer read actual files from the memory scratchpad?
3. What constitutes a valid assertion in the test quality gate?
4. Where in the builder node should pipeline gates run relative to builder attempts?

---

## Question 1: Pipeline Phase Execution — Shared vs. Duplicated

**Decision**: Extract a `run_pipeline()` helper that both the builder node and reviewer persona can call. The helper accepts `(repo_path, phases, timeout)` and returns a `PipelineResult`.

**Rationale**: The pipeline sequence (install → lint → build → test, skipping empty phases) is identical for builder and reviewer. A shared utility avoids drift. The existing `execute_shell_tool` in `bureau/tools/shell_tools.py` is the correct primitive — `run_pipeline` wraps it.

**Alternatives considered**:
- Duplicate the logic in builder.py and reviewer.py — rejected because the phases must be kept in sync; a bug fix in one would silently not apply to the other.
- New `PipelineRunner` class — rejected as over-engineered; a module-level function suffices for a four-step sequence.

**Implementation note**: `install_cmd` runs once per builder round (current behaviour) and once by the reviewer before its pipeline execution. This is consistent with the spec assumption: "install_cmd (install phase) is run once per ralph round."

---

## Question 2: Reviewer File Reading from Memory Scratchpad

**Decision**: The reviewer reads `files_changed` from `builder_summary` in the memory scratchpad, then reads each file from disk at `repo_path / relative_path`.

**Rationale**: The builder already writes `files_changed: list[str]` to `builder_summary` in memory (see `bureau/nodes/builder.py:103`). The reviewer node already reads `builder_summary` via `Memory(run_id).read("builder_summary")`. The relative paths stored in `files_changed` are relative to `repo_path`. File contents are injected into the reviewer's LLM prompt, not passed through a tool — the reviewer persona uses a single synchronous API call.

**Alternatives considered**:
- Add file-reading tool use to the reviewer LLM call — rejected; tool-use adds latency and complexity. Injecting file contents directly into the prompt is simpler and sufficient for the file sizes expected.
- Store file contents in memory at build time — rejected; doubles storage and risks stale content if the builder modifies files after writing the summary.

**Edge cases** (per spec):
- `files_changed` absent or empty → reviewer skips file reading and issues `revise` (no files changed finding)
- File deleted before reviewer reads it → reviewer notes missing file and continues with available files

---

## Question 3: Test Quality Gate — Assertion Detection

**Decision**: Detect assertions by scanning test file contents for:
1. Bare `assert` keyword (`assert ` at word boundary)
2. Method calls matching `assert*` pattern (e.g., `assertEqual`, `assertIn`, `assertTrue`)
3. `pytest.raises` or `pytest.approx` usages

A test file with at least one assertion pattern passes. A test file with zero patterns is flagged as non-asserting.

**Rationale**: The spec requirement (FR-007) defines "test files that contain no assertions" as the failure case. Detecting `assert` keyword and `assert*` method calls covers pytest, unittest, and most other Python test styles without requiring AST parsing or static analysis tools.

**Alternatives considered**:
- AST parsing for assertion detection — rejected; spec assumption says "Test quality is assessed by the presence of assertion statements — the reviewer does not execute static analysis tools." String matching is the intended approach.
- Only check for `assert` keyword — rejected; unittest-style tests (`self.assertEqual(...)`) would be falsely flagged as non-asserting.

**Implementation**: The reviewer persona performs this check via string scanning of file contents before passing them to the LLM. An LLM-only check would be inconsistent; the spec explicitly requires an automatic revise verdict for non-asserting files.

---

## Question 4: Builder Pipeline Gate Placement

**Decision**: The builder runs the pipeline sequence (lint → build → test) as gates **inside each attempt loop**, before the LLM builder persona runs. The install phase runs once per round (current behaviour, unchanged).

**Rationale**: The spec FR-001–004 requires the builder to stop at the first failing phase and not proceed. The existing builder node runs `install_cmd` once before the attempt loop, then calls `run_builder_attempt()` in a loop. Adding lint/build as gates before each attempt means the builder detects failures introduced by the previous attempt immediately, before re-running the LLM.

**Revised understanding**: Re-reading FR-001 more carefully: "The builder MUST execute command phases in strict order: install → lint → build → test." The test phase is what `run_builder_attempt` already runs as part of its loop. The lint and build gates are pre-flight checks that run before the LLM generates code on attempt 0, and after each attempt to verify the attempt didn't break lint/build. This matches acceptance scenario 1: if lint fails before any attempt, builder stops and escalates.

**Final decision**: Add lint and build as gates after each `run_builder_attempt()` call (post-attempt verification), not before attempt 0 (pre-attempt lint on clean repo would always pass and add overhead). The test command is already executed by `run_builder_attempt`. If the attempt fails test, the loop continues. If lint/build fail after the attempt, escalate.

**Wait** — re-reading spec US1 acceptance scenario 1: "Given a repo with `lint_cmd = 'ruff check .'` and a linting violation, When bureau runs, Then the builder stops at the lint gate... and does not run the test suite." This implies lint runs BEFORE the test, not after. The pipeline is install → lint → build → test in order. Each attempt: run lint first, if it passes run build, if that passes run test.

**Revised final decision**: Within each attempt, the builder runs: (1) lint gate, (2) build gate, then (3) calls `run_builder_attempt` which executes test_cmd. If lint or build fail, the builder escalates (does not proceed to test). This matches the spec's sequential gate intent.

---

## Summary of Decisions

| Decision | Choice |
|----------|--------|
| Pipeline utility | Module-level `run_pipeline()` in `bureau/tools/pipeline.py` wrapping `execute_shell_tool` |
| Reviewer file source | Read from disk at `repo_path / path` for each path in `files_changed` from memory |
| Assertion detection | String scan for `assert ` keyword + `assert*` method calls |
| Builder gate placement | Lint + build run before test within each attempt loop |
| Reviewer pipeline | Full re-execution (install → lint → build → test) independent of builder |
| No new dependencies | All implementation uses existing stdlib + current deps |
