# Data Model: Kafka Event Publisher

## Entities

### KafkaPublisher

The process-scoped Kafka producer wrapper. Initialised once at module import; `None` when broker not configured.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `bootstrap_servers` | `str` | `BUREAU_KAFKA_BOOTSTRAP_SERVERS` | Comma-separated broker addresses |
| `topic` | `str` | `BUREAU_KAFKA_TOPIC` or `"bureau.runs"` | Target topic name |
| `producer` | `Producer \| None` | confluent-kafka | Underlying producer; `None` when not configured |

**Lifecycle**: initialised at `bureau.kafka_publisher` module import; flushed and closed via `atexit`.

**State transitions**:
```
not configured → None (no-op on all publish calls)
configured     → Producer (active; publishes on every emit)
configured, broker down → Producer (active; publish fails silently per message)
```

---

### InstanceID

Process-scoped identity for multi-instance deployments.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `value` | `str` | `BUREAU_INSTANCE_ID` or `uuid4()` | Stable for process lifetime |

Generated once at module import alongside `KafkaPublisher` initialisation.

---

### KafkaMessage

The wire format of each published message.

| Field | Source | Value |
|-------|--------|-------|
| `topic` | `BUREAU_KAFKA_TOPIC` | `bureau.runs` (default) |
| `key` | run kwargs `id` field | run-id encoded as UTF-8 bytes |
| `value` | `to_json(CloudEvent(...))` | CloudEvents 1.0 JSON bytes |

The `CloudEvent` envelope for Kafka always uses:
- `source`: `urn:bureau:instance:<instance-id>:run:<run-id>`
- `type`: `com.fancybread.bureau.<event>` (same as stdout CloudEvents)
- All other attributes identical to stdout CloudEvents envelope

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BUREAU_KAFKA_BOOTSTRAP_SERVERS` | No | (unset = disabled) | Broker addresses; empty string treated as unset |
| `BUREAU_KAFKA_TOPIC` | No | `bureau.runs` | Target topic |
| `BUREAU_INSTANCE_ID` | No | UUID v4 generated at startup | Instance identifier for `source` URI |
