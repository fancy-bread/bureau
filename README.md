# Bureau

**Spec file in. Pull request out.**

Bureau is the autonomous runtime for [ASDLC](https://asdlc.io). You hand it an approved spec. It runs a structured pipeline — validate, plan, build, review — and opens a pull request. You review the PR. Everything in between is not your problem.

```
[bureau] run.started  id=run-a3f9c2b1  spec=specs/002-auth/spec.md  repo=./
[bureau] phase.started  phase=validate_spec
[bureau] phase.completed  phase=validate_spec
[bureau] phase.started  phase=builder
[bureau] phase.completed  phase=builder  duration=4m12s
[bureau] phase.started  phase=reviewer
[bureau] phase.completed  phase=reviewer  verdict=pass
[bureau] run.completed  pr=https://github.com/org/repo/pull/42  duration=6m01s
```

Set `BUREAU_OUTPUT_FORMAT=cloudevents` to emit [CloudEvents 1.0](https://cloudevents.io) NDJSON instead — one JSON object per line, parseable by any structured log consumer:

```json
{"specversion":"1.0","id":"8b67eaba...","source":"urn:bureau:run:run-a3f9c2b1","type":"io.bureau.run.started","time":"2026-04-25T14:32:00.123Z","datacontenttype":"application/json","data":{"id":"run-a3f9c2b1","spec":"specs/002-auth/spec.md","repo":"./"}}
```

---

## How it works

Bureau runs a [LangGraph](https://github.com/langchain-ai/langgraph) pipeline of five sequential phases. Each phase is a persona with a specific contract:

| Phase | Role | Output |
|-------|------|--------|
| `validate_spec` | Guard | Confirms spec is complete and unambiguous before any work starts |
| `repo_analysis` | Scout | Reads the target repo's `.bureau/config.toml` to understand the stack |
| `builder` | Engineer | Implements the plan using skills middleware; runs tests, iterates until passing |
| `reviewer` | Auditor | Scores the implementation across five axes against the spec and constitution |
| `pr_create` | Closer | Opens the pull request with a structured run summary |

If any phase cannot proceed, bureau emits a structured escalation and pauses. You provide the missing information and resume — no re-running from scratch.

---

## Stack

- **Python 3.14**
- **[LangGraph](https://github.com/langchain-ai/langgraph) 0.2+** — state machine orchestration with per-node checkpointing
- **SQLite** — run state persisted at `~/.bureau/runs/<run-id>/checkpoint.db`
- **[Typer](https://typer.tiangolo.com)** — CLI
- **[Anthropic API](https://docs.anthropic.com)** — Claude powers the builder and reviewer personas
- **[deepagents](https://github.com/deepagents/deepagents)** — skills middleware for the Builder; SKILL.md files from `bureau/skills/addyosmani/` are bundled in the package and loaded at Builder initialisation
- **Vendored skills** — four ASDLC skills sourced from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) v0.5.0 (MIT); see `NOTICE`
- **[cloudevents](https://pypi.org/project/cloudevents/)** — CloudEvents 1.0 envelope construction for structured NDJSON output (`BUREAU_OUTPUT_FORMAT=cloudevents`)

---

## Prerequisites

**uv** — Python package manager
```sh
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**GitHub CLI** — required for PR creation
```sh
brew install gh
gh auth login
```

**Anthropic API key** — required for persona execution (Builder, Reviewer)

**Local development** — store the key in `~/.bureau/.env` to keep bureau's Anthropic billing separate from Claude Code's Pro subscription:

```sh
mkdir -p ~/.bureau
cp bureau/data/env.example ~/.bureau/.env
# edit ~/.bureau/.env and replace the placeholder with your real key
```

Bureau reads `~/.bureau/.env` at startup via `python-dotenv`. Your shell environment takes precedence over the file — if `ANTHROPIC_API_KEY` is already exported in your shell, bureau uses that value.

**CI** — inject the key as an environment variable from a secret; no `.env` file is needed:

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

See `bureau/data/env.example` for the canonical list of variables bureau reads.

**Spec Kit** — required for the spec-driven development workflow
```sh
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
```
Initialise in your repo:
```sh
cd /path/to/your/repo
specify init . --ai claude
```
This scaffolds `.specify/` and wires the slash commands (`/speckit-specify`, `/speckit-plan`, etc.) for use with Claude Code.

**bureau** — the CLI itself (install from source until a release package is available)
```sh
uv pip install git+https://github.com/fancy-bread/bureau.git
```

**Target repo setup**
```sh
cd /path/to/your/repo
bureau init
```

> **Upcoming**: bureau will be released as an installable CLI via a curl script and Homebrew tap so that `brew install bureau` or `curl -LsSf https://bureau.sh/install.sh | sh` is the standard setup path.

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
base_image  = "python:3.14-slim"
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

## Structured output

Bureau emits one event per line to stdout. The format is controlled by `BUREAU_OUTPUT_FORMAT`:

| Value | Format | Default |
|-------|--------|---------|
| `text` (default) | `[bureau] event  key=value  key=value` | ✅ |
| `cloudevents` | CloudEvents 1.0 NDJSON | — |

CloudEvents mode produces spec-compliant envelopes with `specversion`, `id`, `source` (`urn:bureau:run:<run-id>`), `type` (`io.bureau.<event>`), `time`, `datacontenttype`, and `data`. Every event type in bureau's schema is supported.

Both variables are set the same way as `ANTHROPIC_API_KEY` — in `~/.bureau/.env` for persistent local config, or as shell/CI environment variables for per-invocation control. See `bureau/data/env.example` for the full list.

Text mode is the default and is byte-identical to previous releases — existing consumers are unaffected.

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
base_image  = "python:3.14-slim" # Docker base for the build environment
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
# Mirror CI (lint + unit + integration tests with 80% coverage gate)
make ci

# Individual targets
make lint        # ruff check
make test        # pytest unit + integration
make test-cov    # pytest with coverage report and 80% gate
make test-e2e    # end-to-end tests (requires live API key)

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
| Builder persona (deepagents + skills middleware) | ✅ |
| Reviewer persona (five-axis quality framework) | ✅ |
| PR creation | ✅ |
| CloudEvents 1.0 NDJSON output (`BUREAU_OUTPUT_FORMAT=cloudevents`) | ✅ |

