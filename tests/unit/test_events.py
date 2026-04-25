from __future__ import annotations

import importlib
import json
import sys

import pytest

from bureau import events


def test_emit_no_kwargs(capsys):
    events.emit("run.started")
    assert capsys.readouterr().out.strip() == "[bureau] run.started"


def test_emit_with_kwargs(capsys):
    events.emit("run.started", id="abc", phase="builder")
    out = capsys.readouterr().out.strip()
    assert "[bureau] run.started" in out
    assert "id=abc" in out
    assert "phase=builder" in out


def test_phase_context_manager_emits_started_and_completed(capsys):
    with events.phase("validate_spec"):
        pass
    out = capsys.readouterr().out
    assert "phase.started  phase=validate_spec" in out
    assert "phase.completed  phase=validate_spec" in out
    assert "duration=" in out


def test_phase_stub_flag_included_in_output(capsys):
    with events.phase("memory", stub=True):
        pass
    out = capsys.readouterr().out
    assert "stub=true" in out
    lines = out.strip().splitlines()
    assert len(lines) == 2
    assert all("stub=true" in ln for ln in lines)


# --- US2: text-mode regression tests ---


def test_text_mode_run_started_exact_format(capsys, monkeypatch):
    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    events.emit("run.started", id="run-abc", spec="/s", repo="/r")
    out = capsys.readouterr().out
    assert out == "[bureau] run.started  id=run-abc  spec=/s  repo=/r\n"


def test_text_mode_default_when_unset(monkeypatch):
    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    assert not events.is_cloudevents_mode()


def test_is_cloudevents_mode_false_by_default(monkeypatch):
    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    assert events.is_cloudevents_mode() is False


def test_is_cloudevents_mode_true_when_set(monkeypatch):
    # Module-level _FORMAT is already resolved; test the enum directly
    assert events.OutputFormat("cloudevents") == events.OutputFormat.CLOUDEVENTS


def test_invalid_format_raises_value_error():
    with pytest.raises(ValueError):
        events.OutputFormat("xml")


# --- US1: CloudEvents mode unit tests ---


def _reload_events_with_format(monkeypatch, fmt: str):
    """Reload the events module with a specific BUREAU_OUTPUT_FORMAT."""
    monkeypatch.setenv("BUREAU_OUTPUT_FORMAT", fmt)
    if "bureau.events" in sys.modules:
        del sys.modules["bureau.events"]
    mod = importlib.import_module("bureau.events")
    return mod


ALL_EVENTS = [
    ("run.started", {"id": "run-abc", "spec": "/s", "repo": "/r"}),
    ("run.completed", {"id": "run-abc", "pr": "https://github.com/x/y/pull/1", "duration": "5.0s"}),
    ("run.failed", {"id": "run-abc", "phase": "builder", "error": "boom"}),
    ("run.escalated", {"id": "run-abc", "phase": "builder", "reason": "BLOCKER"}),
    ("phase.started", {"phase": "builder"}),
    ("phase.completed", {"phase": "builder", "duration": "3.0s"}),
    ("ralph.started", {"phase": "builder", "round": 1}),
    ("ralph.attempt", {"phase": "builder", "round": 1, "attempt": 1, "result": "pass", "exit_code": 0}),
    ("ralph.completed", {"rounds": 1, "verdict": "pass"}),
    ("builder.tool", {"tool": "execute", "exit_code": 0}),
]


@pytest.mark.parametrize("event_name,kwargs", ALL_EVENTS)
def test_cloudevents_emit_valid_envelope(event_name, kwargs, capsys, monkeypatch):
    ev = _reload_events_with_format(monkeypatch, "cloudevents")
    ev.emit(event_name, **kwargs)
    # restore
    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    del sys.modules["bureau.events"]
    importlib.import_module("bureau.events")

    out = capsys.readouterr().out.strip()
    assert out, "Expected output on stdout"
    envelope = json.loads(out)
    assert envelope["specversion"] == "1.0"
    assert envelope["type"] == f"com.fancybread.bureau.{event_name}"
    assert envelope["datacontenttype"] == "application/json"
    assert isinstance(envelope["data"], dict)
    assert "id" in envelope
    assert "source" in envelope
    assert "time" in envelope


def test_cloudevents_source_updates_after_run_started(capsys, monkeypatch):
    ev = _reload_events_with_format(monkeypatch, "cloudevents")
    ev.emit("run.started", id="run-xyz", spec="/s", repo="/r")
    ev.emit("phase.started", phase="builder")

    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    del sys.modules["bureau.events"]
    importlib.import_module("bureau.events")

    lines = capsys.readouterr().out.strip().splitlines()
    started = json.loads(lines[0])
    phase_ev = json.loads(lines[1])
    assert "run-xyz" in started["source"]
    assert "run-xyz" in phase_ev["source"]
