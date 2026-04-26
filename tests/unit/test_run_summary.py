from __future__ import annotations

import json
from unittest.mock import patch

from bureau.run_manager import write_run_summary


def _make_state(
    run_id: str = "run-test0001",
    ralph_rounds: list | None = None,
    build_attempts: list | None = None,
    reviewer_findings: list | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "spec_path": "specs/011/spec.md",
        "ralph_rounds": ralph_rounds or [],
        "build_attempts": build_attempts or [],
        "reviewer_findings": reviewer_findings or [],
    }


def _make_round(files: list[str], passed: bool = True) -> dict:
    ts_start = "2026-04-26T03:00:00+00:00"
    ts_end = "2026-04-26T03:00:45+00:00"
    return {
        "round": 0,
        "build_attempts": [{"timestamp": ts_start, "files_changed": files, "passed": passed}],
        "reviewer_verdict": "pass" if passed else "revise",
        "reviewer_findings": [],
        "completed_at": ts_end,
    }


def test_write_run_summary_pass(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    rr = _make_round(["bureau/run_manager.py", "tests/unit/test_run_summary.py"])
    state = _make_state(
        ralph_rounds=[rr],
        build_attempts=rr["build_attempts"],
        reviewer_findings=[{"type": "requirement", "ref_id": "FR-001", "verdict": "met"}],
    )

    write_run_summary(state, "pass")

    out = json.loads((tmp_path / "runs" / "run-test0001" / "run-summary.json").read_text())
    assert out["run_id"] == "run-test0001"
    assert out["final_verdict"] == "pass"
    assert set(out["files_changed"]) == {"bureau/run_manager.py", "tests/unit/test_run_summary.py"}
    assert len(out["attempt_durations"]) == 1
    assert abs(out["attempt_durations"][0] - 45.0) < 1.0
    assert out["ralph_rounds"] == 1
    assert len(out["reviewer_findings"]) == 1


def test_write_run_summary_escalated(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    state = _make_state()
    write_run_summary(state, "escalated")
    out = json.loads((tmp_path / "runs" / "run-test0001" / "run-summary.json").read_text())
    assert out["final_verdict"] == "escalated"


def test_write_run_summary_failed_empty_state(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    state = _make_state()
    write_run_summary(state, "failed")
    out = json.loads((tmp_path / "runs" / "run-test0001" / "run-summary.json").read_text())
    assert out["final_verdict"] == "failed"
    assert out["files_changed"] == []
    assert out["attempt_durations"] == []
    assert out["ralph_rounds"] == 0


def test_write_run_summary_deduplicates_files(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    rr1 = _make_round(["a.py", "b.py"])
    rr2 = _make_round(["b.py", "c.py"])
    state = _make_state(
        ralph_rounds=[rr1, rr2],
        build_attempts=rr1["build_attempts"] + rr2["build_attempts"],
    )
    write_run_summary(state, "pass")
    out = json.loads((tmp_path / "runs" / "run-test0001" / "run-summary.json").read_text())
    assert set(out["files_changed"]) == {"a.py", "b.py", "c.py"}


def test_write_run_summary_overwrites_existing(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    state = _make_state()
    write_run_summary(state, "escalated")
    write_run_summary(state, "pass")
    out = json.loads((tmp_path / "runs" / "run-test0001" / "run-summary.json").read_text())
    assert out["final_verdict"] == "pass"


def test_write_run_summary_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    state = _make_state()
    with patch("os.replace", side_effect=OSError("disk full")):
        write_run_summary(state, "pass")


def test_write_run_summary_skips_bad_timestamps(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    rr = {
        "round": 0,
        "build_attempts": [{"timestamp": "not-a-date", "files_changed": []}],
        "reviewer_verdict": "pass",
        "reviewer_findings": [],
        "completed_at": "also-not-a-date",
    }
    state = _make_state(ralph_rounds=[rr], build_attempts=rr["build_attempts"])
    write_run_summary(state, "pass")
    out = json.loads((tmp_path / "runs" / "run-test0001" / "run-summary.json").read_text())
    assert out["attempt_durations"] == []
