---
icon: octicons/broadcast-24
---

# Events

Bureau emits a structured event for every significant action. In text mode each event is a single `[bureau] event  key=value` line. In CloudEvents mode it is a spec-compliant JSON envelope with `type = com.fancybread.bureau.<event>`.

---

## Run lifecycle

| Event | Key fields | When |
|---|---|---|
| `run.started` | `id`, `spec`, `repo` | First line of every run |
| `run.completed` | `id`, `duration` | Run finished — PR created or already done |
| `run.escalated` | `id`, `phase`, `reason` | Run paused; developer action required |
| `run.failed` | `id`, `phase`, `error` | Unhandled exception; run cannot continue |

---

## Phase transitions

| Event | Key fields | When |
|---|---|---|
| `phase.started` | `phase` | Node begins executing |
| `phase.completed` | `phase`, `duration` | Node finished successfully |

`phase` values: `validate_spec`, `repo_analysis`, `tasks_loader`, `prepare_branch`, `builder`, `reviewer`, `complete_branch`, `pr_create`, `escalate`.

---

## RALPH loop

| Event | Key fields | When |
|---|---|---|
| `ralph.started` | `round` | A RALPH round begins |
| `ralph.attempt` | `round`, `attempt` | Builder starts an attempt within a round |
| `ralph.completed` | `round`, `passed` | Round finished; Reviewer has a verdict |

---

## Builder

| Event | Key fields | When |
|---|---|---|
| `builder.tool` | `tool`, `path` or `exit_code` | Builder invokes a filesystem or shell tool |

`tool` values: `write_file`, `edit_file`, `run_command`. For `run_command`, `exit_code` is included. For file tools, `path` is included.

---

## Reviewer

| Event | Key fields | When |
|---|---|---|
| `reviewer.pipeline` | `passed` | Independent pipeline re-execution result |
| `reviewer.verdict` | `verdict`, `findings` | Final Reviewer verdict for the round |

`verdict` values: `pass`, `revise`, `escalate`.

---

## PR creation

| Event | Key fields | When |
|---|---|---|
| `pr.created` | `id`, `pr`, `duration` | Pull request opened successfully |

---

## CloudEvents envelope

All events share the same envelope structure when `BUREAU_OUTPUT_FORMAT=cloudevents`:

```json
{
  "specversion": "1.0",
  "id": "<uuid>",
  "source": "urn:bureau:run:<run-id>",
  "type": "com.fancybread.bureau.<event>",
  "time": "<ISO-8601>",
  "datacontenttype": "application/json",
  "data": { "<key>": "<value>" }
}
```

The `source` URI uses `BUREAU_SOURCE_URI` if set, otherwise defaults to `urn:bureau:run:<run-id>`.
