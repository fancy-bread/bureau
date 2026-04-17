# Implementation Plan: Bureau CLI Foundation

**Branch**: `001-autonomous-runtime-core` | **Date**: 2026-04-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-autonomous-runtime-core/spec.md`

## Summary

Build the foundation Python CLI application for bureau: a Typer-based `bureau` command with
`run`, `resume`, `list`, `show`, `abort`, and `init` subcommands; a LangGraph StateGraph
wired with all seven nodes (`validate_spec`, `repo_analysis`, `memory`, `planner`, `builder`,
`critic`, `pr_create`) plus `escalate`; SqliteSaver checkpointing after every node; real
implementations of `validate_spec`, `repo_analysis`, and `escalate`; stub implementations
of `planner`, `builder`, `critic`, and `pr_create`; a `Memory` scaffold class; and a
`bureau init` command that scaffolds `.bureau/config.toml` in a target repo. Done when
`bureau run <spec> --repo <path>` completes a stub end-to-end run emitting structured
events, and `bureau resume <run-id>` continues from the last checkpoint.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: langgraph 0.2+, langgraph-checkpoint-sqlite, typer, tomllib (stdlib), pydantic
**Storage**: SQLite per run via `SqliteSaver` (`~/.bureau/runs/<run-id>/checkpoint.db`); Memory store as JSON file (`~/.bureau/runs/<run-id>/memory.json`)
**Testing**: pytest, pytest-cov
**Target Platform**: macOS / Linux (developer's local machine; CLI tool)
**Project Type**: CLI application
**Performance Goals**: N/A for foundation scaffold — no LLM calls in this feature
**Constraints**: No Docker dependency for this feature; no Anthropic API calls; `gh` CLI not required until PR creation feature
**Scale/Scope**: Single-run sequential execution; v1 foundation only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First Execution | ✅ Pass | Approved spec exists; no implementation before spec |
| II. Escalate, Don't Guess | ✅ Pass | `escalate` is a real node; validate_spec rejects ambiguous specs before execution |
| III. Verification Gates Are Real Gates | ✅ Pass | `validate_spec` and `repo_analysis` are real gates; stub phases still emit verified events |
| IV. Constitution-First Compliance | ✅ Pass | No CRITICAL violations identified |
| V. Terse, Structured Output | ✅ Pass | All terminal output is structured run events; no prose output |
| VI. Autonomous Operation With Resumability | ✅ Pass | SqliteSaver checkpointing after every node; `bureau resume` required by SC-002 |

**Post-design re-check**: ✅ No violations introduced by Phase 1 design. Memory JSON file and per-run SQLite are both local and isolated.

## Project Structure

### Documentation (this feature)

```text
specs/001-autonomous-runtime-core/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── cli-commands.md
│   ├── terminal-events.md
│   ├── bureau-toml.md
│   └── bureau-config-toml.md
└── tasks.md             ← Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
bureau/
├── bureau/
│   ├── __init__.py
│   ├── cli.py                  ← Typer app; all command entry points
│   ├── run_manager.py          ← Run lifecycle: start, resume, list, show, abort
│   ├── graph.py                ← LangGraph StateGraph definition and compilation
│   ├── state.py                ← RunState TypedDict; Phase enum; all shared types
│   ├── memory.py               ← Memory class: write/read/summary
│   ├── spec_parser.py          ← Spec Kit Markdown → Spec dataclass
│   ├── repo_analyser.py        ← .bureau/config.toml → RepoContext dataclass
│   ├── config.py               ← bureau.toml and .bureau/config.toml loading
│   ├── events.py               ← Structured terminal event emission
│   └── nodes/
│       ├── __init__.py
│       ├── validate_spec.py    ← Real: validates spec structure + NEEDS CLARIFICATION check
│       ├── repo_analysis.py    ← Real: reads .bureau/config.toml → RepoContext
│       ├── memory_node.py      ← Real (scaffold): initialises Memory for run
│       ├── planner.py          ← Stub: emits phase events, writes placeholder output
│       ├── builder.py          ← Stub: emits phase events, writes placeholder output
│       ├── critic.py           ← Stub: emits phase events, returns pass verdict
│       ├── pr_create.py        ← Stub: emits phase events, logs placeholder PR URL
│       └── escalate.py         ← Real: prints structured escalation, pauses graph
├── tests/
│   ├── integration/
│   │   ├── test_graph_run.py   ← E2E stub run; resume from checkpoint
│   │   └── test_init_cmd.py    ← bureau init creates config; does not overwrite
│   └── unit/
│       ├── test_spec_parser.py
│       ├── test_repo_analyser.py
│       └── test_validate_spec.py
├── pyproject.toml
├── bureau.toml.example         ← documented example; not loaded automatically
└── Dockerfile                  ← scaffold only (FROM python:3.12-slim); not used in this feature
```

**Structure Decision**: Single-project layout. `bureau/` is both the repo root and the Python package directory. All source under `bureau/bureau/`; tests under `bureau/tests/`. Matches TDD Section 18 exactly.

## Complexity Tracking

> No constitution violations to justify.
