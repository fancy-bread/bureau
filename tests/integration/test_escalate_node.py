from __future__ import annotations

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
