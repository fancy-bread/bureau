from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


SPEC_PATH = str(
    Path(__file__).parents[2]
    / "specs"
    / "001-autonomous-runtime-core"
    / "spec.md"
)

_BUREAU_CONFIG = """
[runtime]
language    = "python"
base_image  = "python:3.12-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"
"""


@pytest.fixture()
def target_repo(tmp_path: Path) -> Path:
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(_BUREAU_CONFIG)
    return tmp_path


def _bureau_exe() -> str:
    return str(Path(sys.executable).parent / "bureau")


def _run_bureau(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bureau_exe(), *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[2],
    )


def test_e2e_stub_run_completes(target_repo: Path) -> None:
    result = _run_bureau("run", SPEC_PATH, "--repo", str(target_repo))
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "run.started" in output
    for phase in ("validate_spec", "repo_analysis", "memory", "planner", "builder", "critic", "pr_create"):
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
