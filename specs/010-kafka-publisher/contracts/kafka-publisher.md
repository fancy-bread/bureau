# Contract: `bureau.kafka_publisher` Module Interface

## Public API

```
publish(event: str, run_id: str, **kwargs: Any) -> None
is_kafka_enabled() -> bool
```

### `publish(event, run_id, **kwargs)`

Publishes one CloudEvents 1.0 envelope to Kafka. Called from `events.emit()` after the existing text/CloudEvents stdout logic.

- **`event`**: Bureau event name (e.g. `"run.started"`)
- **`run_id`**: Run ID used as the Kafka message key and embedded in `source`
- **`**kwargs`**: Event-specific fields placed in `data`
- **Side effects**: Enqueues one message to the Kafka producer (non-blocking). Logs to stderr on failure.
- **Returns**: `None`
- **Raises**: Never — all exceptions caught internally

### `is_kafka_enabled() -> bool`

Returns `True` when `BUREAU_KAFKA_BOOTSTRAP_SERVERS` is set and non-empty. Used by `events.emit()` to decide whether to call `publish()`.

---

## Message Contract

Every Kafka message MUST conform to:

| Field | Value |
|-------|-------|
| Topic | `BUREAU_KAFKA_TOPIC` (default `bureau.runs`) |
| Key | `run_id.encode("utf-8")` |
| Value | CloudEvents 1.0 JSON bytes |
| Encoding | UTF-8 |

### CloudEvents Envelope (Kafka)

```json
{
  "specversion": "1.0",
  "id": "<uuid4>",
  "source": "urn:bureau:instance:<BUREAU_INSTANCE_ID>:run:<run-id>",
  "type": "com.fancybread.bureau.<event>",
  "time": "<rfc3339-utc>",
  "datacontenttype": "application/json",
  "data": { "<event-specific fields>" }
}
```

- `source` always includes instance ID — distinguishes concurrent bureau processes
- `type` prefix matches stdout CloudEvents mode (`com.fancybread.bureau.*`)
- `data` schema per event type is identical to the stdout CloudEvents envelope (see spec 009 contracts)

---

## Environment Contract

| Variable | Behaviour when absent |
|----------|-----------------------|
| `BUREAU_KAFKA_BOOTSTRAP_SERVERS` | Kafka disabled; `publish()` is a no-op |
| `BUREAU_KAFKA_TOPIC` | Defaults to `bureau.runs` |
| `BUREAU_INSTANCE_ID` | UUID v4 generated at module import |

---

## Failure Contract

| Failure | Behaviour |
|---------|-----------|
| Broker unreachable at init | Producer created; error deferred to first `produce()` |
| `produce()` raises `BufferError` | Caught; one-line log to stderr; continue |
| `produce()` raises `KafkaException` | Caught; one-line log to stderr; continue |
| Any other exception | Caught; one-line log to stderr; continue |
| Delivery failure (async callback) | Logged to stderr; no retry |

Stderr log format: `[bureau/kafka] publish failed: {exception}`

Run exit code is never affected by Kafka failures.
