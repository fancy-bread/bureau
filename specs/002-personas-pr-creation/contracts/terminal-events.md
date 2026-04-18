# Contract: Terminal Events (v2)

**Feature**: Bureau Personas and PR Creation | **Date**: 2026-04-18
**Supersedes**: `specs/001-autonomous-runtime-core/contracts/terminal-events.md`

All run events are written to stdout. Format: `[bureau] <event-name>  <key>=<value> ...`
Double-space between `event-name` and first key. Single space between subsequent key-value pairs.
No trailing newline after values. All timestamps ISO 8601.

---

## Event Catalogue

### `run.started`
```
[bureau] run.started  id=<run-id>  spec=<spec-path>  repo=<repo-path>
```
Emitted once at the start of `bureau run` or `bureau resume`.

### `phase.started`
```
[bureau] phase.started  phase=<phase-name>
```
Emitted immediately before a node begins execution.

### `phase.completed`
```
[bureau] phase.completed  phase=<phase-name>  duration=<Ns>
```
Emitted immediately after a node returns successfully. Duration in seconds, one decimal place.

### `ralph.started`
```
[bureau] ralph.started  phase=builder  round=<N>
```
Emitted at the start of each Ralph Loop round (0-indexed). `phase=builder` always.

### `ralph.attempt`
```
[bureau] ralph.attempt  phase=builder  round=<N>  attempt=<N>  result=<pass|fail>
```
Emitted after each Builder attempt within a round. `result=pass` means tests passed.

### `ralph.completed`
```
[bureau] ralph.completed  rounds=<N>  verdict=<pass|revise|escalate>
```
Emitted when the Ralph Loop concludes (Critic issues `pass` or the loop escalates).

### `run.escalated`
```
[bureau] run.escalated  id=<run-id>  phase=<phase-name>  reason=<EscalationReason>
```
Followed by a structured escalation block (see below).

### `run.completed`
```
[bureau] run.completed  id=<run-id>  pr=<pr-url>  duration=<Ns>
```
Emitted when `pr_create` completes successfully. Includes the PR URL.

### `run.failed`
```
[bureau] run.failed  id=<run-id>  phase=<phase-name>  error=<short-message>
```
Emitted when an unhandled error terminates the run.

---

## Escalation Block Format

Emitted to stdout after `run.escalated`. Indented with 2 spaces. Unchanged from v1.

```
[bureau] run.escalated  id=run-a3f2b1c9  phase=builder  reason=RALPH_EXHAUSTED

  What happened:  Builder exhausted 3 attempts in round 2 without a passing test run.
  What's needed:  Review the failing tests and provide guidance on the approach.
  Options:
    1. Resume with --response providing guidance on the failing tests
    2. Abort this run and revise the spec or task plan

  Resume: bureau resume run-a3f2b1c9 --response "..."
```

---

## Full Happy-Path Event Sequence

```
[bureau] run.started  id=run-a3f9c2b1  spec=specs/002-auth/spec.md  repo=./
[bureau] phase.started  phase=validate_spec
[bureau] phase.completed  phase=validate_spec  duration=0.3s
[bureau] phase.started  phase=repo_analysis
[bureau] phase.completed  phase=repo_analysis  duration=0.1s
[bureau] phase.started  phase=memory
[bureau] phase.completed  phase=memory  duration=0.0s
[bureau] phase.started  phase=planner
[bureau] phase.completed  phase=planner  duration=38s
[bureau] ralph.started  phase=builder  round=0
[bureau] ralph.attempt  phase=builder  round=0  attempt=0  result=fail
[bureau] ralph.attempt  phase=builder  round=0  attempt=1  result=pass
[bureau] phase.started  phase=critic
[bureau] phase.completed  phase=critic  duration=22s
[bureau] ralph.completed  rounds=1  verdict=pass
[bureau] phase.started  phase=pr_create
[bureau] phase.completed  phase=pr_create  duration=3s
[bureau] run.completed  id=run-a3f9c2b1  pr=https://github.com/org/repo/pull/42  duration=6m01s
```

---

## EscalationReason Values (extended)

| Reason | Phase | Description |
|--------|-------|-------------|
| `SPEC_INVALID` | validate_spec | Spec fails validation |
| `CONFIG_MISSING` | repo_analysis | `.bureau/config.toml` absent or invalid |
| `PLAN_INCOMPLETE` | planner | Planner cannot cover all P1 FRs |
| `RALPH_EXHAUSTED` | builder | Builder retry limit reached without passing tests |
| `RALPH_ROUNDS_EXCEEDED` | critic | Ralph Loop round limit reached without Critic pass |
| `CONSTITUTION_VIOLATION` | critic | Constitution violation detected; cannot revise |
| `PR_FAILED` | pr_create | PR creation failed (auth, remote, or API error) |
| `UNKNOWN` | any | Unclassified error |
