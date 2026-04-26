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
    prune_runs,
    resume_run,
    write_run_record,
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


# ---------------------------------------------------------------------------
# prune_runs
# ---------------------------------------------------------------------------


def _make_paused(tmp_path, spec_path: str):
    r = create_run(spec_path, str(tmp_path))
    r.status = RunStatus.PAUSED
    write_run_record(r)
    return r


def test_prune_dry_run_does_not_delete(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = _make_paused(tmp_path, "/nonexistent/spec.md")
    results = prune_runs(dry_run=True, missing_spec=True)
    assert len(results) == 1
    assert results[0].run_id == r.run_id
    assert results[0].deleted is False
    assert (tmp_path / "runs" / r.run_id).exists()


def test_prune_no_dry_run_deletes(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = _make_paused(tmp_path, "/nonexistent/spec.md")
    results = prune_runs(dry_run=False, missing_spec=True)
    assert results[0].deleted is True
    assert not (tmp_path / "runs" / r.run_id).exists()


def test_prune_missing_spec_only_matches_gone_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    real_spec = tmp_path / "spec.md"
    real_spec.write_text("# spec")
    keep = _make_paused(tmp_path, str(real_spec))
    drop = _make_paused(tmp_path, "/nonexistent/spec.md")
    results = prune_runs(dry_run=False, missing_spec=True)
    ids = {r.run_id for r in results}
    assert drop.run_id in ids
    assert keep.run_id not in ids


def test_prune_older_than_matches_by_age(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    from datetime import timedelta

    r = _make_paused(tmp_path, "/nonexistent/spec.md")
    # backdate updated_at to 10 days ago
    record = get_run(r.run_id)
    from datetime import datetime, timezone

    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    record.updated_at = old_time
    write_run_record(record)
    # re-set updated_at directly since write_run_record overwrites it
    import json

    rpath = tmp_path / "runs" / r.run_id / "run.json"
    data = json.loads(rpath.read_text())
    data["updated_at"] = old_time
    rpath.write_text(json.dumps(data))

    results = prune_runs(dry_run=True, older_than_days=5)
    assert any(res.run_id == r.run_id for res in results)


def test_prune_status_filter_excludes_non_matching(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    r = create_run("/nonexistent/spec.md", str(tmp_path))  # status=running
    results = prune_runs(dry_run=True, status_filter=RunStatus.PAUSED, missing_spec=True)
    assert not any(res.run_id == r.run_id for res in results)


def test_prune_returns_empty_when_no_match(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
    real_spec = tmp_path / "spec.md"
    real_spec.write_text("# spec")
    _make_paused(tmp_path, str(real_spec))
    results = prune_runs(dry_run=True, missing_spec=True)
    assert results == []
