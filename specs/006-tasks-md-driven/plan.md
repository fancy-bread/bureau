# Implementation Plan: Tasks.md-Driven Execution

**Branch**: `006-tasks-md-driven` | **Date**: 2026-04-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-tasks-md-driven/spec.md`

## Summary

Replace the LLM Planner persona with a deterministic `tasks_loader_node` that parses `tasks.md` from the spec folder. The builder continues to receive a `task_plan` dict in state — only the source changes (file parse vs LLM generation). The CLI gains folder-path support; file-path invocation remains backwards-compatible.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: `pathlib` (stdlib), `re` (stdlib) — no new deps
**Storage**: LangGraph state (existing `SqliteSaver` checkpoint)
**Testing**: pytest (existing)
**Target Platform**: macOS/Linux (same as existing bureau)
**Project Type**: CLI modification + LangGraph node replacement
**Performance Goals**: `tasks_loader_node` completes in < 100ms (file I/O only, no LLM call)
**Constraints**: Must not break existing `bureau run <spec-file>` invocation; TaskPlan shape fed to builder must remain compatible

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | tasks.md is a spec artifact; bureau still requires approved spec folder |
| II. Escalate Don't Guess | ✅ PASS | TASKS_MISSING and TASKS_COMPLETE are structured escalations |
| III. Verification Gates | ✅ PASS | Critic gate unchanged; tasks_loader is a new pre-builder gate |
| IV. Constitution-First | ✅ PASS | no violations |
| V. Terse Output | ✅ PASS | tasks_loader emits standard phase events only |
| VI. Autonomous + Resumability | ✅ PASS | node is checkpointed; resumable |

**Note**: The constitution's Development Workflow section references "Planner" as a persona. This plan removes the LLM Planner — the constitution should be updated (PATCH bump) to reflect that the Planner role is now fulfilled by the developer via speckit, not by bureau at runtime.

## Project Structure

### Documentation (this feature)

```text
specs/006-tasks-md-driven/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── tasks-loader-node.md
└── tasks.md
```

### Source Code (repository root)

```text
bureau/
├── nodes/
│   ├── tasks_loader.py     ← new: reads tasks.md, builds TaskPlan, escalates if missing/complete
│   └── planner.py          ← deleted
├── personas/
│   └── planner.py          ← deleted
├── state.py                ← add TASKS_MISSING, TASKS_COMPLETE to EscalationReason; add spec_folder to initial state
├── graph.py                ← replace planner node with tasks_loader node
└── cli.py                  ← accept folder or file; resolve spec.md and tasks.md paths

tests/
├── unit/
│   └── test_tasks_loader.py  ← new: unit tests for tasks.md parsing
└── integration/
    └── test_graph_run.py     ← add: test_tasks_missing_escalates, test_tasks_complete_escalates
```

**Structure Decision**: Single new node file replacing planner. Two files deleted. Minimal surface area.
