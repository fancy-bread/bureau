# Research: Artifact Support for Bureau Runs

## Existing State Inventory

**Decision**: All data needed for `run-summary.json` is already present in LangGraph state at run-end.
**Rationale**: No new state fields are required for US1.
**Details**:
- `state["ralph_round"]` — current round counter (0-indexed integer). Completed round count = `len(state["ralph_rounds"])`.
- `state["ralph_rounds"]` — list of `RalphRound` dicts with fields: `round`, `build_attempts`, `reviewer_verdict`, `reviewer_findings`, `completed_at`.
- `state["reviewer_findings"]` — list of the *last* round's `ReviewerFinding` dicts (`type`, `ref_id`, `verdict`, `detail`, `remediation`).
- `state["build_attempts"]` — list of all `BuildAttempt` dicts with fields: `round`, `attempt`, `files_changed`, `test_output`, `test_exit_code`, `passed`, `timestamp`.
- `state["run_id"]`, `state["spec_path"]` — present from initial state.
- `RunRecord.status` — available from `get_run(run_id)` in `run_manager.py`.

## Where to Write run-summary.json

**Decision**: Write from within terminal nodes (`pr_create_node`, `escalate_node`) and from `cli.py` on the unhandled-exception path.
**Rationale**: Nodes have direct access to the full LangGraph state dict. The `cli.py` run loop discards streaming state chunks; retrieving the full final state from the SQLite checkpoint would add unnecessary complexity. The exception path in `cli.py` only has `RunRecord`, so it writes a minimal report there.
**Alternatives considered**:
- Writing exclusively from `cli.py` by loading the checkpoint: adds a `SqliteSaver` dependency to the CLI layer and couples it to LangGraph internals.
- Writing from a dedicated `report_node` at the end of the graph: adds a node that has no other purpose and slightly changes graph structure.

## Deriving files_changed and attempt_durations

**Decision**: Aggregate from `build_attempts` list in state.

- **files_changed**: union of unique file paths across all `BuildAttempt.files_changed` from all rounds, preserving insertion order.
- **attempt_durations**: duration of each ralph round in seconds, derived as `(RalphRound.completed_at − first BuildAttempt.timestamp in that round)`. If a round has no build attempts (shouldn't happen) or timestamps cannot be parsed, omit that entry.

**Rationale**: No new fields needed; data is already captured. Per-round duration (not per-attempt) matches what a human reader cares about — "how long did each builder-reviewer cycle take".

## Atomic Write for run-summary.json

**Decision**: Write to a `.tmp` sibling file then `os.replace()` (atomic on POSIX).
**Rationale**: Prevents partial reads if bureau is interrupted during write. Same directory as `run.json` so the rename is within the same filesystem mount.

## Build Audit Artifact: Capture Strategy

**Decision**: Write captured bureau stdout to per-test files in `./bureau-artifacts/` directory during the e2e test run; upload the directory as a CI artifact.
**Rationale**: The e2e test (`run_bureau()`) already captures bureau stdout in `result.stdout`. A pytest fixture (or inline write) can persist this to a named file after each test. This avoids mixing bureau output with pytest output and produces one file per bureau run.
**Alternatives considered**:
- `tee` in the workflow step: applies only to direct CLI invocations, not subprocess calls from within pytest. Doesn't work for this test structure.
- `BUREAU_STDOUT_FILE` env var in bureau itself: more invasive; bureau would need to tee its own output.

## Artifact Naming

**Decision**: Parse run-id from the first `run.started` event in stdout; fall back to `bureau-run-unknown-<epoch>` if absent.
- CloudEvents mode: `bureau-run-<run-id>.ndjson`
- Text mode: `bureau-run-<run-id>.log`

**Detection**: line contains `"run.started"` (either as CloudEvents type suffix or as text event name). In CloudEvents NDJSON, `json.loads(line)["data"]["id"]` gives the run-id. In text mode, `id=<run-id>` appears in the event line.

## GitHub Actions Artifact Upload

**Decision**: Use `actions/upload-artifact@v4` with `if: always()` and `retention-days: 7`.
**Rationale**: `always()` ensures upload runs even when tests fail, which is the primary value of the artifact. v4 is the current stable version.

## No New Python Dependencies

**Decision**: US1 uses only `json`, `os`, `pathlib` (stdlib). US2 uses only YAML/workflow configuration changes plus a few lines of Python in the e2e test.
