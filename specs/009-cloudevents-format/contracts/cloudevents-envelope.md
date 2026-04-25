# Contract: CloudEvents 1.0 Envelope JSON Schema

Defines the JSON structure each bureau event must produce in CloudEvents mode. Validators (unit tests, external tooling) MUST accept any conforming envelope and MUST reject any envelope missing a required attribute.

## JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/fancy-bread/bureau/schemas/cloudevents-envelope/1.0.0",
  "title": "Bureau CloudEvents Envelope",
  "type": "object",
  "required": ["specversion", "id", "source", "type", "time", "datacontenttype", "data"],
  "additionalProperties": false,
  "properties": {
    "specversion": {
      "type": "string",
      "const": "1.0"
    },
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "UUID v4, unique per event per source"
    },
    "source": {
      "type": "string",
      "format": "uri-reference",
      "description": "urn:bureau:run:<run-id> or BUREAU_SOURCE_URI override"
    },
    "type": {
      "type": "string",
      "pattern": "^io\\.bureau\\.[a-z]+(\\.[a-z]+)+$",
      "description": "Reverse-DNS namespaced event type"
    },
    "time": {
      "type": "string",
      "format": "date-time",
      "description": "RFC 3339 UTC timestamp of emission"
    },
    "datacontenttype": {
      "type": "string",
      "const": "application/json"
    },
    "data": {
      "type": "object",
      "description": "Event-specific fields per bureau event schema v1.0.0"
    }
  }
}
```

## Per-Event `data` Schemas

### `io.bureau.run.started`
```json
{ "run_id": "string (required)", "spec": "string (required)", "repo": "string (required)", "resumed": "boolean (optional)" }
```

### `io.bureau.run.completed`
```json
{ "run_id": "string (required)", "pr": "string (required)", "duration": "string (required)" }
```

### `io.bureau.run.failed`
```json
{ "run_id": "string (required)", "phase": "string (required)", "error": "string (required)" }
```

### `io.bureau.run.escalated`
```json
{
  "run_id": "string (required)",
  "phase": "string (required)",
  "reason": "string enum (required): CONFIG_MISSING | DIRTY_REPO | RALPH_EXHAUSTED | RALPH_ROUNDS_EXCEEDED | BLOCKER | UNKNOWN",
  "what_happened": "string ≤1000 chars (optional)",
  "what_is_needed": "string (optional)"
}
```

### `io.bureau.phase.started`
```json
{ "phase": "string (required)", "stub": "boolean (optional)" }
```

### `io.bureau.phase.completed`
```json
{
  "phase": "string (required)",
  "duration": "string (required)",
  "stub": "boolean (optional)",
  "tasks": "integer (optional, tasks_loader only)",
  "verdict": "string (optional, reviewer only): pass | revise",
  "round": "integer (optional, reviewer only)"
}
```

### `io.bureau.ralph.started`
```json
{ "phase": "string (required)", "round": "integer (required)" }
```

### `io.bureau.ralph.attempt`
```json
{
  "phase": "string (required)",
  "round": "integer (required)",
  "attempt": "integer (required)",
  "result": "string enum (required): pass | fail",
  "exit_code": "integer (required)",
  "output": "string (optional)"
}
```

### `io.bureau.ralph.completed`
```json
{ "rounds": "integer (required)", "verdict": "string (required)" }
```

### `io.bureau.builder.tool`
```json
{
  "tool": "string enum (required): write_file | read_file | edit_file | glob | grep | execute | ls",
  "detail": "string (optional)",
  "exit_code": "integer (optional, execute only)"
}
```

## Conformance Rules

1. An envelope missing any required attribute is **invalid**.
2. An envelope with `datacontenttype` other than `"application/json"` is **invalid**.
3. A `data` field that is `null`, a scalar, or an array is **invalid**.
4. A `type` not matching `^io\.bureau\.[a-z]+(\.[a-z]+)+$` is **invalid**.
5. Required `data` fields for the specific event type must be present (see per-event schemas above).
6. Optional `data` fields must be omitted (not `null`) when not applicable.
