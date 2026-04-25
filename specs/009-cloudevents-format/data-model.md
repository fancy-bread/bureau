# Data Model: CloudEvents 1.0 Event Format

## Entities

### OutputFormat (enum)

Determines how `events.emit()` serializes output.

| Value          | Description                                         |
|----------------|-----------------------------------------------------|
| `text`         | Default. Current `[bureau] event  key=value` format |
| `cloudevents`  | CloudEvents 1.0 JSON, one object per line (NDJSON)  |

Resolved once at module load from `BUREAU_OUTPUT_FORMAT` env var. Defaults to `text`.

---

### CloudEventsEnvelope

Represents one CloudEvents 1.0 structured event as it will be serialized to stdout.

| Field             | Type    | Required | Source                                      |
|-------------------|---------|----------|---------------------------------------------|
| `specversion`     | string  | yes      | Always `"1.0"`                              |
| `id`              | string  | yes      | UUID v4 generated at emit time              |
| `source`          | URI     | yes      | `urn:bureau:run:<run-id>` or `BUREAU_SOURCE_URI` env override |
| `type`            | string  | yes      | `com.fancybread.bureau.<event-name>`                    |
| `time`            | string  | yes      | RFC 3339 UTC timestamp at emit time         |
| `datacontenttype` | string  | yes      | Always `"application/json"`                 |
| `data`            | object  | yes      | Event-specific fields per v1.0.0 schema; `{}` if none |

**Relationships**: One `CloudEventsEnvelope` is produced per `events.emit()` call when `OutputFormat = cloudevents`.

---

### EventData

The `data` object inside a CloudEventsEnvelope. Shape varies by event type — fields are defined in the bureau event schema v1.0.0. All required schema fields are always present; optional fields are omitted when not applicable (not `null`).

---

### SourceURI

The value placed in the CloudEvents `source` attribute.

**Resolution order**:
1. `BUREAU_SOURCE_URI` environment variable (if set and non-empty)
2. `urn:bureau:run:<run-id>` constructed from the current run's ID

`run-id` is extracted from event kwargs when available (e.g. `run.started` carries `id`). For events that don't carry a run ID directly (e.g. `builder.tool`), the source is a module-level default set when `run.started` is first emitted.

---

## State Transitions

```
process start
    │
    ▼
OutputFormat resolved from env ──► cached for process lifetime
    │
    ▼
events.emit(event, **kwargs) called
    │
    ├── OutputFormat = text ──► write "[bureau] event  k=v ..." to stdout
    │
    └── OutputFormat = cloudevents ──► build CloudEventsEnvelope
                                        │
                                        ▼
                                    serialize to JSON (one line)
                                        │
                                        ▼
                                    write + flush to stdout
```

---

## Validation Rules

- `id`: Must be a valid UUID v4. Generated fresh per event — never reused.
- `source`: Must be a valid URI reference. URN form `urn:bureau:run:<run-id>` is always valid. Custom override must be non-empty.
- `type`: Must match pattern `io\.bureau\.[a-z]+(\.[a-z]+)+`.
- `time`: Must be RFC 3339 with UTC offset (`Z` or `+00:00`).
- `data`: Must be a JSON object (`{}`), never `null` or a scalar.
- `datacontenttype`: Fixed at `"application/json"` — not configurable.
