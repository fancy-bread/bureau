# Contract: CLI Commands

**Feature**: Bureau CLI Foundation | **Date**: 2026-04-16

All commands are subcommands of `bureau`. Exit codes: `0` = success, `1` = user error
(bad args, missing files), `2` = runtime error (run failed, graph error).

---

## `bureau run`

```
bureau run <spec-file> [--repo <path>] [--config <path>]
```

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `spec-file` | path | Yes | — | Path to spec.md (Spec Kit format) |
| `--repo` | path | No | `.` (cwd) | Path to target repository |
| `--config` | path | No | `bureau.toml` in cwd | Operator config file |

**Behaviour**:
- Assigns a new run ID (`run-<8hex>`)
- Creates `~/.bureau/runs/<run-id>/` directory
- Writes initial `run.json` with status `running`
- Compiles and invokes the LangGraph graph
- Emits structured events to stdout for each phase transition
- On completion: updates `run.json` status to `complete`
- On failure: updates `run.json` status to `failed`; exits with code `2`
- On escalation: updates `run.json` status to `paused`; exits with code `0`

**Stdout** (structured events — see terminal-events.md):
```
[bureau] run.started  id=run-a3f2b1c9  spec=specs/001.../spec.md  repo=./
[bureau] phase.started  phase=validate_spec
[bureau] phase.completed  phase=validate_spec  duration=0.1s
...
[bureau] run.completed  id=run-a3f2b1c9  duration=2.3s
```

---

## `bureau resume`

```
bureau resume <run-id> [--response "<text>"]
```

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `run-id` | string | Yes | — | Run ID from `bureau run` output |
| `--response` | string | No | `""` | Response to the escalation question |

**Behaviour**:
- Looks up `~/.bureau/runs/<run-id>/run.json`; errors if not found or status is not `paused`
- Reinitialises the LangGraph graph with the same `thread_id`; execution resumes from last checkpoint
- `--response` value is injected into graph state for the escalation node to read
- Emits structured events from the resume point

---

## `bureau list`

```
bureau list [--status <status>]
```

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--status` | string | No | all | Filter by status: `running`, `paused`, `complete`, `failed`, `aborted` |

**Output** (one run per line, tab-separated):
```
run-a3f2b1c9  complete  2026-04-16T10:00:00Z  specs/001-autonomous-runtime-core/spec.md
run-b4e3a2d1  paused    2026-04-16T11:30:00Z  specs/002-planner/spec.md
```

---

## `bureau show`

```
bureau show <run-id>
```

**Output**: Full `RunRecord` fields printed as key: value pairs, plus escalation history if any.

---

## `bureau abort`

```
bureau abort <run-id>
```

**Behaviour**:
- Updates `run.json` status to `aborted`
- Does not interrupt an actively running process (v1); acts on stored status only
- Exits `0` on success; `1` if run not found

---

## `bureau init`

```
bureau init [--repo <path>]
```

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--repo` | path | No | `.` (cwd) | Target repo to scaffold |

**Behaviour**:
- Creates `.bureau/` directory if it does not exist
- Writes `.bureau/config.toml` with default values (see bureau-config-toml.md)
- If `.bureau/config.toml` already exists: prints a warning and exits `0` without overwriting
- Prints path to created file on success
