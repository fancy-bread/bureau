# Research: CloudEvents 1.0 Event Format

## CloudEvents 1.0 JSON Format

**Decision**: Use CloudEvents 1.0 structured content mode (JSON)
**Rationale**: Well-adopted CNCF standard; JSON structured mode is the simplest to produce from Python and the most widely consumed by tooling.
**Alternatives considered**: Binary content mode (not needed for stdout); batch format (adds envelope complexity not justified for streaming stdout).

### Required Context Attributes

Every CloudEvents 1.0 JSON object MUST include:

| Attribute        | Type   | Constraint                                              |
|------------------|--------|---------------------------------------------------------|
| `specversion`    | string | Always `"1.0"`                                          |
| `id`             | string | Unique per event per source; UUID v4 is conventional    |
| `source`         | URI    | Identifies the producing system                         |
| `type`           | string | Reverse-DNS namespaced; e.g. `com.fancybread.bureau.run.started`    |

### Optional Context Attributes (used by bureau)

| Attribute          | Type        | Usage                                          |
|--------------------|-------------|------------------------------------------------|
| `time`             | RFC 3339    | Emission timestamp, UTC with milliseconds      |
| `datacontenttype`  | media type  | `"application/json"` for JSON `data`           |

### `data` Field

When `datacontenttype` is `application/json`, `data` is an inline JSON object (not a string). All event-specific fields from the v1.0.0 schema go here.

### Full Envelope Example

```json
{
  "specversion": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "urn:bureau:run:run-cbf3c2b9",
  "type": "com.fancybread.bureau.run.started",
  "time": "2026-04-25T14:32:00.123Z",
  "datacontenttype": "application/json",
  "data": {
    "run_id": "run-cbf3c2b9",
    "spec": "/repos/myapp/specs/001/spec.md",
    "repo": "/repos/myapp"
  }
}
```

---

## CloudEvents Python SDK (`cloudevents` package)

**Decision**: Use the `cloudevents` PyPI package for envelope construction
**Rationale**: Handles attribute validation, serialization, and spec compliance automatically. Avoids hand-rolling JSON with subtle spec violations. Lightweight (no heavy deps).
**Alternatives considered**: Hand-rolled `json.dumps` dict — simpler but risks missing spec nuances (e.g. `datacontenttype` quoting, `time` format). Not worth the risk for a format meant to be consumed by external validators.

```
pip install cloudevents
```

Key API:
```python
from cloudevents.http import CloudEvent
from cloudevents.conversion import to_json

event = CloudEvent(
    attributes={
        "type": "com.fancybread.bureau.run.started",
        "source": "urn:bureau:run:run-cbf3c2b9",
        "id": str(uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
    },
    data={"run_id": "run-cbf3c2b9", "spec": "...", "repo": "..."},
)
line = to_json(event).decode()  # returns bytes; decode to str
```

---

## NDJSON Stdout Streaming

**Decision**: One JSON object per line, flushed immediately
**Rationale**: NDJSON is the de facto standard for streaming structured records over a byte stream. Each event is self-contained; partial reads don't corrupt later events.
**Alternatives considered**: Pretty-printed JSON (multi-line per event) — breaks line-oriented log consumers and grep; not appropriate for streaming.

Implementation: `print(line, flush=True)` — matches the existing `flush=True` pattern in `events.emit()`.

---

## `source` URI Format

**Decision**: `urn:bureau:run:<run-id>` when no override is configured
**Rationale**: URN format is valid per CloudEvents spec (URI reference). Encodes the run ID directly so consumers can correlate events to runs without parsing the `data` field. Run IDs are UUID-based and globally unique, so the source URI is unique per run even with multiple concurrent bureau instances — no instance ID is needed for CloudEvents stdout output.
**Alternatives considered**: `https://bureau.local/<run-id>` — looks like an HTTP URL, implies a reachable endpoint that doesn't exist. `bureau://<run-id>` — custom scheme, less conventional than URN. `urn:bureau:instance:<id>:run:<run-id>` — correct for Kafka partition routing but premature here; deferred to the Kafka spec where multi-instance topology matters.

Override mechanism: `BUREAU_SOURCE_URI` environment variable. If set, used as-is for `source`. Allows organizations to use their own namespacing (e.g. `https://ci.myorg.com/bureau`).

> **Deferred**: `BUREAU_INSTANCE_ID` — a future env var that would enrich `source` to `urn:bureau:instance:<instance-id>:run:<run-id>`. Introduced in the Kafka spec where consumers need to route or filter by producing instance.

---

## Output Format Selection

**Decision**: `BUREAU_OUTPUT_FORMAT` environment variable; values `text` (default) and `cloudevents`
**Rationale**: Environment variable is the lowest-friction toggle for CI/CD — no file editing required, works in Docker, GitHub Actions, and shell one-liners. Consistent with `BUREAU_SOURCE_URI` pattern.
**Alternatives considered**: Config file entry in `.bureau/config.toml` — requires file editing, less convenient for ephemeral environments. CLI flag `--output-format` — would require threading through all call sites; env var is simpler given bureau's architecture.

Format is resolved once at `events` module import time and cached — no per-event overhead.

---

## Backward Compatibility

**Decision**: Plain-text format (`text`) is the default; zero behavior change unless `BUREAU_OUTPUT_FORMAT=cloudevents` is set
**Rationale**: All existing consumers (e2e test assertions, CI pipelines) depend on `[bureau] event  key=value` format. Opt-in CloudEvents protects them.
**Alternatives considered**: CloudEvents as default with text as fallback — would break existing e2e suite immediately; not viable without a major version boundary.

The existing `emit()` and `phase()` functions remain as the public API surface. Format selection is encapsulated inside them — callers do not change.

---

## Type Mapping: Bureau Event Names → CloudEvents `type`

| Bureau event        | CloudEvents `type`                |
|---------------------|-----------------------------------|
| `run.started`       | `com.fancybread.bureau.run.started`           |
| `run.completed`     | `com.fancybread.bureau.run.completed`         |
| `run.failed`        | `com.fancybread.bureau.run.failed`            |
| `run.escalated`     | `com.fancybread.bureau.run.escalated`         |
| `phase.started`     | `com.fancybread.bureau.phase.started`         |
| `phase.completed`   | `com.fancybread.bureau.phase.completed`       |
| `ralph.started`     | `com.fancybread.bureau.ralph.started`         |
| `ralph.attempt`     | `com.fancybread.bureau.ralph.attempt`         |
| `ralph.completed`   | `com.fancybread.bureau.ralph.completed`       |
| `builder.tool`      | `com.fancybread.bureau.builder.tool`          |

Pattern: `com.fancybread.bureau.<event-name>` — direct mapping, no transformation needed beyond prepending the namespace.

---

## Escalation Structured Fields

**Decision**: In CloudEvents mode, suppress the `print()` lines in `escalate_node` and include `what_happened`/`what_is_needed` in `run.escalated` `data`
**Rationale**: Raw `print()` lines are not CloudEvents events — they have no envelope, no type, no source. In CloudEvents mode a consumer reading NDJSON would see non-JSON lines and error. Structured fields in `data` are the correct location.
**Alternatives considered**: Emit a separate `escalation.detail` event type — adds a new event type for information already belonging to `run.escalated`; unnecessary. Keep print lines in both modes — violates NDJSON contract in CloudEvents mode.

The `escalate_node` must be aware of the active output format and conditionally suppress its raw print block.
