# Contract: git_commit_node

Node inserted between `critic` (verdict=pass) and `pr_create` in the LangGraph pipeline.

## Position in graph

```
critic (verdict=pass) → git_commit → pr_create
critic (escalate)     → escalate
```

## Inputs (from state)

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `run_id` | `str` | ✅ | Used to derive `run-id-prefix` for branch name |
| `repo_path` | `str` | ✅ | Absolute path to target repo |
| `spec` | `Spec \| None` | ✅ | Used to derive spec name for branch |
| `spec_path` | `str` | ✅ | Fallback for spec name if `spec` is None |

## Outputs (state updates)

| Key | Type | Description |
|-----|------|-------------|
| `branch_name` | `str` | Branch created and pushed: `feat/<spec-name>-<run-id-prefix>` |
| `phase` | `Phase` | `Phase.PR_CREATE` on success |
| `_route` | `str` | `"ok"` on success, `"escalate"` on failure |
| `escalations` | `list` | Appended on failure |

## Git operations (in order)

1. `git -C <repo_path> checkout -b <branch_name>` — create and switch to branch
2. `git -C <repo_path> add -A` — stage all changes
3. `git -C <repo_path> commit -m "feat: <spec-name> [bureau/<run-id-prefix>]"` — commit
4. `git -C <repo_path> push origin <branch_name>` — push to remote

## Escalation conditions

| Condition | EscalationReason | What's needed message |
|-----------|------------------|-----------------------|
| Branch name collision after 3 attempts | `GIT_BRANCH_EXISTS` | Delete stale bureau branches or run `bureau abort` on prior runs |
| `git checkout -b` fails (other reason) | `GIT_PUSH_FAILED` | Check repo state and git permissions |
| `git push` returns non-zero | `GIT_PUSH_FAILED` | Verify `gh auth status` and remote access |

## Events emitted

None beyond the standard `phase.started` / `phase.completed` from `events.phase()` context manager.
