# Data Model: Builder Git Workflow

**Feature**: 005-builder-git-workflow
**Date**: 2026-04-19

---

## New Entities

### GitWorkflowResult

Produced by `git_commit_node`. Written to LangGraph state and memory.

| Field | Type | Description |
|-------|------|-------------|
| `branch_name` | `str` | Full branch name: `feat/<spec-name>-<run-id-prefix>` |
| `commit_sha` | `str` | Short SHA of the commit created |
| `remote` | `str` | Remote name pushed to (always `origin` for v1) |
| `pushed` | `bool` | Whether push succeeded |

---

## Modified Entities

### `Phase` (StrEnum) — `bureau/state.py`

Add new phase value:

| New Value | String | Position in pipeline |
|-----------|--------|---------------------|
| `GIT_COMMIT` | `"git_commit"` | Between `CRITIC` and `PR_CREATE` |

### `EscalationReason` (StrEnum) — `bureau/state.py`

Add new escalation reasons:

| New Value | String | Trigger |
|-----------|--------|---------|
| `DIRTY_REPO` | `"DIRTY_REPO"` | Target repo has uncommitted changes at run start |
| `GIT_PUSH_FAILED` | `"GIT_PUSH_FAILED"` | `git push` returned non-zero |
| `GIT_BRANCH_EXISTS` | `"GIT_BRANCH_EXISTS"` | Branch collision exhausted 3 name attempts |

### `make_initial_state` — `bureau/state.py`

Add to initial state dict:

| New Key | Default | Description |
|---------|---------|-------------|
| `branch_name` | `""` | Populated by `git_commit_node`; read by `pr_create_node` |

---

## Branch Name Derivation

```
spec_path  →  stem  →  kebab-case  →  truncate to 40 chars
run_id     →  strip "run-" prefix  →  first 8 chars

branch_name = f"feat/{spec_name}-{run_id_prefix}"
```

**Examples**:
- `specs/001-smoke-hello-world/spec.md` + `run-deaaf184` → `feat/smoke-hello-world-deaaf184`
- `specs/002-auth-service/spec.md` + `run-a3f9c2b1` → `feat/auth-service-a3f9c2b1`

**Collision sequence**: `feat/<name>-<prefix>` → `feat/<name>-<prefix>-2` → `feat/<name>-<prefix>-3`

---

## Commit Message Format

```
feat: <spec-name> [bureau/<run-id-prefix>]
```

**Example**: `feat: smoke-hello-world [bureau/deaaf184]`
