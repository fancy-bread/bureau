from __future__ import annotations

import pytest

from bureau.run_manager import (
    RunNotFoundError,
    RunNotPausedError,
    abort_run,
    create_run,
    get_run,
    init_repo,
    list_runs,
    new_run_id,
    resume_run,
)
from bureau.state import RunStatus


def test_new_run_id_format():
    run_id = new_run_id()
    assert run_id.startswith("run-")
    assert len(run_id) == 12


def test_create_and_get_run(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    record = create_run("specs/001/spec.md", str(tmp_path))
    fetched = get_run(record.run_id)
    assert fetched.run_id == record.run_id
    assert fetched.spec_path == "specs/001/spec.md"
    assert fetched.status == RunStatus.RUNNING


def test_get_run_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    with pytest.raises(RunNotFoundError):
        get_run("run-doesnotexist")


def test_list_runs_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    assert list_runs() == []


def test_list_runs_returns_records(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r1 = create_run("specs/001/spec.md", str(tmp_path))
    r2 = create_run("specs/002/spec.md", str(tmp_path))
    runs = list_runs()
    ids = {r.run_id for r in runs}
    assert r1.run_id in ids
    assert r2.run_id in ids


def test_list_runs_status_filter(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = create_run("specs/001/spec.md", str(tmp_path))
    abort_run(r.run_id)
    assert list_runs(status_filter=RunStatus.RUNNING) == []
    aborted = list_runs(status_filter=RunStatus.ABORTED)
    assert any(x.run_id == r.run_id for x in aborted)


def test_abort_run(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = create_run("specs/001/spec.md", str(tmp_path))
    abort_run(r.run_id)
    assert get_run(r.run_id).status == RunStatus.ABORTED


def test_resume_run(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = create_run("specs/001/spec.md", str(tmp_path))
    r.status = RunStatus.PAUSED
    from bureau.run_manager import write_run_record
    write_run_record(r)
    resumed = resume_run(r.run_id)
    assert resumed.status == RunStatus.RUNNING


def test_resume_not_paused_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = create_run("specs/001/spec.md", str(tmp_path))
    with pytest.raises(RunNotPausedError):
        resume_run(r.run_id)


def test_init_repo_creates_config(tmp_path):
    result = init_repo(str(tmp_path))
    assert result == "created"
    assert (tmp_path / ".bureau" / "config.toml").exists()


def test_init_repo_already_exists(tmp_path):
    init_repo(str(tmp_path))
    result = init_repo(str(tmp_path))
    assert result == "exists"
