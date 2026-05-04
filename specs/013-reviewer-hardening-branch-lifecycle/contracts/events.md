# Contract: New and Modified Events

**Feature**: 013-reviewer-hardening-branch-lifecycle
**Date**: 2026-05-03

This document defines the event contracts introduced or changed by this feature. All events follow the bureau event schema (see `projects/bureau/event-schema-v1.md` in Obsidian).

---

## New Events

### `reviewer.pipeline`

**When emitted**: After the Reviewer's independent pipeline runs, before any verdict logic.
**Emitted by**: `reviewer_node` in `bureau/nodes/reviewer.py`

**Text mode**:
```
[bureau] reviewer.pipeline  passed=True  phases=['install', 'build', 'test']  failed_phase=None
[bureau] reviewer.pipeline  passed=False  phases=['install', 'lint']  failed_phase=lint
```

**CloudEvents data payload**:
```json
{
  "passed": true,
  "phases": ["install", "build", "test"],
  "failed_phase": null
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `passed` | boolean | yes | True if all phases exited 0 |
| `phases` | array[string] | yes | Phase names that were executed |
| `failed_phase` | string \| null | yes | Name of first failing phase; null if passed |

---

### `reviewer.verdict`

**When emitted**: After verdict is produced, before routing (pass/revise/escalate).
**Emitted by**: `_process_verdict` in `bureau/nodes/reviewer.py`

**Text mode**:
```
[bureau] reviewer.verdict  verdict=pass  round=0  summary=All requirements met.  findings=[...]
[bureau] reviewer.verdict  verdict=revise  round=1  summary=FR-003 unmet.  findings=[...]
```

**CloudEvents data payload**:
```json
{
  "verdict": "pass",
  "round": 0,
  "summary": "All requirements met.",
  "findings": [
    {"ref_id": "FR-001", "verdict": "met", "type": "requirement"},
    {"ref_id": "FR-002", "verdict": "met", "type": "requirement"}
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `verdict` | string | yes | `"pass"` \| `"revise"` \| `"escalate"` |
| `round` | integer | yes | Ralph round index, 0-based |
| `summary` | string | yes | One-sentence summary from reviewer LLM |
| `findings` | array[object] | yes | Condensed finding list (see below) |

**Finding object**:

| Field | Type | Notes |
|-------|------|-------|
| `ref_id` | string | Spec FR ID, constitution ref, or sentinel (`PIPELINE`, `FILES-MISSING`, `TEST-QUALITY`) |
| `verdict` | string | `"met"` \| `"unmet"` \| `"violation"` |
| `type` | string | `"requirement"` \| `"constitution"` \| `"pipeline"` |

---

## Modified Phase Names

The following phase names changed. All consumers of `phase.started` and `phase.completed` events must accept the new values:

| Old name | New name |
|----------|----------|
| `git_branch` | `prepare_branch` |
| `git_commit` | `complete_branch` |

`planner` phase name removed (no planner node exists).

---

## Backward Compatibility

`reviewer.pipeline` and `reviewer.verdict` are **additive** — existing consumers that do not handle these event types are unaffected.

The phase name changes (`prepare_branch`, `complete_branch`) are **breaking** for any consumer that pattern-matches on `git_branch` or `git_commit` phase names. The e2e test `_assert_phase_order` lists have been updated accordingly.
