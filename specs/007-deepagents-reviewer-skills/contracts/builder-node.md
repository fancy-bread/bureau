# Contract: builder_node (deepagents-backed)

**Phase**: BUILDER | **File**: `bureau/nodes/builder.py`

## Input (from RunState)

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `run_id` | `str` | ✅ | Run identifier |
| `repo_path` | `str` | ✅ | Absolute path to target git repo |
| `task_plan` | `dict` | ✅ | Serialised `TaskPlan` from `tasks_loader` |
| `plan_text` | `str` | ✅ | Content of `plan.md` (may be empty string) |
| `spec_text` | `str` | ✅ | Raw spec markdown |
| `repo_context` | `RepoContext \| None` | ✅ | Config with `test_cmd`, `build_cmd`, `builder_model`, etc. |
| `ralph_round` | `int` | ✅ | Current round number (0-based) |
| `builder_attempts` | `int` | ✅ | Attempts used in current round |
| `build_attempts` | `list[dict]` | ✅ | All prior `BuildAttempt` records |

## Output (merged into RunState)

| Key | Type | Description |
|-----|------|-------------|
| `build_attempts` | `list[dict]` | Appended with new `BuildAttempt.model_dump()` |
| `builder_attempts` | `int` | Incremented |
| `phase` | `Phase` | `Phase.REVIEWER` on pass; `Phase.ESCALATE` on max retries |
| `_route` | `str` | `"ok"` → Reviewer; `"escalate"` → escalate node |

## Behaviour Contract

1. Construct `BuilderAgent` using `create_deep_agent`:
   - `model`: `repo_context.builder_model`
   - `system_prompt`: populated from spec, task plan, and constitution
   - `middleware`: `(FilesystemMiddleware(backend=FilesystemBackend(root_dir=repo_path)), SkillsMiddleware(backend=FilesystemBackend(root_dir=skills_root), sources=[build_sources, test_sources, ship_sources]), MemoryMiddleware(backend=FilesystemBackend(root_dir=context_dir), sources=[context_dir]), SummarizationMiddleware(model=builder_model, backend=FilesystemBackend()))`

2. Invoke agent with `HumanMessage("Begin implementation per the task plan.")` (first attempt) or retry message (subsequent attempts).

3. Walk returned `AgentState.messages` to extract `files_changed`, `test_exit_code`, `test_output`.

4. Construct and append `BuildAttempt` to `build_attempts`.

5. If `test_exit_code == 0`: route to Reviewer.

6. If `builder_attempts >= max_builder_attempts`: escalate with `EscalationReason.RALPH_EXHAUSTED`.

## Events Emitted

```
[bureau] ralph.started   phase=builder  round=N  attempt=N
[bureau] ralph.attempt   phase=builder  round=N  attempt=N  result=pass|fail
```

## Error Handling

- Any unhandled exception from `agent.invoke()` is caught, logged to `BuildAttempt.test_output`, and treated as `test_exit_code=-1` (fail).
- Skills directory missing or empty: logged as warning; Builder initialises with no vendored skills.
- Required ASDLC skill missing from sources: escalate with `EscalationReason.BLOCKER` at node init before any attempt.
