# Feature Specification: Kafka Event Publisher

**Feature Branch**: `010-kafka-publisher`
**Created**: 2026-04-25
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Kafka publisher activates via environment variable (Priority: P1)

An operator running bureau in a data platform environment sets `BUREAU_KAFKA_BOOTSTRAP_SERVERS` and bureau automatically begins publishing all run events to the configured Kafka topic. No code changes or restarts beyond the environment variable are required. When the variable is absent, behaviour is identical to today.

**Why this priority**: Core value of the feature — zero-config opt-in publishing that is invisible when not configured. All other stories depend on this working.

**Independent Test**: Set `BUREAU_KAFKA_BOOTSTRAP_SERVERS` pointing to a local broker, run `bureau run <spec> --repo <repo>`, consume from the topic, and assert every event emitted to stdout also appears in the topic as a valid CloudEvents 1.0 JSON message.

**Acceptance Scenarios**:

1. **Given** `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is set and the broker is reachable, **When** bureau runs a spec, **Then** every run event is published to the topic in CloudEvents 1.0 JSON format with the correct `type`, `source`, and `data` fields
2. **Given** `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is not set, **When** bureau runs a spec, **Then** stdout behaviour is identical to before this feature and no Kafka code paths execute
3. **Given** a custom `BUREAU_KAFKA_TOPIC` is set, **When** bureau publishes events, **Then** messages appear on that topic rather than the default `bureau.runs`

---

### User Story 2 — Broker unavailability does not crash a run (Priority: P2)

An operator has `BUREAU_KAFKA_BOOTSTRAP_SERVERS` configured but the broker is temporarily unreachable (network partition, broker restart). Bureau continues to completion and opens the PR; the Kafka publishing failure is reported to stderr but does not abort the run.

**Why this priority**: Reliability contract — bureau's core job is producing a PR, not guaranteeing message delivery. Kafka is observability infrastructure; it must never block the primary outcome.

**Independent Test**: Point `BUREAU_KAFKA_BOOTSTRAP_SERVERS` at an unreachable address, run a spec end-to-end, assert exit code 0 and a PR URL in stdout. Assert a warning message on stderr referencing the Kafka failure.

**Acceptance Scenarios**:

1. **Given** `BUREAU_KAFKA_BOOTSTRAP_SERVERS` points to an unreachable broker, **When** bureau runs a spec, **Then** the run completes successfully with exit code 0 and opens a PR
2. **Given** the broker becomes unreachable mid-run after initial connection, **When** a publish attempt fails, **Then** bureau logs the failure to stderr and continues without retrying indefinitely
3. **Given** a broker failure occurs, **When** the run completes, **Then** stdout events are unaffected and complete

---

### User Story 3 — Per-run source identity via instance ID (Priority: P3)

In environments running multiple concurrent bureau instances (e.g., parallel CI jobs), each instance stamps its events with a stable identity so consumers can correlate events to their originating process. The identity is set via `BUREAU_INSTANCE_ID` or auto-generated at startup.

**Why this priority**: Needed for multi-instance deployments but adds no value for single-instance use. Safe to add after P1/P2 are validated.

**Independent Test**: Run two bureau instances simultaneously with distinct `BUREAU_INSTANCE_ID` values, consume from the topic, and assert events from each instance have distinct `source` URIs that include the respective instance IDs.

**Acceptance Scenarios**:

1. **Given** `BUREAU_INSTANCE_ID=worker-1` is set, **When** bureau publishes events, **Then** the `source` field is `urn:bureau:instance:worker-1:run:<run-id>`
2. **Given** `BUREAU_INSTANCE_ID` is not set, **When** bureau starts, **Then** a UUID is generated once for the process lifetime and used as the instance ID in all Kafka `source` URIs
3. **Given** two instances with different IDs run concurrently, **When** events are consumed from the topic, **Then** events are distinguishable by `source` without ambiguity

---

### Edge Cases

- What happens when the broker is reachable at startup but drops mid-run? — publish failures are silent after the first warning; run continues
- What happens when the topic does not exist? — broker auto-creates it if configured to do so; otherwise the first publish fails silently and is logged to stderr
- What happens if `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is set to an empty string? — treated as unset; Kafka path not activated
- What happens with very large event payloads (e.g., long test output in `ralph.attempt`)? — existing 500-char truncation on `output` field applies; no additional truncation needed

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is set and non-empty, bureau MUST initialise a Kafka producer at process startup and publish every event to the configured topic
- **FR-002**: When `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is absent or empty, bureau MUST NOT activate any Kafka code paths and behaviour MUST be identical to the pre-feature baseline
- **FR-003**: Every Kafka message MUST be a CloudEvents 1.0 JSON envelope with `specversion`, `id`, `source`, `type`, `time`, `datacontenttype`, and `data` fields — regardless of `BUREAU_OUTPUT_FORMAT`
- **FR-004**: The Kafka message key MUST be the run ID, ensuring all events for a run land on the same partition
- **FR-005**: The `source` field in Kafka envelopes MUST be `urn:bureau:instance:<instance-id>:run:<run-id>`; the instance ID is taken from `BUREAU_INSTANCE_ID` or a UUID generated once at startup
- **FR-006**: The Kafka topic MUST be configurable via `BUREAU_KAFKA_TOPIC`; the default MUST be `bureau.runs`
- **FR-007**: A broker failure at any point MUST NOT raise an unhandled exception or cause bureau to exit with a non-zero code — failures MUST be caught and reported to stderr
- **FR-008**: The stdout event stream MUST be unaffected by Kafka configuration — `BUREAU_OUTPUT_FORMAT` controls stdout independently

### Key Entities

- **KafkaPublisher**: Stateful component holding the producer connection; initialised once, closed at process exit; no-op implementation when broker not configured
- **InstanceID**: Process-scoped identifier; read from `BUREAU_INSTANCE_ID` env var or generated as UUID v4 at startup; stable for the lifetime of the process

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every event emitted to stdout also appears in the Kafka topic within 1 second when the broker is reachable
- **SC-002**: A run against an unreachable broker completes with exit code 0 in the same time as a run with no Kafka configuration (no timeout delays on the critical path)
- **SC-003**: All 10 bureau event types appear in the topic as valid CloudEvents 1.0 JSON for a full run
- **SC-004**: Message keys for a single run are identical across all events, enabling partition-ordered consumption
- **SC-005**: Zero existing unit or integration tests break when `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is not set

---

## Assumptions

- Kafka broker is pre-provisioned; bureau does not create or configure the broker
- Topic auto-creation is broker-side configuration; bureau does not enforce topic existence
- No authentication or TLS required for this spec — deferred to a future security spec
- `confluent-kafka` Python client is the selected library; its C extension dependency is acceptable in CI
- Redpanda is the recommended local development broker (single Docker container, Kafka-compatible API)
- The instance ID uniqueness guarantee is UUID v4 — collision probability is negligible for the expected concurrency
- Publish is fire-and-forget (no delivery confirmation wait on the critical path); at-least-once delivery is acceptable
