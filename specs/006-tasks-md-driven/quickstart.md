# Quickstart: Tasks.md-Driven Execution

## Happy path (folder invocation)

```sh
# Developer has completed speckit pipeline; spec folder has tasks.md
ls bureau-test/specs/001-smoke-hello-world/
# spec.md  plan.md  tasks.md  ...

bureau run specs/001-smoke-hello-world/ --repo bureau-test/

# Expected output — no phase=planner:
# [bureau] phase.started  phase=tasks_loader
# [bureau] phase.completed  phase=tasks_loader  duration=0.0s  tasks=5
# [bureau] ralph.started  phase=builder  round=0
# ...
# [bureau] run.completed  pr=https://github.com/...
```

## Backwards-compatible file invocation

```sh
# Old-style invocation still works
bureau run specs/001-smoke-hello-world/spec.md --repo bureau-test/
# tasks.md resolved from parent dir: specs/001-smoke-hello-world/tasks.md
```

## tasks.md missing escalation

```sh
bureau run specs/no-tasks-yet/ --repo bureau-test/

# Expected:
# [bureau] run.escalated  reason=TASKS_MISSING
#   What happened:  tasks.md not found at specs/no-tasks-yet/tasks.md
#   What's needed:  Run /speckit-tasks to generate tasks.md before invoking bureau.
```

## tasks.md all complete escalation

```sh
# All tasks already checked off
bureau run specs/done-spec/ --repo bureau-test/

# Expected:
# [bureau] run.escalated  reason=TASKS_COMPLETE
#   What happened:  tasks.md exists but all tasks are already complete.
#   What's needed:  Nothing to build. If this is a re-run, reset tasks or create a new spec.
```

## Files changed by this feature

| File | Change |
|------|--------|
| `bureau/nodes/tasks_loader.py` | New node |
| `bureau/nodes/planner.py` | Deleted |
| `bureau/personas/planner.py` | Deleted |
| `bureau/graph.py` | Replace planner with tasks_loader |
| `bureau/state.py` | Add TASKS_MISSING, TASKS_COMPLETE, spec_folder/tasks_path/plan_text to initial state |
| `bureau/cli.py` | Accept folder or file; resolve spec_folder |
| `tests/unit/test_tasks_loader.py` | New unit tests |
| `tests/integration/test_graph_run.py` | Add missing/complete escalation tests |
