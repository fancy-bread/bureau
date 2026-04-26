# Research: Kafka Event Publisher

## confluent-kafka Python Producer

**Decision**: Use `confluent-kafka` PyPI package for Kafka publishing
**Rationale**: Official Confluent client, best performance (C extension via librdkafka), actively maintained, production-grade. Matches user decision.
**Alternatives considered**: `kafka-python` (pure Python, poorly maintained), `aiokafka` (async-first, incompatible with bureau's sync emit path).

Key Producer config for fire-and-forget:
```python
Producer({
    "bootstrap.servers": BUREAU_KAFKA_BOOTSTRAP_SERVERS,
    "acks": "0",   # true fire-and-forget — no broker ack required
})
```

- `Producer.produce(topic, key=run_id.encode(), value=json_bytes)` — non-blocking; queues message
- `acks='0'` means no delivery confirmation on critical path; messages may be silently dropped if broker is down — acceptable for observability-only publishing
- Delivery errors surface via optional `on_delivery` callback (used for stderr logging only, not required)
- `Producer.flush(timeout=0)` at process exit — zero timeout so it doesn't block shutdown
- `Producer.produce()` raises `BufferError` only if internal queue is full (`queue.buffering.max.messages` exceeded); all other failures are silent or callback-based
- Connection failure at init does NOT raise immediately — errors surface on first `produce()` or poll

---

## Producer Lifecycle

**Decision**: Module-level singleton initialised once in `bureau/kafka_publisher.py`; `None` when broker not configured
**Rationale**: Matches `_FORMAT` and `_source_uri` pattern from `bureau/events.py`. Single import, no dependency injection required. Process-scoped — correct for bureau's CLI model.
**Alternatives considered**: Class-based publisher passed through state — adds indirection with no benefit for a single-process CLI.

```python
_producer: Producer | None = None

def _init() -> None:
    global _producer
    servers = os.environ.get("BUREAU_KAFKA_BOOTSTRAP_SERVERS", "").strip()
    if servers:
        _producer = Producer({"bootstrap.servers": servers, ...})

_init()  # called at module import
```

`atexit.register(_flush)` handles clean shutdown.

---

## Error Handling

**Decision**: Catch all Kafka exceptions at the publish call site; log to stderr; never re-raise
**Rationale**: FR-007 — broker failure MUST NOT crash a run. `produce()` is called from inside `events.emit()` which is called from every node. An unhandled exception here would abort the LangGraph pipeline.

Exceptions to catch:
- `BufferError` — internal queue full (produce)
- `KafkaException` — base class for all confluent-kafka errors
- `Exception` — safety net for unexpected errors (e.g. init failure that deferred)

stderr log format: `[bureau/kafka] publish failed: {e}` (one line, no stack trace)

---

## Message Format

**Decision**: CloudEvents 1.0 JSON (same envelope as stdout CloudEvents mode); message key = run-id encoded as UTF-8 bytes
**Rationale**: Consistent with spec 009 envelope; consumers can use the same deserialiser as stdout. Key = run-id ensures partition ordering per run.

Source URI for Kafka differs from stdout: `urn:bureau:instance:<BUREAU_INSTANCE_ID>:run:<run-id>`
Instance ID: `BUREAU_INSTANCE_ID` env var if set, otherwise UUID v4 generated at module import (same as `_init()`).

---

## Topic Configuration

**Decision**: `BUREAU_KAFKA_TOPIC` env var, default `bureau.runs`
**Rationale**: Operator may need different topics per environment (dev/staging/prod). Single topic with type-based discrimination is sufficient for bureau's event volume.
**Alternatives considered**: Per-event-type topics (e.g. `bureau.run.started`) — premature; adds consumer complexity without current benefit.

---

## testcontainers Integration

**Decision**: Use `testcontainers` PyPI package with `redpandadata/redpanda` Docker image for integration tests
**Rationale**: Redpanda is Kafka-compatible, starts in ~1s, single container (no ZooKeeper), actively maintained. testcontainers handles lifecycle automatically in pytest.

Use `pip install testcontainers[kafka]` — the `testcontainers.kafka` module ships a built-in `RedpandaContainer`:

```python
from testcontainers.kafka import RedpandaContainer

with RedpandaContainer() as redpanda:
    bootstrap = redpanda.get_bootstrap_server()  # returns "localhost:<port>"
    monkeypatch.setenv("BUREAU_KAFKA_BOOTSTRAP_SERVERS", bootstrap)
    # reimport bureau.kafka_publisher to pick up new env var
```

No custom container class needed. Tests set `BUREAU_KAFKA_BOOTSTRAP_SERVERS` via monkeypatch and reimport `bureau.kafka_publisher` to pick up the new env state.

**Alternatives considered**: `docker-compose` fixture — requires daemon management outside pytest; less portable. Mock producer — loses integration coverage value.

---

## confluent-kafka and Python 3.14

**Decision**: Accept the C extension dependency; pin `confluent-kafka>=2.3`
**Rationale**: confluent-kafka 2.14.0 ships pre-built wheels for Linux x86_64/aarch64 and macOS arm64 including Python 3.14. No source build required on ubuntu-latest CI. GIL-free (free-threaded) support is incomplete in 2.x — importing confluent-kafka reverts to GIL mode, but bureau is single-threaded so this has no impact.

---

## Redpanda Local Dev

**Decision**: Single `docker run` one-liner in README
**Rationale**: Zero infrastructure complexity for local testing. No `docker-compose.yml` in the repo — keeps bureau's dependency footprint minimal.

```sh
docker run -d -p 9092:9092 --name bureau-kafka \
  redpandadata/redpanda:latest \
  redpanda start --smp 1 --overprovisioned
```

Consume events: `rpk topic consume bureau.runs` (Redpanda CLI) or any Kafka consumer.
