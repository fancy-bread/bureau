# Feature Specification: CloudEvents 1.0 Event Format

**Feature Branch**: `009-cloudevents-format`
**Created**: 2026-04-25
**Status**: Draft

## Overview

Bureau emits structured events throughout a run (phase transitions, builder attempts, escalations, etc.) as plain text lines to stdout. This feature adopts the CloudEvents 1.0 specification as the envelope format for those events, making bureau's output consumable by any CloudEvents-compatible tooling while preserving the existing plain-text format as the default for current consumers.

The event schema contract (12 event types, their fields, and constraints) is defined in the bureau event schema v1.0.0 document. This feature implements that contract in CloudEvents format — it does not change which events are emitted or when.

## User Scenarios & Testing

### User Story 1 - Enable CloudEvents output via configuration (Priority: P1)

An operator running bureau in a pipeline wants structured, machine-readable event output they can pipe to a CloudEvents consumer (log aggregator, monitoring system, webhook relay). They configure bureau to emit CloudEvents format and receive one JSON object per line on stdout, each a valid CloudEvents 1.0 envelope.

**Why this priority**: Unlocks all downstream integration use cases. Without the format switch, no external tooling can consume bureau events. This is the core capability of the feature.

**Independent Test**: Set the CloudEvents output format flag, run bureau against a test repo, and verify every line of stdout is a valid CloudEvents 1.0 JSON object with correct `specversion`, `type`, `source`, `id`, `time`, and `data` fields.

**Acceptance Scenarios**:

1. **Given** bureau is configured to emit CloudEvents format, **When** a run starts, **Then** stdout contains a single-line JSON object with `specversion: "1.0"`, `type: "io.bureau.run.started"`, a `source` URI containing the run ID, an RFC 3339 `time`, a unique `id`, and `data` containing `run_id`, `spec`, and `repo`.

2. **Given** bureau is configured to emit CloudEvents format, **When** any event is emitted, **Then** each event appears as exactly one complete JSON object on its own line (NDJSON), with no trailing content on that line.

3. **Given** bureau is configured to emit CloudEvents format, **When** a `ralph.attempt` event fires, **Then** the CloudEvents `data` field contains `round`, `attempt`, `result`, `exit_code`, and optionally `output` matching the v1.0.0 schema.

---

### User Story 2 - Preserve plain-text format as default (Priority: P2)

An operator running bureau in CI (GitHub Actions, terminal) with existing log parsing or e2e test assertions against the `[bureau] event  key=value` format must not have their workflow broken when they upgrade bureau. Plain-text format remains the default; CloudEvents is opt-in.

**Why this priority**: Existing consumers (e2e test suite, CI pipelines) depend on the current format. Breaking them on upgrade would block adoption of this feature.

**Independent Test**: Run bureau with no format configuration and verify stdout matches the existing `[bureau] event  key=value` pattern. Run the existing e2e test suite — all assertions must pass without modification.

**Acceptance Scenarios**:

1. **Given** bureau is run with no output format configuration, **When** any event is emitted, **Then** stdout matches the existing `[bureau] <event>  key=value  key=value` format unchanged.

2. **Given** the existing e2e test suite, **When** bureau runs in default mode, **Then** all existing stdout assertions pass without modification.

---

### User Story 3 - Structured escalation fields replace raw print output (Priority: P3)

When bureau escalates (pauses for human input), the escalation detail — what happened, what is needed, and resume instructions — currently appears as raw unstructured `print()` lines after the `run.escalated` event. In CloudEvents mode, this information must appear as structured fields in the `run.escalated` event's `data` object so consumers can act on it programmatically.

**Why this priority**: Escalation is the primary human-in-the-loop interaction point. Structured escalation data enables automated alerting, ticket creation, and resume workflows. Lower priority than core format adoption but required before Kafka transport is useful.

**Independent Test**: Trigger an escalation in CloudEvents mode. Verify the `run.escalated` event's `data` contains `what_happened` and `what_is_needed` as string fields. Verify no separate raw `print()` lines appear for escalation detail in CloudEvents mode.

**Acceptance Scenarios**:

1. **Given** bureau in CloudEvents mode encounters an escalation, **When** `run.escalated` is emitted, **Then** the `data` object contains `reason`, `what_happened` (string ≤ 1000 chars), and `what_is_needed` (string).

2. **Given** bureau in CloudEvents mode, **When** escalation occurs, **Then** no raw unstructured escalation detail lines appear on stdout — all detail is in the CloudEvents `data` field.

3. **Given** bureau in plain-text mode, **When** escalation occurs, **Then** behavior is unchanged — raw print lines still appear as today.

---

### Edge Cases

- What happens if stdout is not a TTY (piped to a file or another process) — CloudEvents NDJSON must still be written with flush per line.
- What happens if a field value contains characters that would break JSON (control characters, unescaped quotes) — values must be safely serialized.
- What happens if the CloudEvents format is configured but an event has no `data` fields — `data` should be an empty object `{}`, not omitted.
- What happens mid-run if format configuration cannot be read — bureau falls back to plain-text and logs a warning.

## Requirements

### Functional Requirements

- **FR-001**: The event output format MUST be selectable between `text` (default) and `cloudevents` via an environment variable (`BUREAU_OUTPUT_FORMAT`) or configuration file entry.
- **FR-002**: In CloudEvents mode, every bureau event MUST be emitted as a single-line JSON object conforming to CloudEvents 1.0 specification, written to stdout with an immediate flush.
- **FR-003**: Each CloudEvents envelope MUST include `specversion: "1.0"`, `type` (prefixed `io.bureau.`), `source` (URI containing the run ID), `id` (unique per event), `time` (RFC 3339 UTC), `datacontenttype: "application/json"`, and `data` (object).
- **FR-004**: The `type` field MUST map bureau event names to the `io.bureau.<event-name>` namespace (e.g. `run.started` → `io.bureau.run.started`).
- **FR-005**: All event-specific fields from the v1.0.0 schema MUST appear in the CloudEvents `data` object, with required fields always present and optional fields omitted when not applicable.
- **FR-006**: In plain-text mode, all existing event output MUST remain byte-for-byte identical to the current format — no changes to existing consumers.
- **FR-007**: In CloudEvents mode, `run.escalated` MUST include `what_happened` and `what_is_needed` as structured string fields in `data`, and the raw unstructured print lines for those fields MUST be suppressed.
- **FR-008**: The format selection MUST be determined once at process start and remain consistent for the entire run.

### Key Entities

- **CloudEvents Envelope**: The outer wrapper — `specversion`, `id`, `source`, `type`, `time`, `datacontenttype`, `data`. Maps 1:1 to one bureau event emission.
- **Event Data**: The inner payload — all event-specific fields from the v1.0.0 schema, serialized as a JSON object in the `data` field.
- **Output Format**: The active format (`text` or `cloudevents`), resolved at startup from environment or config.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every event emitted in CloudEvents mode validates against the CloudEvents 1.0 JSON schema without errors.
- **SC-002**: All 12 event types defined in the v1.0.0 schema are covered — no event type emits a malformed or incomplete envelope.
- **SC-003**: The existing e2e test suite passes without modification when bureau runs in default (plain-text) mode.
- **SC-004**: Switching from plain-text to CloudEvents mode requires a single environment variable change — no code changes, no restart beyond the process boundary.
- **SC-005**: Each CloudEvents line is flushed to stdout immediately upon emission — a consumer reading stdout line-by-line sees events in real time, not batched at process exit.

## Assumptions

- The CloudEvents 1.0 JSON event format (not binary or batch format) is the target encoding.
- NDJSON (one JSON object per line) is the stdout serialization — no envelope wrapping multiple events.
- The `source` URI format is `urn:bureau:run:<run-id>` unless a `BUREAU_SOURCE_URI` override is configured.
- The `id` field uses a UUID v4 generated per-event.
- `time` is the wall-clock UTC timestamp at the moment of emission, formatted as RFC 3339 with millisecond precision.
- The plain-text format is not deprecated by this feature — both formats are supported indefinitely.
- Kafka transport is out of scope; this spec covers stdout delivery only.
- The CloudEvents Python SDK (`cloudevents` package) is available to use if it simplifies envelope construction, but is not required.
