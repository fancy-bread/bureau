---
icon: octicons/alert-24
---

# Escalation

Escalation is a first-class outcome in bureau, not a failure mode. When bureau cannot proceed autonomously — exhausted retries, ambiguous spec, unresolvable dependency — it pauses the run, writes a structured escalation record, and waits. The run is fully checkpointed and can be resumed once the developer has resolved what was needed.

A paused run with a clear escalation is better than a completed run that silently produced incorrect output.

---

## What Triggers Escalation

| Reason | Trigger |
|---|---|
| `RALPH_ROUNDS_EXCEEDED` | Reviewer returned `revise` after `max_rounds` full cycles |
| `BUILDER_EXHAUSTED` | Builder failed after `max_builder_attempts` within a round |
| `SPEC_INVALID` | `validate_spec` found missing P1 stories or unresolved clarification markers |
| `CONSTITUTION_VIOLATION` | Reviewer found a CRITICAL finding that blocks PR creation |
| `PIPELINE_FAILURE` | Reviewer's independent pipeline re-execution failed in a way the Builder cannot fix |

---

## What an Escalation Contains

```
[bureau] run.escalated  id=run-a3f9c2b1  phase=reviewer  reason=RALPH_ROUNDS_EXCEEDED

  What happened:  Reviewer returned 'revise' after 3 rounds. FR-003 remains unmet.
  What's needed:  AuthService.refreshToken() signature is not defined in spec or codebase.
  Options:
    1. Add the signature to spec.md and resume
    2. Abort this run
```

Every escalation includes:

- **What happened** — the specific condition that triggered the pause
- **What is needed** — what the developer must provide or resolve
- **Options** — concrete next steps

The Reviewer also produces structured findings per functional requirement, so the developer can see exactly which FRs are unmet and why.

---

## Resuming a Run

```sh
# Resume from last checkpoint (no new information)
bureau resume run-a3f9c2b1

# Resume with a response to the escalation
bureau resume run-a3f9c2b1 --response "refreshToken takes (token: str) -> str"
```

The run continues from the checkpointed state. No phases before the escalation point are re-run.

---

## Run State After Escalation

Paused runs are listed by `bureau list --status paused`. Their checkpoint, spec path, and escalation record are all preserved in `~/.bureau/runs/<run-id>/`. A paused run can be:

- **Resumed** — after resolving the escalation condition
- **Aborted** — with `bureau abort <run-id>` if the run is no longer needed
- **Pruned** — with `bureau prune --missing-spec` or `--older-than N` to clean up old runs
