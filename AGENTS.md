# AGENTS.md

Guidance for AI agents (Claude Code, GitHub Copilot, Cursor, etc.) working in this repository.

## What Bureau Is

Bureau is an autonomous ASDLC runtime. It takes an approved feature specification and produces a pull request. The developer's job ends at spec approval and resumes at PR review.

Bureau has no compiled source code — it is a Python runtime, a set of LangGraph nodes, and a skill framework. The "code" is the nodes, personas, tools, skills, templates, hooks, and constitution that govern how bureau runs.

## Before You Commit

```
make ci
```

This runs lint (`ruff check`, `ruff-format`) and the full test suite (`pytest tests/unit tests/integration`). Pre-commit hooks enforce the same checks — do not bypass them.

## Architecture

Bureau executes runs as a sequenced LangGraph pipeline:

```
validate_spec → repo_analysis → memory → tasks_loader → builder → reviewer → git_commit → pr_create
```

Escalations short-circuit to an `escalate` node at any phase.

**Key directories:**

| Path | Purpose |
|------|---------|
| `bureau/nodes/` | LangGraph node functions — one file per phase |
| `bureau/personas/` | LLM persona logic (builder, reviewer) |
| `bureau/tools/` | Shell execution, pipeline runner |
| `bureau/models.py` | Pydantic models shared across nodes |
| `bureau/state.py` | LangGraph state definition, enums |
| `bureau/events.py` | Structured event emission |
| `bureau/memory.py` | Per-run JSON scratchpad (`~/.bureau/runs/<id>/memory.json`) |
| `bureau/skills/addyosmani/` | Vendored SKILL.md files for builder/reviewer |
| `.specify/memory/constitution.md` | The six governing principles — read before changing phase logic |
| `.specify/templates/` | Canonical spec, plan, tasks, and agent context templates |
| `.claude/skills/` | Spec Kit skill implementations (speckit-plan, speckit-tasks, etc.) |

**State persistence:** SQLite checkpoint via `SqliteSaver` at `~/.bureau/runs/<run-id>/checkpoint.db`. Every node checkpoints; interrupted runs are resumable by ID.

## Constitution

`.specify/memory/constitution.md` is the authoritative governance document. The six principles:

1. **Spec-First Execution** — no implementation without an approved spec
2. **Escalate, Don't Guess** — surface uncertainty as structured escalations
3. **Verification Gates Are Real Gates** — a phase is not complete until output is verified
4. **Constitution-First Compliance** — constitution violations block PR creation
5. **Terse, Structured Output** — structured events only, no conversational filler
6. **Autonomous Operation With Resumability** — no mid-run check-ins; all state is checkpointed

Constitution violations are CRITICAL. Check it before changing phase logic, skill definitions, or templates.

## Key Conventions

- `execute_shell_tool` in `bureau/tools/shell_tools.py` is the only entrypoint for running shell commands. Do not call `subprocess` directly from nodes or personas.
- `run_pipeline` in `bureau/tools/pipeline.py` wraps `execute_shell_tool` for ordered phase execution (install → lint → build → test).
- The builder extracts `files_changed` from `write_file` and `edit_file` tool call args (`file_path` key). The reviewer reads those files from disk for code review.
- Events are emitted via `bureau.events.emit()`. Do not `print()` from nodes — all output goes through the event system.
- `Memory(run_id).write(key, value)` / `.read(key)` is the cross-node scratchpad. State dict carries structured data; memory carries prose summaries and file lists.

## Running the Test Suite

```bash
# Unit + integration (fast, no API calls)
pytest tests/unit tests/integration

# Single test file
pytest tests/unit/test_pipeline.py -v

# Full CI mirror
make ci
```

E2e tests require a live Anthropic API key and a target repo configured with `.bureau/config.toml`. They run in CI against `bureau-test-python`.

## Spec Kit Workflow

Bureau's own development uses Spec Kit slash commands:

```
/speckit-specify → /speckit-clarify → /speckit-plan → /speckit-tasks → /speckit-implement
```

Specs live under `specs/[###-feature-name]/`. Each feature directory contains `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, and `tasks.md`. Do not implement without a spec.

## Target Repo Config

Bureau runs against repos that contain a `.bureau/config.toml`. Required fields:

```toml
[runtime]
language    = "python"          # informational
base_image  = "python:3.13-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"

# Optional gates (empty string = skip)
lint_cmd  = "ruff check ."
build_cmd = ""

[ralph_loop]
max_builder_attempts = 3
max_rounds           = 3
command_timeout      = 300  # seconds, applies to all phases

[bureau]
constitution    = ".bureau/constitution.md"  # optional override
planner_model   = "claude-opus-4-7"
builder_model   = "claude-sonnet-4-6"
reviewer_model  = "claude-opus-4-7"
```
