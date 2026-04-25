from __future__ import annotations

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
