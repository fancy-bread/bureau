from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SPEC_PATH = str(Path(__file__).parents[2] / "specs" / "001-autonomous-runtime-core" / "spec.md")

_MINIMAL_SPEC = """\
# Minimal Test Spec

**Feature Branch**: `test-branch`
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Basic feature (Priority: P1)

A user does something useful.

**Acceptance Scenarios**:

1. **Given** a user, **When** they act, **Then** it works.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST do the thing.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The thing is done.
"""

_BUREAU_CONFIG = """
[runtime]
language    = "python"
base_image  = "python:3.12-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"
"""


_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "t@t.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "t@t.com",
}


@pytest.fixture()
def target_repo(tmp_path: Path) -> Path:
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(_BUREAU_CONFIG)
    return tmp_path


@pytest.fixture()
def clean_git_repo(tmp_path: Path) -> Path:
    """A clean git repo with .bureau/config.toml committed — passes the dirty-repo check."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    bureau_dir = repo_dir / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(_BUREAU_CONFIG)
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, env=_GIT_ENV)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_dir, capture_output=True, env=_GIT_ENV,
    )
    return repo_dir


def _bureau_exe() -> str:
    return str(Path(sys.executable).parent / "bureau")


def _run_bureau(*args: str, api_key: str = "sk-ant-test-dummy") -> subprocess.CompletedProcess[str]:
    import os

    env = {**os.environ, "ANTHROPIC_API_KEY": api_key}
    return subprocess.run(
        [_bureau_exe(), *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[2],
        env=env,
    )


def test_tasks_missing_escalates(clean_git_repo: Path, tmp_path: Path) -> None:
    spec_folder = tmp_path / "spec-folder"
    spec_folder.mkdir()
    (spec_folder / "spec.md").write_text(_MINIMAL_SPEC)
    result = _run_bureau("run", str(spec_folder), "--repo", str(clean_git_repo))
    assert "TASKS_MISSING" in result.stdout


def test_tasks_complete_escalates(clean_git_repo: Path, tmp_path: Path) -> None:
    spec_folder = tmp_path / "spec-folder"
    spec_folder.mkdir()
    (spec_folder / "spec.md").write_text(_MINIMAL_SPEC)
    (spec_folder / "tasks.md").write_text("- [x] T001 Already done\n- [x] T002 Also done\n")
    result = _run_bureau("run", str(spec_folder), "--repo", str(clean_git_repo))
    assert "TASKS_COMPLETE" in result.stdout


def test_file_path_invocation_resolves_tasks(clean_git_repo: Path, tmp_path: Path) -> None:
    spec_folder = tmp_path / "spec-folder"
    spec_folder.mkdir()
    spec_file = spec_folder / "spec.md"
    spec_file.write_text(_MINIMAL_SPEC)
    (spec_folder / "tasks.md").write_text("- [ ] T001 A real task\n")
    result = _run_bureau("run", str(spec_file), "--repo", str(clean_git_repo))
    assert "TASKS_MISSING" not in result.stdout
    assert "TASKS_COMPLETE" not in result.stdout


def test_malformed_tasks_escalates(clean_git_repo: Path, tmp_path: Path) -> None:
    spec_folder = tmp_path / "spec-folder"
    spec_folder.mkdir()
    (spec_folder / "spec.md").write_text(_MINIMAL_SPEC)
    (spec_folder / "tasks.md").write_text("# Tasks\n\nJust prose, no checkboxes here.\n")
    result = _run_bureau("run", str(spec_folder), "--repo", str(clean_git_repo))
    assert "TASKS_MISSING" in result.stdout


@pytest.mark.skip(reason="Stub-era E2E test; real persona nodes require Anthropic API + gh CLI")
def test_e2e_stub_run_completes(target_repo: Path) -> None:
    result = _run_bureau("run", SPEC_PATH, "--repo", str(target_repo))
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "run.started" in output
    phases = ("validate_spec", "repo_analysis", "memory", "planner", "builder", "critic", "pr_create")
    for phase in phases:
        assert f"phase.started  phase={phase}" in output, f"Missing phase.started for {phase}"
        assert f"phase.completed  phase={phase}" in output, f"Missing phase.completed for {phase}"
    assert "run.completed" in output


def test_spec_with_needs_clarification_is_rejected(target_repo: Path, tmp_path: Path) -> None:
    bad_spec = tmp_path / "spec.md"
    bad_spec.write_text(
        "# Bad Spec\n\n"
        "## User Scenarios & Testing\n### Story 1 (Priority: P1)\nA story.\n\n"
        "## Requirements\n### Functional Requirements\n"
        "- **FR-001**: System MUST [NEEDS CLARIFICATION: undefined]\n\n"
        "## Success Criteria\n### Measurable Outcomes\n- SC-001: done\n"
    )
    result = _run_bureau("run", str(bad_spec), "--repo", str(target_repo))
    assert "SPEC_INVALID" in result.stdout or "NEEDS CLARIFICATION" in result.stdout


def test_missing_bureau_config_escalates(tmp_path: Path) -> None:
    result = _run_bureau("run", SPEC_PATH, "--repo", str(tmp_path))
    assert "CONFIG_MISSING" in result.stdout or "config.toml" in result.stdout.lower()


def test_resume_unknown_run_id_exits_with_error() -> None:
    result = _run_bureau("resume", "run-00000000")
    assert result.returncode == 1
    assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()


def test_dirty_repo_escalates(tmp_path: Path) -> None:
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(_BUREAU_CONFIG)

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        capture_output=True,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "t@t.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "t@t.com",
        },
    )
    (tmp_path / "dirty.txt").write_text("dirty\n")

    result = _run_bureau("run", SPEC_PATH, "--repo", str(tmp_path))
    assert "DIRTY_REPO" in result.stdout


@pytest.mark.skip(reason="Depends on stub-era E2E full run completing; requires Anthropic API + gh CLI")
def test_resume_completed_run_exits_with_error(target_repo: Path) -> None:
    run_result = _run_bureau("run", SPEC_PATH, "--repo", str(target_repo))
    assert run_result.returncode == 0, run_result.stderr

    # Extract run ID from the run.started event line
    run_id = None
    for line in run_result.stdout.splitlines():
        if "run.started" in line and "id=" in line:
            for part in line.split():
                if part.startswith("id="):
                    run_id = part[3:]
                    break
    assert run_id is not None, f"Could not parse run_id from output: {run_result.stdout}"

    result = _run_bureau("resume", run_id)
    assert result.returncode == 1
    combined = result.stdout.lower() + result.stderr.lower()
    assert "not paused" in combined or "paused" in combined
