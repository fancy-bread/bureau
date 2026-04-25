# Contract: `bureau.events` Module Interface

This contract defines the public interface of the `bureau/events.py` module after the CloudEvents feature is implemented. Callers (nodes, personas, CLI) do not change — format selection is encapsulated inside the module.

## Public API (unchanged)

```
emit(event: str, **kwargs: Any) -> None
phase(name: str, stub: bool = False) -> ContextManager
```

### `emit(event, **kwargs)`

Emits one structured event to stdout.

- **`event`**: One of the 10 defined event type names (see schema v1.0.0).
- **`**kwargs`**: Event-specific fields. Required fields for the event type must be present; optional fields may be omitted.
- **Side effects**: Writes one line to stdout, flushed immediately. Format depends on `BUREAU_OUTPUT_FORMAT`.
- **Returns**: `None`.
- **Raises**: Never raises — emit failures are silent (stdout write errors are not bureau's responsibility to handle).

### `phase(name, stub=False)`

Context manager wrapping a phase block. Emits `phase.started` on enter and `phase.completed` (with duration) on exit.

- **`name`**: Phase name string (e.g. `"builder"`).
- **`stub`**: If `True`, includes `stub=true` in both events.
- **Returns**: Context manager (no yielded value).

---

## Output Contract: Plain-Text Mode (`BUREAU_OUTPUT_FORMAT=text` or unset)

Each `emit()` call produces exactly one line:

```
[bureau] <event>  <key>=<value>  <key>=<value>
```

- Prefix: `[bureau] ` (literal, including trailing space)
- Fields: space-separated `key=value` pairs, two spaces between prefix+event and first field
- Line ends with `\n`; no trailing spaces
- Flushed immediately

**Invariant**: This format must remain byte-for-byte identical to the pre-feature output. Any change is a breaking change.

---

## Output Contract: CloudEvents Mode (`BUREAU_OUTPUT_FORMAT=cloudevents`)

Each `emit()` call produces exactly one line of NDJSON:

```json
{"specversion":"1.0","id":"<uuid4>","source":"<uri>","type":"com.fancybread.bureau.<event>","time":"<rfc3339>","datacontenttype":"application/json","data":{<event-fields>}}
```

- Single line (no pretty-printing)
- Ends with `\n`
- Flushed immediately
- All CloudEvents required attributes present
- `data` is always a JSON object; never `null` or absent

### Type Mapping

| `event` arg        | `type` attribute              |
|--------------------|-------------------------------|
| `run.started`      | `com.fancybread.bureau.run.started`       |
| `run.completed`    | `com.fancybread.bureau.run.completed`     |
| `run.failed`       | `com.fancybread.bureau.run.failed`        |
| `run.escalated`    | `com.fancybread.bureau.run.escalated`     |
| `phase.started`    | `com.fancybread.bureau.phase.started`     |
| `phase.completed`  | `com.fancybread.bureau.phase.completed`   |
| `ralph.started`    | `com.fancybread.bureau.ralph.started`     |
| `ralph.attempt`    | `com.fancybread.bureau.ralph.attempt`     |
| `ralph.completed`  | `com.fancybread.bureau.ralph.completed`   |
| `builder.tool`     | `com.fancybread.bureau.builder.tool`      |

### `source` Resolution

1. `BUREAU_SOURCE_URI` env var (if set and non-empty) — used as-is
2. `urn:bureau:run:<run-id>` — constructed from module-level cached run ID
3. `urn:bureau:run:unknown` — fallback when no run ID has been registered

### run ID Registration

`emit("run.started", id=<run-id>, ...)` caches the run ID at the module level. Subsequent events use it as the `source` run ID component.

---

## Escalation Contract: `escalate_node` Behavior by Format

| Format        | `run.escalated` event        | Raw print lines (what_happened, etc.) |
|---------------|------------------------------|---------------------------------------|
| `text`        | `[bureau] run.escalated ...` | Printed as today                      |
| `cloudevents` | CloudEvents JSON with `data.what_happened`, `data.what_is_needed` | Suppressed |

`escalate_node` calls `events.is_cloudevents_mode()` (a new module-level boolean accessor) to conditionally suppress its raw print block.

---

## Environment Variables

| Variable             | Values              | Default | Description                              |
|----------------------|---------------------|---------|------------------------------------------|
| `BUREAU_OUTPUT_FORMAT` | `text`, `cloudevents` | `text` | Selects output format for the process   |
| `BUREAU_SOURCE_URI`  | Any URI string      | (none)  | Overrides the CloudEvents `source` field |
