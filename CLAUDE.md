# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Bureau Is

Bureau is the autonomous ASDLC runtime. It takes an approved spec and produces a pull request.
The developer's job ends at spec approval and resumes at PR review. Everything in between is bureau.

Bureau has no compiled source code — it is a Claude Code skill framework and runtime configuration.
The "code" is the skills, templates, hooks, and constitution that govern how bureau runs.

## Workflow

Bureau uses Spec Kit skills invoked as slash commands. The phase sequence is:

```
/speckit-specify → /speckit-clarify → /speckit-plan → /speckit-tasks → /speckit-implement → /speckit-analyze
```

Git hooks fire automatically before/after most phases (see `.specify/extensions.yml`).

**Key commands:**
- `/speckit-constitution` — Update the project constitution
- `/speckit-specify` — Create/update a feature spec
- `/speckit-clarify` — Clarify ambiguities in the current spec
- `/speckit-plan` — Generate research, data model, and contracts
- `/speckit-tasks` — Generate dependency-ordered tasks.md
- `/speckit-implement` — Execute tasks
- `/speckit-analyze` — Cross-artifact consistency check
- `/speckit-checklist` — Generate domain-specific verification checklist
- `/speckit-taskstoissues` — Sync tasks to GitHub issues

## Architecture

Bureau is metadata-driven. There is no runtime process to start or binary to build.

**`.specify/`** — Spec Kit configuration and runtime artifacts
- `memory/constitution.md` — The 6 core principles; governs all runs. Constitution violations are CRITICAL and block PR creation.
- `templates/` — Canonical templates for spec, plan, tasks, agent files, checklists
- `extensions/git/` — Git extension: branch creation, commits, validation, remote detection
- `extensions.yml` — Hook registry wiring git operations before/after each phase

**`.claude/skills/`** — 14 skill implementations, each a `SKILL.md` defining execution logic
- `speckit-plan/`, `speckit-implement/`, `speckit-specify/`, etc.
- `speckit-git-*/` — Git workflow skills (initialize, feature branch, commit, validate, remote)

**`VISION.md`** — Bureau's point of view: taste, voice, decision heuristics, and persona boundary definitions (Planner / Builder / Critic).

## Constitution

`.specify/memory/constitution.md` is the authoritative governance document. Before touching
phase logic, skill definitions, or templates, check the constitution for applicable constraints.
The six principles: Spec-First, Escalate-Don't-Guess, Verification Gates, Constitution-First
Compliance, Terse Structured Output, Autonomous Operation With Resumability.

## Spec Artifacts

Each feature lives under `specs/[###-feature-name]/`:
```
spec.md       ← input contract
plan.md
research.md
data-model.md
contracts/
tasks.md
```

## Hook System

`.specify/extensions.yml` wires optional and mandatory hooks before/after each phase.
Most hooks are optional git auto-commits. The `before_constitution` hook (git initialize)
is mandatory. When editing extensions.yml, `optional: false` + `condition: null` = always runs.

## Active Technologies
- Python 3.12 + langgraph 0.2+, langgraph-checkpoint-sqlite, typer, tomllib (stdlib), pydantic (001-autonomous-runtime-core)
- SQLite per run via `SqliteSaver` (`~/.bureau/runs/<run-id>/checkpoint.db`); Memory store as JSON file (`~/.bureau/runs/<run-id>/memory.json`) (001-autonomous-runtime-core)
- Python 3.14 + langgraph 0.2+, langgraph-checkpoint-sqlite, anthropic>=0.25, typer>=0.12, pydantic>=2 (all existing) (002-personas-pr-creation)
- SQLite per-run checkpoint (existing); memory.json per-run scratchpad (existing — extended for task plan and build attempt history) (002-personas-pr-creation)
- Python 3.12+ + `python-dotenv>=1.0` (new runtime), `pytest-timeout>=2.3` (new dev dep), `subprocess` + `os` (stdlib), `gh` CLI (external, pre-installed on ubuntu-latest) (004-e2e-test-suite)
- `~/.bureau/.env` (user-managed, never version-controlled) (004-e2e-test-suite)

## Recent Changes
- 001-autonomous-runtime-core: Added Python 3.12 + langgraph 0.2+, langgraph-checkpoint-sqlite, typer, tomllib (stdlib), pydantic
