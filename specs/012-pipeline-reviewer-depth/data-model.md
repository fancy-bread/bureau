# Data Model: Command Pipeline Formalization and Reviewer Depth

**Date**: 2026-04-26 | **Feature**: [spec.md](spec.md)

## Entities

### PipelinePhase (enum)

Ordered pipeline step identifier.

| Field | Type | Notes |
|-------|------|-------|
| INSTALL | str | "install" |
| LINT | str | "lint" |
| BUILD | str | "build" |
| TEST | str | "test" |

**Ordering**: INSTALL < LINT < BUILD < TEST (strict; skipped phases do not change ordering of remaining phases)

---

### PipelineResult (Pydantic model)

Output of executing all configured pipeline phases in sequence.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| passed | bool | ✅ | True only if all non-skipped phases succeeded |
| failed_phase | Optional[PipelinePhase] | — | None if passed; first phase that returned non-zero exit |
| failed_output | str | — | stdout+stderr of the failing phase (max 2000 chars); empty if passed |
| phases_run | list[PipelinePhase] | ✅ | Phases actually executed (excludes skipped phases) |

**Validation rules**:
- `failed_phase` MUST be set if and only if `passed` is False
- `failed_output` MUST be non-empty if `failed_phase` is set

---

### TestQualityFinding (Pydantic model)

Reviewer finding for a test file that contains no assertions.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| file_path | str | ✅ | Relative path from repo root |
| reason | str | ✅ | Human-readable description of the quality failure |
| remediation | str | ✅ | What the builder must add |

**State transition**: When a `TestQualityFinding` is produced, the reviewer verdict MUST be `revise`.

---

### ReviewerFinding (existing, extended)

Existing model in `bureau/models.py`. No schema changes required; the test quality gate produces findings with `type="requirement"` and `ref_id="FR-007"`.

---

## State Changes

No changes to `RunState` (LangGraph state dict). All pipeline results are passed as local variables within node functions; `TestQualityFinding` instances are serialized into `ReviewerFinding` instances before being written to state.

## Memory Scratchpad

The `builder_summary` key (written by builder node, read by reviewer node) already contains `files_changed: list[str]`. No schema changes to the scratchpad.

```json
{
  "ralph_round": 0,
  "files_changed": ["src/foo.py", "tests/test_foo.py"],
  "last_test_output": "...",
  "attempts": [...]
}
```

The reviewer uses `files_changed` to locate files for content reading and the test quality gate.
