# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Bureau Is

Bureau is the autonomous ASDLC runtime. It takes an approved spec and produces a pull request.
The developer's job ends at spec approval and resumes at PR review. Everything in between is bureau.

Bureau has no compiled source code — it is a Claude Code skill framework and runtime configuration.
The "code" is the skills, templates, hooks, and constitution that govern how bureau runs.

## Before Committing

Run `make ci` to mirror the CI pipeline (lint + unit/integration tests) before every commit.

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

**`VISION.md`** — Bureau's point of view: taste, voice, decision heuristics, and persona boundary definitions (Planner / Builder / Reviewer).

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

## deepagents Reference

- GitHub: https://github.com/langchain-ai/deepagents
- Docs: https://docs.langchain.com/oss/python/deepagents (high-level only; source is more reliable)
- `execute` tool returns plain text ending with `[Command succeeded/failed with exit code N]` — not JSON
- For implementation questions, read the installed source: `.venv/lib/python3.14/site-packages/deepagents/`

## Active Technologies
- Python 3.14 + langgraph 0.2+, langgraph-checkpoint-sqlite, anthropic>=0.25, typer>=0.12, pydantic>=2, python-dotenv>=1.0
- SQLite per-run checkpoint via `SqliteSaver` (`~/.bureau/runs/<run-id>/checkpoint.db`); memory.json per-run scratchpad
- `pytest-timeout>=2.3` (dev dep); `gh` CLI (external); `git` CLI (assumed present)
- `~/.bureau/.env` (user-managed, never version-controlled)
- LangGraph state (existing `SqliteSaver` checkpoint) (005-builder-git-workflow)
- Python 3.14 + `pathlib` (stdlib), `re` (stdlib) — no new deps (006-tasks-md-driven)
- Python 3.14 + `deepagents>=0.5.3` (new), `langchain-anthropic` (new transitive dep), `FilesystemMiddleware`, `SkillsMiddleware`, `MemoryMiddleware`, `SummarizationMiddleware` from deepagents (007-deepagents-verifier-skills)
- SQLite per-run checkpoint via `SqliteSaver` (existing, unchanged); `bureau/skills/addyosmani/{build,test,ship,review}/SKILL.md` vendored skill files (007-deepagents-verifier-skills)
- Critic persona and node renamed to Reviewer throughout; `Phase.REVIEWER`, `ReviewerVerdict`, `ReviewerFinding`, `reviewer_model` in config (007-deepagents-verifier-skills)
- Python 3.14 (no code changes) + None new — file replacement only (008-enrich-skills)
- `bureau/skills/addyosmani/{build,test,ship,review}/SKILL.md` (tracked in git); skills sourced from addyosmani/agent-skills@0.5.0 with attribution frontmatter (008-enrich-skills)
- `cloudevents>=1.11` (new dep for CloudEvents envelope construction, 009-cloudevents-format); `OutputFormat` enum + `BUREAU_OUTPUT_FORMAT` env var selects text (default) vs CloudEvents NDJSON mode; `cloudevents.v1.http.CloudEvent` + `cloudevents.v1.conversion.to_json` for envelope serialization
- Python 3.14 + `confluent-kafka>=2.3` (new), `testcontainers[kafka]` (dev dep); `bureau/kafka_publisher.py` module-level singleton producer; `BUREAU_KAFKA_BOOTSTRAP_SERVERS` opt-in; `BUREAU_KAFKA_TOPIC` (default `bureau.runs`); `BUREAU_INSTANCE_ID` (default UUID); `acks=1`, `retries=0`; Redpanda container for integration tests (010-kafka-publisher)
- `~/.bureau/runs/<run-id>/run-summary.json` written atomically at every run terminus (pass/escalated/failed); `write_run_summary(state, final_verdict)` in `bureau/run_manager.py`; called from `pr_create_node`, `escalate_node`, and `cli.py` exception path; CI artifact upload via `actions/upload-artifact@v4` (`if: always()`, 7d retention) captures bureau stdout per e2e run (011-artifact-support)
- Python 3.14 + no new deps (012-pipeline-reviewer-depth); `bureau/tools/pipeline.py` new module with `run_pipeline(repo_path, phases, timeout) -> PipelineResult`; `PipelinePhase` enum (INSTALL/LINT/BUILD/TEST), `PipelineResult` pydantic model; builder runs lint+build as sequential gates before test within each attempt; reviewer independently re-executes full pipeline + reads actual `files_changed` from memory + applies test quality gate (assert-statement scanning)

## Recent Changes
- 007-deepagents-verifier-skills: deepagents>=0.5.3 added; Builder replaced with `create_deep_agent` adapter + `_extract_build_attempt()` state bridge; Critic renamed to Reviewer throughout (Phase, models, nodes, personas, tests, constitution v1.2.0); ASDLC skills vendored to `bureau/skills/addyosmani/{build,test,ship,review}/`; Builder wired with build/test/ship skills + MemoryMiddleware; Reviewer wired with review skill pre-flight check
- 001-autonomous-runtime-core: Added Python 3.12 + langgraph 0.2+, langgraph-checkpoint-sqlite, typer, tomllib (stdlib), pydantic
