from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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
    _record_path(record.run_id).write_text(json.dumps(record.__dict__, indent=2, default=str))


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
        except Exception as exc:
            print(f"[bureau] skipping unreadable run {run_dir.name}: {exc}", file=sys.stderr)
            continue
    return records


def abort_run(run_id: str) -> None:
    record = get_run(run_id)
    record.status = RunStatus.ABORTED
    write_run_record(record)


def resume_run(run_id: str, response: str = "") -> RunRecord:
    record = get_run(run_id)
    if record.status != RunStatus.PAUSED:
        raise RunNotPausedError(f"Run {run_id} is not paused (status: {record.status})")
    record.status = RunStatus.RUNNING
    write_run_record(record)
    return record


@dataclass
class PruneResult:
    run_id: str
    reason: str
    deleted: bool


def prune_runs(
    *,
    dry_run: bool = True,
    older_than_days: Optional[int] = None,
    status_filter: Optional[str] = None,
    missing_spec: bool = False,
) -> list[PruneResult]:
    """Delete run directories matching the given criteria. Returns one PruneResult per candidate."""
    results: list[PruneResult] = []
    now = datetime.now(timezone.utc)

    for record in list_runs():
        reasons: list[str] = []

        if status_filter and record.status != status_filter:
            continue

        if missing_spec and not Path(record.spec_path).exists():
            reasons.append("spec path no longer exists")

        if older_than_days is not None:
            try:
                updated = datetime.fromisoformat(record.updated_at)
                age_days = (now - updated).days
                if age_days >= older_than_days:
                    reasons.append(f"last updated {age_days}d ago")
            except (ValueError, TypeError):
                pass

        if not reasons:
            continue

        deleted = False
        if not dry_run:
            run_path = _run_dir(record.run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
                deleted = True

        results.append(PruneResult(run_id=record.run_id, reason="; ".join(reasons), deleted=deleted))

    return results


def write_run_summary(state: dict[str, Any], final_verdict: str) -> None:
    """Write run-summary.json to the run directory. Never raises."""
    try:
        run_id = state.get("run_id", "unknown")
        build_attempts = state.get("build_attempts", [])
        ralph_rounds = state.get("ralph_rounds", [])

        seen: dict[str, None] = {}
        for attempt in build_attempts:
            for f in attempt.get("files_changed", []):
                seen[f] = None
        files_changed = list(seen)

        attempt_durations: list[float] = []
        for rr in ralph_rounds:
            try:
                completed_at = datetime.fromisoformat(rr["completed_at"])
                attempts = rr.get("build_attempts", [])
                if attempts:
                    started_at = datetime.fromisoformat(attempts[0]["timestamp"])
                    attempt_durations.append((completed_at - started_at).total_seconds())
            except (KeyError, ValueError, TypeError):
                pass

        try:
            record = get_run(run_id)
            status = str(record.status)
            spec_path = record.spec_path
        except Exception:
            status = state.get("status", "unknown")
            spec_path = state.get("spec_path", "")

        payload = {
            "run_id": run_id,
            "status": status,
            "spec_path": spec_path,
            "ralph_rounds": len(ralph_rounds),
            "reviewer_findings": state.get("reviewer_findings", []),
            "files_changed": files_changed,
            "attempt_durations": attempt_durations,
            "final_verdict": final_verdict,
            "completed_at": _now(),
        }

        run_dir = _run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        tmp = run_dir / "run-summary.json.tmp"
        tmp.write_text(json.dumps(payload, indent=2, default=str))
        os.replace(tmp, run_dir / "run-summary.json")
    except Exception as e:
        print(f"[bureau] run-summary write failed: {e}", file=sys.stderr)


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
        '# constitution = ".bureau/constitution.md"'
        "  # uncomment to use a project-specific constitution\n"
    )
    return "created"
