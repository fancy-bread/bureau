from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch


def _reload_module(monkeypatch, **env_overrides):
    """Reload kafka_publisher with a clean environment."""
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    # Remove module from sys.modules so _init() runs fresh on import
    sys.modules.pop("bureau.kafka_publisher", None)
    import bureau.kafka_publisher as mod

    return mod


def _reload_module_no_kafka(monkeypatch):
    monkeypatch.delenv("BUREAU_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    sys.modules.pop("bureau.kafka_publisher", None)
    import bureau.kafka_publisher as mod

    return mod


# ---------------------------------------------------------------------------
# is_kafka_enabled
# ---------------------------------------------------------------------------


def test_is_kafka_enabled_false_when_env_absent(monkeypatch):
    mod = _reload_module_no_kafka(monkeypatch)
    assert mod.is_kafka_enabled() is False


def test_is_kafka_enabled_false_when_env_empty(monkeypatch):
    mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="")
    assert mod.is_kafka_enabled() is False


def test_is_kafka_enabled_true_when_producer_set(monkeypatch):
    fake_producer = MagicMock()
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")
    assert mod.is_kafka_enabled() is True


# ---------------------------------------------------------------------------
# publish — no-op when disabled
# ---------------------------------------------------------------------------


def test_publish_noop_when_disabled(monkeypatch):
    mod = _reload_module_no_kafka(monkeypatch)
    # should not raise even though there's no producer
    mod.publish("run.started", "run-123", id="run-123")


# ---------------------------------------------------------------------------
# publish — calls producer.produce with correct args
# ---------------------------------------------------------------------------


def test_publish_calls_produce_with_correct_topic_and_key(monkeypatch):
    fake_producer = MagicMock()
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(
            monkeypatch,
            BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092",
            BUREAU_KAFKA_TOPIC="my.topic",
        )
    mod.publish("run.started", "run-abc", id="run-abc", spec="specs/001/spec.md")

    assert fake_producer.produce.call_count == 1
    call_kwargs = fake_producer.produce.call_args
    assert call_kwargs[0][0] == "my.topic"
    assert call_kwargs[1]["key"] == b"run-abc"


def test_publish_value_is_valid_cloudevents_json(monkeypatch):
    fake_producer = MagicMock()
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")
    mod.publish("run.started", "run-xyz", id="run-xyz")

    value = fake_producer.produce.call_args[1]["value"]
    envelope = json.loads(value)
    assert envelope["specversion"] == "1.0"
    assert envelope["type"] == "com.fancybread.bureau.run.started"
    assert "run-xyz" in envelope["source"]
    assert envelope["datacontenttype"] == "application/json"
    assert "id" in envelope
    assert "time" in envelope
    assert envelope["data"]["id"] == "run-xyz"


def test_publish_default_topic_is_bureau_runs(monkeypatch):
    fake_producer = MagicMock()
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    monkeypatch.delenv("BUREAU_KAFKA_TOPIC", raising=False)
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")
    mod.publish("phase.started", "run-1")

    assert fake_producer.produce.call_args[0][0] == "bureau.runs"


# ---------------------------------------------------------------------------
# publish — exception handling (US2)
# ---------------------------------------------------------------------------


def test_publish_catches_buffer_error_and_logs_stderr(monkeypatch, capsys):
    fake_producer = MagicMock()
    fake_producer.produce.side_effect = BufferError("queue full")
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")

    mod.publish("run.started", "run-1")

    captured = capsys.readouterr()
    assert "[bureau/kafka] publish failed:" in captured.err


def test_publish_catches_kafka_exception_and_logs_stderr(monkeypatch, capsys):
    fake_producer = MagicMock()
    fake_kafka_exc = type("KafkaException", (Exception,), {})
    fake_producer.produce.side_effect = fake_kafka_exc("broker unavailable")
    confluent_mock = MagicMock(
        Producer=MagicMock(return_value=fake_producer),
        KafkaException=fake_kafka_exc,
    )
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")

    mod.publish("run.started", "run-1")

    captured = capsys.readouterr()
    assert "[bureau/kafka] publish failed:" in captured.err


def test_publish_never_raises(monkeypatch):
    fake_producer = MagicMock()
    fake_producer.produce.side_effect = RuntimeError("unexpected")
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")

    # should not propagate
    mod.publish("run.started", "run-1")


# ---------------------------------------------------------------------------
# instance ID (US3)
# ---------------------------------------------------------------------------


def test_instance_id_from_env(monkeypatch):
    fake_producer = MagicMock()
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(
            monkeypatch,
            BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092",
            BUREAU_INSTANCE_ID="test-worker",
        )
    mod.publish("run.started", "run-42")

    value = json.loads(fake_producer.produce.call_args[1]["value"])
    assert "urn:bureau:instance:test-worker:run:run-42" == value["source"]


def test_instance_id_defaults_to_uuid_when_unset(monkeypatch):
    import re

    fake_producer = MagicMock()
    confluent_mock = MagicMock(Producer=MagicMock(return_value=fake_producer))
    monkeypatch.delenv("BUREAU_INSTANCE_ID", raising=False)
    with patch.dict("sys.modules", {"confluent_kafka": confluent_mock}):
        mod = _reload_module(monkeypatch, BUREAU_KAFKA_BOOTSTRAP_SERVERS="localhost:9092")
    mod.publish("run.started", "run-99")

    value = json.loads(fake_producer.produce.call_args[1]["value"])
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    assert re.search(uuid_pattern, value["source"])
