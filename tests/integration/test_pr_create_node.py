from __future__ import annotations

from unittest.mock import MagicMock, patch

from bureau.nodes.pr_create import pr_create_node
from bureau.state import EscalationReason, Phase, RepoContext, make_initial_state

_REVIEWER_FINDINGS = [
    {
        "type": "requirement",
        "ref_id": "FR-001",
        "verdict": "met",
        "detail": "Implemented.",
        "remediation": "",
    },
    {
        "type": "requirement",
        "ref_id": "FR-002",
        "verdict": "met",
        "detail": "Also implemented.",
        "remediation": "",
    },
]

_RALPH_ROUNDS = [
    {
        "round": 0,
        "build_attempts": [],
        "reviewer_verdict": "pass",
        "reviewer_findings": _REVIEWER_FINDINGS,
        "completed_at": "2026-04-18T00:00:00+00:00",
    }
]


def _base_state(tmp_path) -> dict:
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(
        "# My Feature\n\n**Feature Branch**: `feat-branch`\n**Status**: Draft\n\n"
        "## User Scenarios & Testing\n\n### US1 (Priority: P1)\nDo it.\n\n"
        "## Requirements\n\n- **FR-001**: Do X.\n\n## Success Criteria\n\n- SC-001: Done.\n"
    )
    from bureau.spec_parser import parse_spec

    state = make_initial_state("run-pr-001", str(spec_file), str(tmp_path))
    state["spec"] = parse_spec(str(spec_file))
    state["spec_text"] = spec_file.read_text()
    state["repo_context"] = RepoContext(
        language="python", base_image="python:3.14-slim", install_cmd="", test_cmd="pytest"
    )
    state["ralph_rounds"] = _RALPH_ROUNDS
    state["reviewer_findings"] = _REVIEWER_FINDINGS
    return state


def test_pr_create_node_emits_run_completed(tmp_path, capsys):
    state = _base_state(tmp_path)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "https://github.com/org/repo/pull/42\n"
    mock_result.stderr = ""

    with (
        patch("bureau.nodes.pr_create.subprocess.run", return_value=mock_result),
        patch("bureau.nodes.pr_create.Memory"),
        patch("bureau.nodes.pr_create.get_run", side_effect=Exception("no record")),
    ):
        result = pr_create_node(state)

    captured = capsys.readouterr()
    assert "run.completed" in captured.out
    assert "https://github.com/org/repo/pull/42" in captured.out
    assert result["phase"] == Phase.COMPLETE


def test_pr_create_node_pr_body_contains_required_fields(tmp_path):
    state = _base_state(tmp_path)

    captured_body: list[str] = []

    def fake_subprocess_run(cmd, **kwargs):
        body_flag_idx = cmd.index("--body")
        captured_body.append(cmd[body_flag_idx + 1])
        result = MagicMock()
        result.returncode = 0
        result.stdout = "https://github.com/org/repo/pull/99\n"
        result.stderr = ""
        return result

    with (
        patch("bureau.nodes.pr_create.subprocess.run", side_effect=fake_subprocess_run),
        patch("bureau.nodes.pr_create.Memory"),
        patch("bureau.nodes.pr_create.get_run", side_effect=Exception("no record")),
    ):
        pr_create_node(state)

    assert captured_body, "PR body was not captured"
    body = captured_body[0]
    assert "run-pr-001" in body
    assert "My Feature" in body
    assert "FR-001" in body
    assert "FR-002" in body
    assert "pass" in body
    assert "1" in body  # ralph_rounds count


def test_pr_create_node_escalates_on_gh_failure(tmp_path):
    state = _base_state(tmp_path)

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "error: remote not configured"

    with (
        patch("bureau.nodes.pr_create.subprocess.run", return_value=mock_result),
        patch("bureau.nodes.pr_create.Memory"),
        patch("bureau.nodes.pr_create.get_run", side_effect=Exception("no record")),
    ):
        result = pr_create_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.PR_FAILED
    assert "remote not configured" in esc.what_happened
