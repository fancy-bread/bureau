# Tasks: Kafka Event Publisher

**Input**: Design documents from `specs/010-kafka-publisher/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Organization**: Tasks grouped by user story for independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: Add dependencies and wire new module into the project

- [X] T001 Add `confluent-kafka>=2.3` to `[project.dependencies]` in pyproject.toml
- [X] T002 Add `testcontainers[kafka]` to `[project.optional-dependencies] dev` in pyproject.toml
- [X] T003 Document `BUREAU_KAFKA_BOOTSTRAP_SERVERS`, `BUREAU_KAFKA_TOPIC`, and `BUREAU_INSTANCE_ID` in `bureau/data/env.example`
- [X] T004 Add Redpanda local dev one-liner to `README.md`

---

## Phase 2: Foundational

**Purpose**: Core `kafka_publisher` module — the singleton producer that all stories depend on

**⚠️ CRITICAL**: User stories 1, 2, and 3 all require this module to exist

- [X] T005 Create `bureau/kafka_publisher.py` with module-level `_producer`, `_INSTANCE_ID`, and `_TOPIC` globals; `_init()` reads `BUREAU_KAFKA_BOOTSTRAP_SERVERS` and creates a `confluent_kafka.Producer` when set; `atexit.register(_flush)` for clean shutdown
- [X] T006 Implement `is_kafka_enabled() -> bool` in `bureau/kafka_publisher.py` returning `True` when `_producer is not None`
- [X] T007 Implement `publish(event: str, run_id: str, **kwargs: Any) -> None` in `bureau/kafka_publisher.py`: builds CloudEvents 1.0 envelope, calls `_producer.produce(_TOPIC, key=run_id.encode(), value=to_json(ce))`, catches all exceptions and logs to stderr

**Checkpoint**: Module importable; `is_kafka_enabled()` returns `False` when env var absent

---

## Phase 3: User Story 1 — Kafka publisher activates via environment variable (P1) 🎯 MVP

**Goal**: When `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is set, all bureau events are published to Kafka as CloudEvents 1.0 JSON; when absent, behaviour is unchanged.

**Independent Test**: Set `BUREAU_KAFKA_BOOTSTRAP_SERVERS` pointing to a local Redpanda broker, run bureau, consume from topic, assert all events present as valid CloudEvents 1.0 JSON.

### Implementation

- [X] T008 [US1] Wire `kafka_publisher.publish()` into `bureau/events.py` `emit()`: after the existing stdout path, call `publish(event, run_id, **kwargs)` when `is_kafka_enabled()` is `True`; extract `run_id` from `kwargs.get("id", "unknown")`
- [X] T009 [US1] Create `tests/unit/test_kafka_publisher.py`: test `is_kafka_enabled()` returns `False` when env var absent; test `publish()` is a no-op when `_producer is None`; test `publish()` calls `_producer.produce()` with correct topic, key, and CloudEvents JSON value (mock producer)
- [X] T010 [US1] Create `tests/integration/test_kafka_integration.py`: start `RedpandaContainer`, set `BUREAU_KAFKA_BOOTSTRAP_SERVERS`, reimport `bureau.kafka_publisher`, call `publish()` for a sample event, consume from topic, assert CloudEvents envelope fields (`specversion`, `type`, `source`, `id`, `time`, `datacontenttype`, `data`)
- [X] T011 [P] [US1] Test that custom `BUREAU_KAFKA_TOPIC` routes messages to the configured topic (integration test, in `tests/integration/test_kafka_integration.py`)

**Checkpoint**: US1 complete — Kafka publishes when configured, silent no-op when not

---

## Phase 4: User Story 2 — Broker unavailability does not crash a run (P2)

**Goal**: Bureau completes with exit code 0 even when the Kafka broker is unreachable; failures are logged to stderr only.

**Independent Test**: Point `BUREAU_KAFKA_BOOTSTRAP_SERVERS` at an unreachable address, assert exit code 0, PR URL in stdout, and a `[bureau/kafka]` warning on stderr.

### Implementation

- [X] T012 [US2] Verify `publish()` exception handler in `bureau/kafka_publisher.py` catches `BufferError`, `KafkaException`, and `Exception`; logs `[bureau/kafka] publish failed: {e}` to stderr; never re-raises
- [X] T013 [US2] Add unit test: mock `_producer.produce()` to raise `BufferError` → assert no exception propagates and stderr contains `[bureau/kafka] publish failed:`
- [X] T014 [US2] Add unit test: mock `_producer.produce()` to raise `KafkaException` → assert no exception propagates and stderr contains `[bureau/kafka] publish failed:`
- [X] T015 [US2] Add integration test in `tests/integration/test_kafka_integration.py`: set `BUREAU_KAFKA_BOOTSTRAP_SERVERS` to `localhost:19999` (unreachable), call `publish()`, assert no exception raised and stderr log produced

**Checkpoint**: US2 complete — broker failures are fully contained; run outcome unaffected

---

## Phase 5: User Story 3 — Per-run source identity via instance ID (P3)

**Goal**: Each bureau process stamps Kafka events with a stable `BUREAU_INSTANCE_ID` (or auto-generated UUID) in the `source` URI, enabling multi-instance correlation.

**Independent Test**: Set `BUREAU_INSTANCE_ID=worker-1`, call `publish()`, consume from topic, assert `source` is `urn:bureau:instance:worker-1:run:<run-id>`.

### Implementation

- [X] T016 [US3] Verify `_INSTANCE_ID` in `bureau/kafka_publisher.py` reads `BUREAU_INSTANCE_ID` env var; falls back to `str(uuid4())` generated once at module import
- [X] T017 [US3] Verify `publish()` builds `source` as `urn:bureau:instance:{_INSTANCE_ID}:run:{run_id}` in the CloudEvents `attributes`
- [X] T018 [US3] Add unit test: set `BUREAU_INSTANCE_ID=test-worker`, assert `source` field in produced message contains `urn:bureau:instance:test-worker:run:`
- [X] T019 [US3] Add unit test: unset `BUREAU_INSTANCE_ID`, assert `source` contains a UUID-shaped instance segment (regex `[0-9a-f-]{36}`)

**Checkpoint**: US3 complete — multi-instance deployments can disambiguate event streams

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 [P] Update `CLAUDE.md` Active Technologies with `confluent-kafka>=2.3` and `testcontainers[kafka]` entries
- [X] T021 Run `make ci` (lint + unit + integration tests) and confirm zero failures with `BUREAU_KAFKA_BOOTSTRAP_SERVERS` unset

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T001–T004 are independent [P]
- **Foundational (Phase 2)**: Depends on T001 (pyproject dep); blocks all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 2 completion; can run in parallel with US1
- **US3 (Phase 5)**: Depends on Phase 2 completion; can run in parallel with US1/US2
- **Polish (Phase 6)**: Depends on all user stories complete

### Parallel Opportunities

```bash
# Phase 1 — all independent:
T001  T002  T003  T004

# Phase 2 — sequential (each builds on previous):
T005 → T006 → T007

# After Phase 2 — all three stories can run concurrently:
[US1: T008–T011]  [US2: T012–T015]  [US3: T016–T019]
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1 (setup)
2. Complete Phase 2 (foundational module)
3. Complete Phase 3 (US1 — activation + publishing)
4. **Validate**: run unit + integration tests with Redpanda
5. Broker failure resilience (US2) and instance identity (US3) add incrementally

### Incremental Delivery

1. Setup + Foundational → importable `kafka_publisher` module
2. US1 → events flow to Kafka when configured (MVP)
3. US2 → broker failures fully contained
4. US3 → multi-instance `source` identity
5. Polish → CI clean, docs updated

---

**Total tasks**: 21
**Per story**: US1 — 4, US2 — 4, US3 — 4; Setup — 4, Foundational — 3, Polish — 2
**Parallel opportunities**: Phase 1 (4 tasks), Phase 3–5 (stories concurrent after Phase 2)
**Suggested MVP scope**: Phases 1–3 (User Story 1)
