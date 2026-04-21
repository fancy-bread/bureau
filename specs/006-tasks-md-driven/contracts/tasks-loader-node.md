# Contract: tasks_loader_node

Replaces `planner_node` in the graph. Runs between `memory` and `builder`.

## Inputs (from state)

| Key | Type | Required |
|-----|------|----------|
| `spec_folder` | `str` | Yes — absolute path to spec folder |
| `run_id` | `str` | Yes |

## Behaviour

1. Resolve `tasks_path = Path(spec_folder) / "tasks.md"`
2. If `tasks_path` does not exist → escalate `TASKS_MISSING`
3. Parse lines: collect all lines matching `^- \[ \]`
4. If no incomplete lines found:
   - If any `- [x]` lines exist → escalate `TASKS_COMPLETE`
   - Else → escalate `TASKS_MISSING`
5. Build `TaskPlan` from parsed lines (see data-model.md)
6. Read `plan_text` from `plan.md` if present
7. Return updated state

## Outputs (state keys set)

| Key | Value |
|-----|-------|
| `task_plan` | `TaskPlan.model_dump()` |
| `plan_text` | content of plan.md or `""` |
| `phase` | `Phase.BUILDER` |
| `_route` | `"ok"` |

## Escalation shape

```python
Escalation(
    reason=EscalationReason.TASKS_MISSING,  # or TASKS_COMPLETE
    what_happened="...",
    what_is_needed="Run /speckit-tasks to generate tasks.md before invoking bureau.",
    options=["Run /speckit-tasks in the spec folder", "bureau abort <run-id>"],
)
```

## Events emitted

```
[bureau] phase.started  phase=tasks_loader
[bureau] phase.completed  phase=tasks_loader  duration=Xs  tasks=N
```
