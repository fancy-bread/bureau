from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bureau.state import Phase, RunRecord, RunStatus


class RunNotFoundError(Exception):
    pass


class RunNotPausedError(Exception):
    pass


def _runs_dir() -> Path:
    return Path.home() / ".bureau" / "runs"


def _run_dir(run_id: str) -> Path:
    return _runs_dir() / run_id


def _record_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    return "run-" + uuid.uuid4().hex[:8]


def create_run(spec_path: str, repo_path: str) -> RunRecord:
    run_id = new_run_id()
    _run_dir(run_id).mkdir(parents=True, exist_ok=True)
    record = RunRecord(
        run_id=run_id,
        spec_path=spec_path,
        repo_path=repo_path,
        status=RunStatus.RUNNING,
        current_phase=Phase.VALIDATE_SPEC,
        started_at=_now(),
        updated_at=_now(),
    )
    write_run_record(record)
    return record


def write_run_record(record: RunRecord) -> None:
    record.updated_at = _now()
    _record_path(record.run_id).write_text(
        json.dumps(record.__dict__, indent=2, default=str)
    )


def get_run(run_id: str) -> RunRecord:
    path = _record_path(run_id)
    if not path.exists():
        raise RunNotFoundError(f"Run not found: {run_id}")
    data = json.loads(path.read_text())
    return RunRecord(**data)


def list_runs(status_filter: Optional[str] = None) -> list[RunRecord]:
    runs_dir = _runs_dir()
    if not runs_dir.exists():
        return []
    records = []
    for run_dir in sorted(runs_dir.iterdir()):
        record_path = run_dir / "run.json"
        if not record_path.exists():
            continue
        try:
            record = get_run(run_dir.name)
            if status_filter is None or record.status == status_filter:
                records.append(record)
        except Exception:
            continue
    return records


def abort_run(run_id: str) -> None:
    record = get_run(run_id)
    record.status = RunStatus.ABORTED
    write_run_record(record)


def resume_run(run_id: str, response: str = "") -> RunRecord:
    record = get_run(run_id)
    if record.status != RunStatus.PAUSED:
        raise RunNotPausedError(
            f"Run {run_id} is not paused (status: {record.status})"
        )
    record.status = RunStatus.RUNNING
    write_run_record(record)
    return record


def init_repo(repo_path: str) -> str:
    """Scaffold .bureau/config.toml in repo_path. Returns 'created' or 'exists'."""
    bureau_dir = Path(repo_path) / ".bureau"
    config_path = bureau_dir / "config.toml"
    if config_path.exists():
        return "exists"
    bureau_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "[runtime]\n"
        'language    = "FILL_IN"          # e.g. python, typescript, go\n'
        'base_image  = "FILL_IN"          # e.g. python:3.12-slim, node:20-slim\n'
        'install_cmd = "FILL_IN"          # e.g. pip install -e ., npm ci\n'
        'test_cmd    = "FILL_IN"          # e.g. pytest, npm test\n'
        'build_cmd   = ""\n'
        'lint_cmd    = ""\n'
        "\n"
        "[bureau]\n"
        "# constitution = \".bureau/constitution.md\""
        "  # uncomment to use a project-specific constitution\n"
    )
    return "created"
