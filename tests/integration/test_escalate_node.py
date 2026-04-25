from __future__ import annotations

import importlib
import json
import sys
from unittest.mock import patch

from bureau.nodes.escalate import escalate_node
from bureau.state import Escalation, EscalationReason, Phase, make_initial_state


def _make_state(**overrides):
    state = make_initial_state("run-esc-001", "specs/001/spec.md", "/tmp/repo")
    return {**state, **overrides}


def _make_escalation(run_id: str = "run-esc-001") -> Escalation:
    return Escalation(
        run_id=run_id,
        phase=Phase.BUILDER,
        reason=EscalationReason.RALPH_EXHAUSTED,
        what_happened="Tests failed after 3 attempts.",
        what_is_needed="Fix the implementation.",
        options=["Option A", "Option B"],
        timestamp="2026-01-01T00:00:00+00:00",
    )


def test_escalate_node_sets_phase(tmp_path):
    state = _make_state(escalations=[_make_escalation()])
    with patch("bureau.nodes.escalate.get_run", side_effect=Exception("no db")):
        result = escalate_node(state)
    assert result["phase"] == Phase.ESCALATE


def test_escalate_node_no_escalations(tmp_path):
    state = _make_state(escalations=[])
    with patch("bureau.nodes.escalate.get_run", side_effect=Exception("no db")):
        result = escalate_node(state)
    assert result["phase"] == Phase.ESCALATE


def test_escalate_node_writes_run_record(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    from bureau.run_manager import create_run

    record = create_run("specs/001/spec.md", "/tmp/repo")
    state = _make_state(run_id=record.run_id, escalations=[_make_escalation(record.run_id)])
    escalate_node(state)
    from bureau.run_manager import get_run
    from bureau.state import RunStatus

    updated = get_run(record.run_id)
    assert updated.status == RunStatus.PAUSED


# --- US3: CloudEvents escalation tests ---


def _reload_events_with_format(monkeypatch, fmt: str):
    monkeypatch.setenv("BUREAU_OUTPUT_FORMAT", fmt)
    for mod in list(sys.modules.keys()):
        if "bureau.events" in mod or "bureau.nodes.escalate" in mod:
            del sys.modules[mod]
    importlib.import_module("bureau.events")
    importlib.import_module("bureau.nodes.escalate")


def _restore_events(monkeypatch):
    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    for mod in list(sys.modules.keys()):
        if "bureau.events" in mod or "bureau.nodes.escalate" in mod:
            del sys.modules[mod]
    importlib.import_module("bureau.events")
    importlib.import_module("bureau.nodes.escalate")


def test_escalation_cloudevents_structured_fields(capsys, monkeypatch):
    _reload_events_with_format(monkeypatch, "cloudevents")
    from bureau.nodes.escalate import escalate_node as esc_node

    state = _make_state(escalations=[_make_escalation()])
    with patch("bureau.nodes.escalate.get_run", side_effect=Exception("no db")):
        esc_node(state)

    _restore_events(monkeypatch)

    lines = [ln for ln in capsys.readouterr().out.strip().splitlines() if ln]
    assert len(lines) == 1, f"Expected 1 NDJSON line, got: {lines}"
    envelope = json.loads(lines[0])
    assert envelope["type"] == "com.fancybread.bureau.run.escalated"
    data = envelope["data"]
    assert "what_happened" in data
    assert "what_is_needed" in data
    assert data["what_happened"] == "Tests failed after 3 attempts."
    assert data["what_is_needed"] == "Fix the implementation."
    assert data["reason"] == "RALPH_EXHAUSTED"


def test_escalation_text_mode_prints_raw_lines(capsys, monkeypatch):
    monkeypatch.delenv("BUREAU_OUTPUT_FORMAT", raising=False)
    # Use the already-loaded text-mode escalate_node
    from bureau.nodes.escalate import escalate_node as esc_node

    state = _make_state(escalations=[_make_escalation()])
    with patch("bureau.nodes.escalate.get_run", side_effect=Exception("no db")):
        esc_node(state)

    out = capsys.readouterr().out
    assert "[bureau] run.escalated" in out
    assert "What happened:" in out
    assert "What's needed:" in out
    # In text mode, what_happened appears as k=v in the emit line, not as structured JSON
    assert "what_happened=Tests failed" in out


def test_escalation_cloudevents_no_raw_print_lines(capsys, monkeypatch):
    _reload_events_with_format(monkeypatch, "cloudevents")
    from bureau.nodes.escalate import escalate_node as esc_node

    state = _make_state(escalations=[_make_escalation()])
    with patch("bureau.nodes.escalate.get_run", side_effect=Exception("no db")):
        esc_node(state)

    _restore_events(monkeypatch)

    out = capsys.readouterr().out
    assert "What happened:" not in out
    assert "What's needed:" not in out
    assert "Options:" not in out
    # Verify the output is valid JSON (no non-JSON lines)
    for line in out.strip().splitlines():
        json.loads(line)  # will raise if any line is not JSON
