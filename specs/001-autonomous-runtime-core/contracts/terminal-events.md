# Contract: Terminal Events

**Feature**: Bureau CLI Foundation | **Date**: 2026-04-16

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
Emitted immediately after a node returns successfully. Duration in seconds with one decimal place.

### `run.escalated`
```
[bureau] run.escalated  id=<run-id>  phase=<phase-name>  reason=<EscalationReason>
```
Followed by a structured escalation block (see below). Emitted when `escalate` node executes.

### `run.completed`
```
[bureau] run.completed  id=<run-id>  duration=<Ns>
```
Emitted when `pr_create` stub completes successfully.

### `run.failed`
```
[bureau] run.failed  id=<run-id>  phase=<phase-name>  error=<short-message>
```
Emitted when an unhandled error terminates the run.

---

## Escalation Block Format

Emitted to stdout after `run.escalated`. Indented with 2 spaces.

```
[bureau] run.escalated  id=run-a3f2b1c9  phase=validate_spec  reason=SPEC_INVALID

  What happened:  Spec contains 2 [NEEDS CLARIFICATION] markers in functional requirements.
  What's needed:  Resolve markers before running bureau.
  Options:
    1. Edit spec.md and remove all [NEEDS CLARIFICATION] markers
    2. Run /speckit-clarify to resolve them interactively

  Resume: bureau resume run-a3f2b1c9 --response "..."
```

Fields:
- `What happened`: One sentence describing the blocker
- `What's needed`: One sentence describing what would unblock the run
- `Options`: Numbered list; at least one option always present
- `Resume`: Exact command to resume; always present even when the run cannot be meaningfully resumed

---

## Stub Phase Events

Stub nodes (`planner`, `builder`, `critic`, `pr_create`) emit standard `phase.started` and
`phase.completed` events with an additional `stub=true` key:

```
[bureau] phase.started  phase=planner  stub=true
[bureau] phase.completed  phase=planner  duration=0.0s  stub=true
```
