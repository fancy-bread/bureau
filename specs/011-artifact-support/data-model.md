# Data Model: Artifact Support

## report.json Schema

Written to `~/.bureau/runs/<run-id>/report.json`.

```json
{
  "run_id": "run-abc12345",
  "status": "complete",
  "spec_path": "specs/011-artifact-support/spec.md",
  "ralph_rounds": 2,
  "reviewer_findings": [
    {
      "type": "requirement",
      "ref_id": "FR-001",
      "verdict": "met",
      "detail": "Module created at expected path.",
      "remediation": ""
    }
  ],
  "files_changed": [
    "bureau/run_manager.py",
    "tests/unit/test_run_report.py"
  ],
  "attempt_durations": [45.2, 30.1],
  "final_verdict": "pass",
  "completed_at": "2026-04-26T03:09:56.397860+00:00"
}
```

### Field Definitions

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `run_id` | string | `state["run_id"]` | |
| `status` | string | `RunRecord.status` | One of: `complete`, `failed`, `paused` |
| `spec_path` | string | `state["spec_path"]` | |
| `ralph_rounds` | integer | `len(state["ralph_rounds"])` | Count of completed reviewer cycles |
| `reviewer_findings` | list | `state["reviewer_findings"]` | Last round's findings; empty list if run failed before reviewer |
| `files_changed` | list[string] | Aggregated from all `BuildAttempt.files_changed` | Union of unique paths, insertion order |
| `attempt_durations` | list[float] | Derived from `RalphRound.completed_at` - first attempt `timestamp` | Seconds per ralph round |
| `final_verdict` | string | Terminal node | One of: `pass`, `failed`, `escalated` |
| `completed_at` | string (ISO 8601) | Written at report time | |

### final_verdict Values

| Value | Condition |
|-------|-----------|
| `pass` | `pr_create_node` reached successfully |
| `escalated` | `escalate_node` reached |
| `failed` | Unhandled exception caught in `cli.py` |

## Build Audit Artifact

Written to `./bureau-artifacts/` during e2e test run, uploaded to CI.

| Attribute | Value |
|-----------|-------|
| File name (CloudEvents) | `bureau-run-<run-id>.ndjson` |
| File name (text mode) | `bureau-run-<run-id>.log` |
| File name (fallback) | `bureau-run-unknown-<epoch>.log` |
| Content | Raw bureau stdout (one line per event) |
| Directory | `./bureau-artifacts/` (relative to workflow working dir) |
| CI retention | 7 days |
| Upload condition | `always()` — runs even if tests fail |
