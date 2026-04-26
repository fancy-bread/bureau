# Implementation Plan: Artifact Support for Bureau Runs

**Branch**: `011-artifact-support` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)

## Summary

Bureau runs produce no persistent trace beyond the PR body. This plan adds a structured `report.json` written at run end (pr_create, escalate, and failure paths) and a CI artifact upload of the captured bureau stdout after each e2e run. No new Python dependencies; all data is already present in LangGraph state.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: langgraph 0.2+, pydantic>=2, typer>=0.12 (all existing)
**Storage**: `~/.bureau/runs/<run-id>/report.json` (new file alongside existing `run.json`); `./bureau-artifacts/` directory during CI runs
**Testing**: pytest (existing)
**Target Platform**: Linux (CI), macOS (local dev)
**Project Type**: CLI tool / LangGraph runtime
**Performance Goals**: report.json write < 10ms (stdlib JSON, atomic rename)
**Constraints**: report.json write MUST NOT raise; CI artifact upload MUST run on test failure
**Scale/Scope**: One report.json per run; one artifact file per bureau run in e2e

## Constitution Check

- **Spec-First** ✅: Approved spec at `specs/011-artifact-support/spec.md`
- **Escalate-Don't-Guess** ✅: report.json write errors caught and logged to stderr; never raise
- **Verification Gates** ✅: Unit tests for `write_run_report`; e2e test validates artifact file is written
- **Constitution-First** ✅: No constitution changes; report includes reviewer findings for audit
- **Terse Output** ✅: No new stdout events; report.json is file-based
- **Autonomy/Resumability** ✅: write is idempotent; resumed runs overwrite with final state

No violations.

## Project Structure

### Documentation (this feature)

```text
specs/011-artifact-support/
├── plan.md
├── research.md
├── data-model.md
└── tasks.md
```

### Source Code Changes

```text
bureau/
├── run_manager.py          # add write_run_report(state, final_verdict)
└── nodes/
    ├── pr_create.py        # call write_run_report on success
    └── escalate.py         # call write_run_report on escalation

bureau/cli.py               # call write_run_report (minimal) on failure

tests/
├── unit/
│   └── test_run_report.py  # new: unit tests for write_run_report
└── e2e/
    ├── test_bureau_e2e.py  # write captured stdout to bureau-artifacts/
    └── conftest.py         # fixture: ensure bureau-artifacts/ dir exists

.github/workflows/
└── e2e-python.yml          # add upload-artifact step (always:true, 7d retention)
```

## Implementation Details

### US1: write_run_report

**Function signature** in `bureau/run_manager.py`:

```python
def write_run_report(state: dict, final_verdict: str) -> None
```

- Aggregates `files_changed` as ordered union from all `state["build_attempts"][*].files_changed`
- Derives `attempt_durations` per ralph round: `RalphRound.completed_at` minus first attempt `timestamp` in that round
- Writes atomically: `json.dumps → .tmp file → os.replace()`
- Errors caught with `except Exception` and printed to stderr; never re-raised
- Called in `pr_create_node` (final_verdict="pass"), `escalate_node` (final_verdict="escalated")
- Called in `cli.py` exception handler with a minimal state dict (final_verdict="failed")

### US2: Build audit artifact

**e2e test change**: After `run_bureau()` returns, write `result.stdout` to `./bureau-artifacts/<name>` where `<name>` is determined by parsing the stdout for `run.started` event run-id and detecting CloudEvents vs. text mode.

**Workflow change** in `e2e-python.yml`:
```yaml
- name: Upload bureau run artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: bureau-run-artifacts
    path: bureau-artifacts/
    retention-days: 7
    if-no-files-found: ignore
```

## Complexity Tracking

No constitution violations. No complexity exceptions required.
