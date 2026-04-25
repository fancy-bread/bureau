# Tasks: CloudEvents 1.0 Event Format

**Input**: Design documents from `specs/009-cloudevents-format/`
**Branch**: `009-cloudevents-format`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All changes confined to `bureau/events.py`, `bureau/nodes/escalate.py`, `pyproject.toml`, and tests

---

## Phase 1: Setup

**Purpose**: Add the `cloudevents` PyPI dependency

- [X] T001 Add `cloudevents>=1.11` to `[project.dependencies]` in `pyproject.toml` and run `pip install -e ".[dev]"` to verify it resolves

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core abstractions in `bureau/events.py` that all three user stories depend on. Must be complete before any CloudEvents emit work begins.

**⚠️ CRITICAL**: US1, US2, and US3 all depend on this phase completing first.

- [X] T002 Add `OutputFormat` enum (`TEXT = "text"`, `CLOUDEVENTS = "cloudevents"`) and module-level `_FORMAT` constant resolved once from `os.environ.get("BUREAU_OUTPUT_FORMAT", "text")` in `bureau/events.py`
- [X] T003 Add module-level `_source_uri: str` defaulting to `os.environ.get("BUREAU_SOURCE_URI", "urn:bureau:run:unknown")` and `_register_run(run_id: str)` function that updates `_source_uri` to `urn:bureau:run:<run-id>` when `BUREAU_SOURCE_URI` is not set in `bureau/events.py`
- [X] T004 Add `is_cloudevents_mode() -> bool` public function returning `_FORMAT == OutputFormat.CLOUDEVENTS` in `bureau/events.py`

**Checkpoint**: `OutputFormat`, `_FORMAT`, `_source_uri`, `_register_run()`, and `is_cloudevents_mode()` all present and importable. Existing `emit()` and `phase()` signatures unchanged.

---

## Phase 3: User Story 1 — CloudEvents output via configuration (Priority: P1) 🎯 MVP

**Goal**: `BUREAU_OUTPUT_FORMAT=cloudevents` produces valid CloudEvents 1.0 NDJSON on stdout for all 10 event types.

**Independent Test**: Set `BUREAU_OUTPUT_FORMAT=cloudevents`, run `bureau run <spec> --repo <repo>` against the test repo, parse each stdout line as JSON, and validate CloudEvents attributes (`specversion`, `id`, `source`, `type`, `time`, `datacontenttype`, `data`) are present and well-formed.

- [X] T005 [US1] Implement `_emit_cloudevents(event: str, **kwargs: Any) -> None` in `bureau/events.py` using `cloudevents.http.CloudEvent` and `cloudevents.conversion.to_json` — builds envelope with `type=f"com.fancybread.bureau.{event}"`, `source=_source_uri`, UUID v4 `id`, RFC 3339 `time`, `datacontenttype="application/json"`, `data=kwargs or {}`, then calls `_register_run(kwargs["id"])` when event is `run.started`
- [X] T006 [US1] Update `emit()` in `bureau/events.py` to branch on `_FORMAT`: when `OutputFormat.CLOUDEVENTS` call `_emit_cloudevents(event, **kwargs)`; when `OutputFormat.TEXT` execute existing `[bureau] event  k=v` print (no change to text path)
- [X] T007 [US1] Add CloudEvents mode unit tests to `tests/unit/test_events.py`: set `BUREAU_OUTPUT_FORMAT=cloudevents` via monkeypatch, call `emit()` for each of the 10 event types, parse stdout as JSON, assert `specversion=="1.0"`, `type==f"com.fancybread.bureau.{event}"`, `source` contains run ID after `run.started`, `datacontenttype=="application/json"`, `data` is a dict

**Checkpoint**: `BUREAU_OUTPUT_FORMAT=cloudevents pytest tests/unit/test_events.py` passes. Each tested emit call produces valid JSON on one line.

---

## Phase 4: User Story 2 — Plain-text format preserved as default (Priority: P2)

**Goal**: No format configuration → identical `[bureau] event  k=v` output. Existing e2e test assertions pass without modification.

**Independent Test**: Run `make ci` with no `BUREAU_OUTPUT_FORMAT` set. All 110 existing unit/integration tests pass. Run the existing e2e test suite in default mode — all assertions against `[bureau]` prefixed lines still match.

- [X] T008 [P] [US2] Add text-mode regression unit tests to `tests/unit/test_events.py`: with no `BUREAU_OUTPUT_FORMAT` set (or set to `"text"`), assert `emit("run.started", id="run-abc", spec="/s", repo="/r")` produces exactly `[bureau] run.started  id=run-abc  spec=/s  repo=/r\n` — pin the byte-exact format for each structurally distinct event shape
- [X] T009 [P] [US2] Add unit test to `tests/unit/test_events.py` asserting `is_cloudevents_mode()` returns `False` when `BUREAU_OUTPUT_FORMAT` is unset and `True` when set to `"cloudevents"`, and that an invalid value (e.g. `"xml"`) raises `ValueError` at import time

**Checkpoint**: `make ci` passes with all 110+ tests green. Text output is byte-identical to pre-feature output.

---

## Phase 5: User Story 3 — Structured escalation in CloudEvents mode (Priority: P3)

**Goal**: In CloudEvents mode, `run.escalated` carries `what_happened` and `what_is_needed` in `data`; raw print lines are suppressed.

**Independent Test**: Trigger an escalation with `BUREAU_OUTPUT_FORMAT=cloudevents`. Parse the `run.escalated` JSON line — verify `data.reason`, `data.what_happened`, and `data.what_is_needed` are present. Verify no non-JSON lines appear on stdout after `run.escalated`.

- [X] T010 [US3] Update `escalate_node` in `bureau/nodes/escalate.py` to pass `what_happened=esc.what_happened[:1000]` and `what_is_needed=esc.what_is_needed` as kwargs to `events.emit(events.RUN_ESCALATED, id=run_id, phase=esc.phase, reason=esc.reason, ...)` (fields were previously only in raw print lines)
- [X] T011 [US3] Wrap the raw `print()` block in `escalate_node` (the `What happened:` / `What's needed:` / `Options:` / `Resume:` lines) in `if not events.is_cloudevents_mode():` in `bureau/nodes/escalate.py`
- [X] T012 [US3] Add escalation CloudEvents tests to `tests/integration/test_escalate_node.py`: in CloudEvents mode assert `run.escalated` JSON `data` contains `what_happened` and `what_is_needed`; in text mode assert the raw print lines still appear and the `run.escalated` event line does not contain `what_happened`

**Checkpoint**: Escalation in CloudEvents mode produces a single structured `run.escalated` JSON line with all fields. Escalation in text mode is byte-identical to pre-feature behavior.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T013 [P] Run `make ci` and verify coverage remains ≥ 80%; if `bureau/events.py` drops below threshold add targeted unit tests to `tests/unit/test_events.py` for any uncovered branches (e.g. `_register_run` override guard, `OutputFormat` fallback)
- [X] T014 [P] Update `## Active Technologies` in `CLAUDE.md` to add `cloudevents>=1.11` (new dep for CloudEvents envelope construction, 009-cloudevents-format)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (dependency installed)
- **US1 (Phase 3)**: Depends on Phase 2 — needs `OutputFormat`, `_emit_cloudevents`, `is_cloudevents_mode`
- **US2 (Phase 4)**: Depends on Phase 2 — T008/T009 can run in parallel with US1 (different test coverage, same file but non-conflicting)
- **US3 (Phase 5)**: Depends on Phase 3 — needs `is_cloudevents_mode()` to be live and `emit()` CloudEvents path to work
- **Polish (Phase 6)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Foundational complete → implement CloudEvents emit path → independently testable
- **US2 (P2)**: Foundational complete → regression test the text path → independently testable (no new code, just tests)
- **US3 (P3)**: US1 complete → update escalate_node → independently testable

### Parallel Opportunities

- T008 and T009 (US2 regression tests) can run in parallel with T005–T007 (US1 implementation) — they test the text path, which is already working
- T013 and T014 (Polish) can run in parallel with each other

---

## Parallel Example: Foundational Phase

```
T002: Add OutputFormat enum + _FORMAT resolution  →  bureau/events.py
T003: Add _source_uri cache + _register_run()     →  bureau/events.py (sequential after T002)
T004: Add is_cloudevents_mode()                   →  bureau/events.py (sequential after T003)
```

(All in the same file — must run sequentially)

## Parallel Example: US1 + US2

```
After Phase 2 completes:
  Path A (US1): T005 → T006 → T007   ← CloudEvents implementation + tests
  Path B (US2): T008, T009 [parallel] ← Text-mode regression tests (no new implementation)
```

---

## Implementation Strategy

### MVP (US1 Only)

1. T001 — add dependency
2. T002 → T003 → T004 — foundational abstractions
3. T005 → T006 — CloudEvents emit path
4. T007 — unit tests
5. **STOP and VALIDATE**: `BUREAU_OUTPUT_FORMAT=cloudevents bureau run <spec> --repo <repo>` — parse every stdout line as JSON

### Full Delivery

1. MVP above
2. T008, T009 — pin text regression (US2)
3. T010 → T011 → T012 — structured escalation (US3)
4. T013, T014 — polish

---

## Notes

- All implementation changes are in two files: `bureau/events.py` and `bureau/nodes/escalate.py`
- `_FORMAT` is resolved at module import — changing `BUREAU_OUTPUT_FORMAT` mid-process has no effect (by design, per FR-008)
- The `cloudevents` SDK's `to_json()` returns `bytes`; decode with `.decode()` before printing
- `data=kwargs or {}` ensures `data` is always a JSON object, never absent (contract requirement)
- Text path in `emit()` must not change — even whitespace differences would break existing consumers
