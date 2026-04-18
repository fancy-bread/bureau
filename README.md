# Bureau

**Spec file in. Pull request out.**

Bureau is the autonomous runtime for [ASDLC](https://asdlc.io). You hand it an approved spec. It runs a structured pipeline — validate, plan, build, review — and opens a pull request. You review the PR. Everything in between is not your problem.

```
[bureau] run.started  id=run-a3f9c2b1  spec=specs/002-auth/spec.md  repo=./
[bureau] phase.started  phase=validate_spec
[bureau] phase.completed  phase=validate_spec
[bureau] phase.started  phase=planner
[bureau] phase.completed  phase=planner  duration=38s
[bureau] phase.started  phase=builder
[bureau] phase.completed  phase=builder  duration=4m12s
[bureau] phase.started  phase=critic
[bureau] phase.completed  phase=critic  verdict=pass
[bureau] run.completed  pr=https://github.com/org/repo/pull/42  duration=6m01s
```

---

## How it works

Bureau runs a [LangGraph](https://github.com/langchain-ai/langgraph) pipeline of five sequential phases. Each phase is a persona with a specific contract:

| Phase | Role | Output |
|-------|------|--------|
| `validate_spec` | Guard | Confirms spec is complete and unambiguous before any work starts |
| `repo_analysis` | Scout | Reads the target repo's `.bureau/config.toml` to understand the stack |
| `planner` | Architect | Breaks the spec into a verified, dependency-ordered task plan |
| `builder` | Engineer | Implements the plan, runs tests, iterates until the build passes |
| `critic` | Reviewer | Audits the implementation against the spec and constitution; blocks or approves |
| `pr_create` | Closer | Opens the pull request with a structured run summary |

If any phase cannot proceed, bureau emits a structured escalation and pauses. You provide the missing information and resume — no re-running from scratch.

---

## Stack

- **Python 3.14**
- **[LangGraph](https://github.com/langchain-ai/langgraph) 0.2+** — state machine orchestration with per-node checkpointing
- **SQLite** — run state persisted at `~/.bureau/runs/<run-id>/checkpoint.db`
- **[Typer](https://typer.tiangolo.com)** — CLI
- **[Anthropic API](https://docs.anthropic.com)** — Claude powers the planner, builder, and critic personas

---

## Quickstart

**1. Install bureau**

```sh
pip install -e ".[dev]"
```

**2. Scaffold a target repo**

```sh
bureau init --repo /path/to/your/repo
```

This creates `.bureau/config.toml`. Fill in the `FILL_IN` placeholders before running:

```toml
[runtime]
language    = "python"
base_image  = "python:3.12-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"
```

**3. Run a spec**

```sh
cd /path/to/your/repo
bureau run /path/to/specs/001-my-feature/spec.md
```

`--repo` defaults to `.`, so invoking bureau from the repo root is the normal workflow. Bureau validates the spec, analyses the repo, and runs the full pipeline. When done, it prints a PR URL.

---

## Run management

```sh
bureau list                        # all runs
bureau list --status paused        # only paused runs
bureau show <run-id>               # full run details
bureau resume <run-id>             # continue from last checkpoint
bureau resume <run-id> --response "AuthService.refreshToken() takes (token: str) -> str"
bureau abort <run-id>              # cancel a run
```

---

## Escalations

When bureau cannot proceed — ambiguous spec, missing contract, failing tests after N retries — it pauses and tells you exactly what it needs:

```
[bureau] run.escalated  id=run-a3f9c2b1  phase=builder  reason=BLOCKER

  What happened:  Builder encountered an undefined contract in auth-service interface.
  What's needed:  AuthService.refreshToken() signature — not present in spec or codebase.
  Options:
    1. Add the signature to the spec and resume
    2. Abort this run

  Resume: bureau resume run-a3f9c2b1 --response "..."
```

A wrong guess is worse than a paused run. Bureau escalates rather than hallucinate.

---

## Target repo setup

Every repo bureau operates on needs a `.bureau/config.toml`:

```toml
[runtime]
language    = "python"           # or typescript, go, etc.
base_image  = "python:3.12-slim" # Docker base for the build environment
install_cmd = "pip install -e ."
test_cmd    = "pytest"
build_cmd   = ""                 # optional
lint_cmd    = ""                 # optional

[bureau]
# constitution = ".bureau/constitution.md"  # optional project-specific constitution
```

Run `bureau init --repo <path>` to scaffold this file.

---

## Spec format

Bureau expects specs in the format produced by [Spec Kit](https://github.com/fancy-bread/bureau/tree/main/.claude/skills). Required sections:

- `## User Scenarios & Testing` — user stories with `### Title (Priority: P1)` headings
- `## Requirements` — functional requirements as `**FR-001**: ...` bullets
- `## Success Criteria` — measurable, technology-agnostic outcomes

Bureau will reject specs with `[NEEDS CLARIFICATION]` markers or missing P1 stories before any work begins.

---

## Development

```sh
# Run tests
pytest

# Lint
ruff check .

# Pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install
```

Run records are stored at `~/.bureau/runs/`. Each run gets a UUID-prefixed directory with `run.json` (metadata), `checkpoint.db` (LangGraph state), and `memory.json` (inter-phase scratchpad).

---

## Status

Bureau is in active development. The current release implements the CLI foundation:

| Capability | Status |
|------------|--------|
| Spec validation | ✅ |
| Repo config parsing | ✅ |
| Run lifecycle (create / resume / abort) | ✅ |
| `bureau init` | ✅ |
| LangGraph pipeline with checkpointing | ✅ |
| Planner persona | 🚧 stub |
| Builder persona | 🚧 stub |
| Critic persona | 🚧 stub |
| PR creation | 🚧 stub |

