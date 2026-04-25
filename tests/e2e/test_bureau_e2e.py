from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.e2e.conftest import SKIP_NO_KEY, SKIP_NO_REPO, run_bureau

pytestmark = [SKIP_NO_REPO, SKIP_NO_KEY]


def _assert_phase_order(stdout: str) -> None:
    expected_phases = [
        "validate_spec",
        "repo_analysis",
        "tasks_loader",
        "git_commit",
        "pr_create",
    ]
    started: dict[str, int] = {}
    completed: dict[str, int] = {}
    for i, line in enumerate(stdout.splitlines()):
        m_start = re.search(r"phase\.started\s+phase=(\S+)", line)
        if m_start:
            started[m_start.group(1)] = i
        m_done = re.search(r"phase\.completed\s+phase=(\S+)", line)
        if m_done:
            completed[m_done.group(1)] = i

    for phase in expected_phases:
        assert phase in started, f"phase.started missing for {phase}"
        assert phase in completed, f"phase.completed missing for {phase}"
        assert started[phase] < completed[phase], f"started after completed for {phase}"

    start_positions = [started[p] for p in expected_phases]
    assert start_positions == sorted(start_positions), "phases started out of order"


@pytest.mark.timeout(650)
def test_smoke_hello_world(bureau_test_repo):
    spec_path = str(Path(bureau_test_repo) / "specs" / "001-smoke-hello-world" / "spec.md")
    result = run_bureau(spec_path, bureau_test_repo)

    assert result.returncode == 0, (
        f"bureau exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "[bureau] run.completed" in result.stdout
    assert "https://github.com/" in result.stdout

    _assert_phase_order(result.stdout)

    ralph_lines = [ln for ln in result.stdout.splitlines() if "ralph.attempt" in ln]
    assert any("result=pass" in ln for ln in ralph_lines), "no ralph.attempt with result=pass found"

    completed_line = next((ln for ln in result.stdout.splitlines() if "run.completed" in ln), None)
    assert completed_line is not None
    assert "pr=" in completed_line
    assert "duration=" in completed_line


@pytest.mark.timeout(350)
@pytest.mark.xfail(
    strict=False,
    reason="Planner may complete spec 004 instead of escalating — AI behaviour is non-deterministic",
)
def test_escalation_missing_artifact(bureau_test_repo):
    spec_path = str(Path(bureau_test_repo) / "specs" / "004-escalation-missing-schema" / "spec.md")
    result = run_bureau(spec_path, bureau_test_repo, timeout=300)

    assert "[bureau] run.escalated" in result.stdout
    assert "https://github.com/" not in result.stdout
    assert "What happened" in result.stdout
    assert "What's needed" in result.stdout
