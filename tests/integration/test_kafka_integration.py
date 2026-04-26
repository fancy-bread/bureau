from __future__ import annotations

import json
import sys
import time

import pytest

pytest.importorskip("testcontainers")
pytest.importorskip("confluent_kafka")


@pytest.fixture(scope="module")
def redpanda():
    from confluent_kafka.admin import AdminClient
    from testcontainers.kafka import RedpandaContainer

    with RedpandaContainer() as container:
        bootstrap = container.get_bootstrap_server()
        # Poll until the broker accepts connections (up to 30s)
        admin = AdminClient({"bootstrap.servers": bootstrap, "socket.timeout.ms": "2000"})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                admin.list_topics(timeout=2)
                break
            except Exception:
                time.sleep(0.5)
        admin.poll(0)
        yield container


def _reload_publisher(monkeypatch, bootstrap_servers: str, **extra_env):
    monkeypatch.setenv("BUREAU_KAFKA_BOOTSTRAP_SERVERS", bootstrap_servers)
    for k, v in extra_env.items():
        monkeypatch.setenv(k, v)
    sys.modules.pop("bureau.kafka_publisher", None)
    import bureau.kafka_publisher as mod

    return mod


def _consume_matching(
    bootstrap_servers: str,
    topic: str,
    group_id: str,
    run_id: str,
    timeout: float = 15.0,
) -> dict:
    """Consume from earliest offset; return the first envelope whose source contains run_id."""
    from confluent_kafka import Consumer

    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([topic])
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            msg = consumer.poll(timeout=1.0)
            if msg is not None:
                assert msg.error() is None, f"Consumer error: {msg.error()}"
                envelope = json.loads(msg.value())
                if run_id in envelope.get("source", "") or run_id in str(envelope.get("data", {})):
                    return envelope
        pytest.fail(f"No message for run_id='{run_id}' in topic '{topic}' within {timeout}s")
    finally:
        consumer.close()


# ---------------------------------------------------------------------------
# US1: publisher activates and produces valid CloudEvents envelope
# ---------------------------------------------------------------------------


def test_publish_produces_valid_cloudevents_envelope(monkeypatch, redpanda):
    bootstrap = redpanda.get_bootstrap_server()
    mod = _reload_publisher(monkeypatch, bootstrap)

    assert mod.is_kafka_enabled()
    mod.publish("run.started", "run-int-001", id="run-int-001", spec="specs/test/spec.md")
    unflushed = mod._producer.flush(timeout=15)
    assert unflushed == 0, f"{unflushed} message(s) still in queue after flush"

    envelope = _consume_matching(
        bootstrap, "bureau.runs", group_id="grp-us1-default", run_id="run-int-001"
    )
    assert envelope["specversion"] == "1.0"
    assert envelope["type"] == "com.fancybread.bureau.run.started"
    assert "run-int-001" in envelope["source"]
    assert envelope["datacontenttype"] == "application/json"
    assert "id" in envelope
    assert "time" in envelope
    assert envelope["data"]["id"] == "run-int-001"


# ---------------------------------------------------------------------------
# US2: unreachable broker does not raise
# ---------------------------------------------------------------------------


def test_unreachable_broker_does_not_raise(monkeypatch):
    monkeypatch.delenv("BUREAU_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    sys.modules.pop("bureau.kafka_publisher", None)
    mod = _reload_publisher(monkeypatch, "localhost:19999")

    mod.publish("run.started", "run-unreachable", id="run-unreachable")
    if mod._producer is not None:
        mod._producer.flush(timeout=0)


# ---------------------------------------------------------------------------
# US3: instance ID env appears in source URI
# ---------------------------------------------------------------------------


def test_instance_id_env_appears_in_source(monkeypatch, redpanda):
    bootstrap = redpanda.get_bootstrap_server()
    mod = _reload_publisher(monkeypatch, bootstrap, BUREAU_INSTANCE_ID="ci-worker-7")

    mod.publish("run.started", "run-int-003", id="run-int-003")
    unflushed = mod._producer.flush(timeout=15)
    assert unflushed == 0, f"{unflushed} message(s) still in queue after flush"

    envelope = _consume_matching(
        bootstrap, "bureau.runs", group_id="grp-us3-instance", run_id="run-int-003"
    )
    assert envelope["source"] == "urn:bureau:instance:ci-worker-7:run:run-int-003"
