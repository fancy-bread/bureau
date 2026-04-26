# Tasks: Artifact Support for Bureau Runs

**Input**: Design documents from `specs/011-artifact-support/`
**Branch**: `011-artifact-support`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies at that point)
- **[Story]**: Which user story this task belongs to
- No setup or foundational phases required — this adds to an existing, fully initialized codebase

---

## Phase 1: User Story 1 — Run Summary File (Priority: P1) 🎯 MVP

**Goal**: Write `run-summary.json` to the run directory at every run terminus (pass, escalated, failed)

**Independent Test**: `make ci` passes; `~/.bureau/runs/<run-id>/run-summary.json` exists with all required fields after running bureau against a test spec via `pytest tests/unit/test_run_summary.py`

- [X] T001 [US1] Add `write_run_summary(state: dict, final_verdict: str) -> None` to `bureau/run_manager.py`:
  - Aggregate `files_changed` as ordered union from `state.get("build_attempts", [])` each entry's `files_changed` list
  - Derive `attempt_durations` from `state.get("ralph_rounds", [])`: for each round dict parse `completed_at` and the first `build_attempts[0]["timestamp"]`, return difference in seconds; skip rounds where timestamps are missing or unparseable
  - Build payload dict with keys: `run_id`, `status` (from `RunRecord.status` via `get_run(state["run_id"]).status`), `spec_path`, `ralph_rounds` (integer: `len(state.get("ralph_rounds", []))`), `reviewer_findings` (from `state.get("reviewer_findings", [])`), `files_changed`, `attempt_durations`, `final_verdict`, `completed_at` (ISO UTC now)
  - Write atomically: `json.dumps` to `<run_dir>/run-summary.json.tmp` then `os.replace()` to `run-summary.json`
  - Wrap entire function body in `try/except Exception as e: print(f"[bureau] run-summary write failed: {e}", file=sys.stderr)`

- [X] T002 [P] [US1] Add unit tests in `tests/unit/test_run_summary.py`:
  - `test_write_run_summary_pass`: state with 1 ralph_round (one BuildAttempt with files_changed and timestamp, completed_at set), final_verdict="pass"; assert file exists, all fields present, `final_verdict == "pass"`, `files_changed` populated, `attempt_durations` has one float
  - `test_write_run_summary_escalated`: final_verdict="escalated"; assert `final_verdict == "escalated"`
  - `test_write_run_summary_failed`: empty state (no build_attempts, no ralph_rounds); assert `files_changed == []`, `attempt_durations == []`, `ralph_rounds == 0`
  - `test_write_run_summary_overwrites_existing`: call twice; assert second write wins
  - `test_write_run_summary_never_raises`: patch `os.replace` to raise `OSError`; assert no exception propagates
  - Use `monkeypatch` to redirect `_runs_dir()` to `tmp_path`

- [X] T003 [P] [US1] Wire `write_run_summary(state, "pass")` into `bureau/nodes/pr_create.py`: call it after `run_summary` is built and before the final `return` at the end of the success path in `pr_create_node`; import `write_run_summary` from `bureau.run_manager`

- [X] T004 [P] [US1] Wire `write_run_summary(state, "escalated")` into `bureau/nodes/escalate.py`: call it after `write_run_record(record)` and before `return`; import `write_run_summary` from `bureau.run_manager`; pass `state` directly (the full node state dict is available)

- [X] T005 [US1] Wire `write_run_summary` into `bureau/cli.py` exception handler: in both `run()` and `resume()` commands, in the `except Exception as exc` block after `write_run_record(record)`, call `write_run_summary({"run_id": run_id, "spec_path": record.spec_path}, "failed")`; import `write_run_summary` from `bureau.run_manager`

**Checkpoint**: `make ci` passes; unit tests confirm run-summary.json is written correctly for all three verdict types

---

## Phase 2: User Story 2 — Build Audit Artifact on CI (Priority: P2)

**Goal**: Capture bureau stdout per e2e run to `./bureau-artifacts/` and upload as a GitHub Actions artifact

**Independent Test**: Trigger e2e workflow; confirm at least one downloadable artifact appears in the Actions run named `bureau-run-<run-id>.ndjson` or `.log`; verify upload step runs even when tests fail

- [X] T006 [P] [US2] Add `_write_bureau_artifact(stdout: str) -> None` helper to `tests/e2e/test_bureau_e2e.py`:
  - Parse run-id from stdout: iterate lines; if line parses as JSON and contains `"run.started"` in `type` field, use `json.loads(line)["data"]["id"]`; else if line matches text mode pattern `r"run\.started.*\bid=(\S+)"`, use the capture group; fallback: `f"unknown-{int(time.time())}"`
  - Detect format: if any line is valid JSON with a `specversion` key → CloudEvents (`.ndjson` extension) else `.log`
  - Write `stdout` to `Path("bureau-artifacts") / f"bureau-run-{run_id}.{ext}"` creating the directory if needed (`mkdir(parents=True, exist_ok=True)`)
  - Add `import json, re, time` at top if not already present

- [X] T007 [US2] Call `_write_bureau_artifact(result.stdout)` in `tests/e2e/test_bureau_e2e.py` immediately after each `result = run_bureau(...)` call in both `test_smoke_hello_world` and `test_escalation_missing_artifact`

- [X] T008 [P] [US2] Add artifact upload step to `.github/workflows/e2e-python.yml` after the "Run E2E tests" step:
  ```yaml
  - name: Upload bureau run artifacts
    if: always()
    uses: actions/upload-artifact@v4
    with:
      name: bureau-run-artifacts
      path: bureau-artifacts/
      retention-days: 7
      if-no-files-found: ignore
  ```

**Checkpoint**: Workflow run shows a downloadable `bureau-run-artifacts` artifact containing one `.ndjson` or `.log` file per bureau run

---

## Phase 3: Polish

- [X] T009 [P] Update `CLAUDE.md` Active Technologies and Recent Changes sections to document spec 011: `run-summary.json` written at terminus nodes, `write_run_summary` in `run_manager.py`, CI artifact upload via `actions/upload-artifact@v4`

---

## Dependencies & Execution Order

- **US1 (T001–T005)**: T001 first; T002, T003, T004 can then run in parallel (different files); T005 after T001
- **US2 (T006–T008)**: T006 first; T007 after T006 (same file); T008 parallel with T006/T007 (different file)
- **US1 and US2**: Fully independent — can be worked in any order
- **Polish (T009)**: After all implementation tasks

### Parallel Opportunities

```bash
# After T001 completes, these three can run in parallel:
T002  # tests/unit/test_run_summary.py
T003  # bureau/nodes/pr_create.py
T004  # bureau/nodes/escalate.py

# T008 can run any time alongside US2 work:
T008  # .github/workflows/e2e-python.yml (no Python dependency)
```

---

## Implementation Strategy

### MVP (US1 only)

1. T001 — implement `write_run_summary`
2. T002, T003, T004 in parallel — tests + node wiring
3. T005 — CLI failure path
4. `make ci` — validate

### Full delivery

1. MVP above
2. T006 → T007 — e2e artifact capture
3. T008 — workflow upload step (can merge to branch anytime)
4. T009 — CLAUDE.md update

---

## Notes

- `write_run_summary` MUST NOT raise under any circumstance — the try/except is the spec's safety contract
- `os.replace()` is atomic on POSIX (same filesystem); the `.tmp` intermediate prevents partial reads
- `_write_bureau_artifact` can silently skip if stdout is empty — `if-no-files-found: ignore` in the workflow handles the no-artifact case
- The artifact upload step uses `if: always()` not `if: success()` — this is the core requirement for CI inspectability
