from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.e2e.conftest import SKIP_NO_KEY, SKIP_NO_REPO, run_bureau

pytestmark = [SKIP_NO_REPO, SKIP_NO_KEY]


def _is_cloudevents(stdout: str) -> bool:
    first = stdout.strip().splitlines()[0] if stdout.strip() else ""
    try:
        obj = json.loads(first)
        return obj.get("specversion") == "1.0"
    except (json.JSONDecodeError, AttributeError):
        return False


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
        if _is_cloudevents(stdout):
            try:
                obj = json.loads(line)
                event_type = obj.get("type", "")
                phase = obj.get("data", {}).get("phase", "")
                if not phase:
                    continue
                if event_type.endswith("phase.started"):
                    started[phase] = i
                elif event_type.endswith("phase.completed"):
                    completed[phase] = i
            except (json.JSONDecodeError, AttributeError):
                continue
        else:
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

    # run.completed present regardless of format
    assert "run.completed" in result.stdout
    # PR URL always present in data/output
    assert "https://github.com/" in result.stdout

    _assert_phase_order(result.stdout)

    # ralph.attempt with a passing result
    ralph_lines = [ln for ln in result.stdout.splitlines() if "ralph.attempt" in ln]
    assert ralph_lines, "no ralph.attempt lines found"
    if _is_cloudevents(result.stdout):
        assert any(json.loads(ln).get("data", {}).get("result") == "pass" for ln in ralph_lines), (
            "no ralph.attempt with result=pass found"
        )
    else:
        assert any("result=pass" in ln for ln in ralph_lines), "no ralph.attempt with result=pass found"

    # run.completed carries pr and duration
    completed_line = next((ln for ln in result.stdout.splitlines() if "run.completed" in ln), None)
    assert completed_line is not None
    assert "pr" in completed_line
    assert "duration" in completed_line


@pytest.mark.timeout(350)
def test_escalation_missing_artifact(bureau_test_repo):
    spec_path = str(Path(bureau_test_repo) / "specs" / "004-escalation-missing-schema" / "spec.md")
    result = run_bureau(spec_path, bureau_test_repo, timeout=300)

    assert "run.escalated" in result.stdout
    # no PR opened — check absence of pull URL rather than absence of github.com
    # (CE mode source URI contains github.com but no pull/)
    assert "/pull/" not in result.stdout
    if _is_cloudevents(result.stdout):
        escalated = next(
            (json.loads(ln) for ln in result.stdout.splitlines() if "run.escalated" in ln),
            None,
        )
        assert escalated is not None
        assert "what_happened" in escalated.get("data", {})
        assert "what_is_needed" in escalated.get("data", {})
    else:
        assert "What happened" in result.stdout
        assert "What's needed" in result.stdout
