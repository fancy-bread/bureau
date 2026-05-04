# Data Model: Reviewer Hardening and Branch Lifecycle

**Feature**: 013-reviewer-hardening-branch-lifecycle
**Date**: 2026-05-03

---

## Modified Entities

### ReviewerFinding (`bureau/models.py`)

No schema change. The `type` field now carries a third value in practice: `"pipeline"` for bureau-internal diagnostic findings. No model change required — `type: str` accepts any value.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"requirement"` \| `"constitution"` \| `"pipeline"` |
| `ref_id` | `str` | Spec FR ID (e.g. `FR-001`), constitution ref, or sentinel (`PIPELINE`, `FILES-MISSING`, `TEST-QUALITY`) |
| `verdict` | `str` | `"met"` \| `"unmet"` \| `"violation"` |
| `detail` | `str` | What was found |
| `remediation` | `str` | What the Builder must do (empty if met) |

**Sentinel ref_ids** (bureau-internal, never appear in spec FR lists):

| ref_id | Produced by | Meaning |
|--------|-------------|---------|
| `PIPELINE` | `reviewer_node` | Reviewer's independent pipeline failed |
| `FILES-MISSING` | `reviewer_node` | No files_changed in builder summary, or a listed file is absent |
| `TEST-QUALITY` | `run_reviewer()` | Test file has no assertions |

---

### Phase (`bureau/state.py`)

Two values renamed:

| Old | New | Notes |
|-----|-----|-------|
| `GIT_BRANCH = "git_branch"` | `PREPARE_BRANCH = "prepare_branch"` | Node creates branch before builder |
| `GIT_COMMIT = "git_commit"` | `COMPLETE_BRANCH = "complete_branch"` | Node commits and pushes after reviewer passes |

`PLANNER = "planner"` removed (no planner node exists).

---

### BureauState (`bureau/state.py`)

`branch_name` is now set by `prepare_branch_node` instead of `complete_branch_node`. Semantically changed: it is available in state before the builder runs.

| Field | Set by | Read by |
|-------|--------|---------|
| `branch_name` | `prepare_branch_node` | `complete_branch_node`, `pr_create_node` |

---

## New Events

### `reviewer.pipeline`

Emitted by `reviewer_node` after the independent pipeline completes.

| Field | Type | Notes |
|-------|------|-------|
| `passed` | bool | Whether all phases passed |
| `phases` | list[str] | Phase names that ran (e.g. `["install", "lint", "build", "test"]`) |
| `failed_phase` | str \| null | Name of the failing phase, or null if passed |

---

### `reviewer.verdict`

Emitted by `_process_verdict` before routing.

| Field | Type | Notes |
|-------|------|-------|
| `verdict` | str | `"pass"` \| `"revise"` \| `"escalate"` |
| `round` | int | Ralph round index (0-based) |
| `summary` | str | One-sentence summary from the reviewer LLM |
| `findings` | list[object] | Condensed findings: `{ref_id, verdict, type}` per finding |

---

## Pipeline Phase Sequence (updated)

```
validate_spec → repo_analysis → memory → tasks_loader → prepare_branch → builder → reviewer → complete_branch → pr_create
```

`prepare_branch` is a new phase node. `complete_branch` replaces `git_commit`. All phase event consumers must accept the new names.
