---
icon: octicons/rocket-24
---

# Quick Start

This walks through a bureau run from scratch — scaffolding a target repo, pointing bureau at a spec, and reading the output.

**Before you begin:** complete [Installation](installation.md).

---

## 1. Prepare the target repo

Bureau reads `.bureau/config.toml` from the target repo to understand the stack. Scaffold it with:

```sh
bureau init --repo /path/to/your/repo
```

This creates `.bureau/config.toml` with `FILL_IN` placeholders. Edit it before running:

```toml
[runtime]
language    = "python"
base_image  = "python:3.14-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"
```

See [Config Reference](config-reference.md) for all fields and language examples.

---

## 2. Prepare the spec

Bureau expects a spec folder produced by [Spec Kit](../how-to/write-a-spec.md). A typical folder looks like:

```
specs/001-my-feature/
├── spec.md          ← functional requirements and success criteria (required)
├── plan.md          ← architecture decisions, stack choices, phase breakdown
├── research.md      ← resolved unknowns and dependency decisions from planning
├── data-model.md    ← entities, fields, relationships, validation rules
└── tasks.md         ← dependency-ordered implementation plan (required)
```

Bureau requires `spec.md` and `tasks.md`. The other artifacts are produced by the Spec Kit planning phase (`/speckit-plan`) and give the Builder richer context — plan.md in particular shapes how the Builder structures its implementation. Omitting them is valid but the Builder will have less to work with.

Bureau will reject a spec with `[NEEDS CLARIFICATION]` markers or missing P1 user stories before any work begins.

---

## 3. Run

```sh
bureau run specs/001-my-feature/spec.md --repo /path/to/your/repo
```

`--repo` defaults to `.` — if you invoke bureau from inside the target repo, you can omit it. You can also pass the spec folder instead of the file:

```sh
bureau run specs/001-my-feature --repo /path/to/your/repo
```

---

## 4. Reading the output

Bureau emits one line per event. A passing run looks like:

```
[bureau] run.started          id=run-a3f9c2b1  spec=specs/001-my-feature/spec.md
[bureau] phase.started        phase=validate_spec
[bureau] phase.completed      phase=validate_spec
[bureau] phase.started        phase=prepare_branch
[bureau] phase.completed      phase=prepare_branch  branch=feat/my-feature-a3f9c2b1
[bureau] phase.started        phase=builder
[bureau] builder.tool         tool=write_file  path=src/feature.py
[bureau] builder.tool         tool=run_command  exit_code=0
[bureau] phase.completed      phase=builder  duration=4m12s
[bureau] phase.started        phase=reviewer
[bureau] reviewer.pipeline    passed=true
[bureau] reviewer.verdict     verdict=pass  findings=1
[bureau] phase.completed      phase=reviewer
[bureau] pr.created           id=run-a3f9c2b1  pr=https://github.com/org/repo/pull/42
[bureau] run.completed        id=run-a3f9c2b1  duration=6m01s
```

The final line includes a PR URL. That is the output of a successful run.

---

## 5. If bureau escalates

When bureau cannot proceed — exhausted retries, ambiguous spec, missing context — it pauses and tells you what it needs:

```
[bureau] run.escalated  id=run-a3f9c2b1  phase=builder  reason=RALPH_ROUNDS_EXCEEDED

  What happened:  Reviewer returned 'revise' after 3 rounds.
  What's needed:  FR-003 remains unmet — AuthService.refreshToken() signature not found in spec or codebase.
```

Runs are checkpointed — you can resume without re-running from scratch:

```sh
bureau resume run-a3f9c2b1
```

Or provide a response to the escalation:

```sh
bureau resume run-a3f9c2b1 --response "refreshToken takes (token: str) -> str"
```

---

## Run management

```sh
bureau list                       # all runs
bureau list --status paused       # only paused runs
bureau show <run-id>              # full run record
bureau abort <run-id>             # cancel a run
bureau prune --older-than 7       # dry-run: show runs older than 7 days
bureau prune --older-than 7 --no-dry-run   # delete them
```

Run state is stored at `~/.bureau/runs/<run-id>/`. Each run directory contains `run.json` (metadata), `checkpoint.db` (LangGraph state), and `memory.json` (inter-phase scratchpad).
