from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bureau.nodes.builder import builder_node
from bureau.state import EscalationReason, RepoContext, make_initial_state

_TASK_PLAN = {
    "tasks": [
        {
            "id": "T001",
            "description": "Add a hello function to bureau/nodes/example.py",
            "fr_ids": ["FR-001"],
            "depends_on": [],
            "files_affected": ["bureau/nodes/example.py"],
            "done": False,
        }
    ],
    "spec_name": "Test Feature",
    "fr_coverage": ["FR-001"],
    "uncovered_frs": [],
    "created_at": "2026-04-18T00:00:00+00:00",
}


def _make_mock_client(exit_code: int = 0) -> MagicMock:
    """Mock Builder persona that returns a run_command call then stops."""
    run_cmd = MagicMock()
    run_cmd.type = "tool_use"
    run_cmd.name = "run_command"
    run_cmd.id = "tool_1"
    run_cmd.input = {"command": "pytest"}

    tool_response = MagicMock()
    tool_response.content = [run_cmd]
    tool_response.stop_reason = "tool_use"

    final_block = MagicMock()
    final_block.type = "text"
    final_block.text = "Implementation complete."

    final_response = MagicMock()
    final_response.content = [final_block]
    final_response.stop_reason = "end_turn"

    client = MagicMock()
    client.messages.create.side_effect = [tool_response, final_response]
    return client


def test_builder_node_appends_build_attempt_on_pass(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_builder_attempts=3,
    )
    state = make_initial_state("run-b-001", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    shell_result = json.dumps({"stdout": "1 passed", "stderr": "", "exit_code": 0})

    with (
        patch("bureau.nodes.builder.anthropic.Anthropic", return_value=_make_mock_client()),
        patch("bureau.personas.builder.execute_shell_tool", return_value=shell_result),
    ):
        result = builder_node(state)

    assert result.get("_route") != "escalate"
    assert len(result["build_attempts"]) == 1
    attempt = result["build_attempts"][0]
    assert attempt["passed"] is True
    assert attempt["round"] == 0
    assert attempt["attempt"] == 0


def test_builder_node_escalates_after_max_attempts(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_builder_attempts=2,
    )
    state = make_initial_state("run-b-002", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    # Client needs responses for 2 attempts × 2 calls each (tool + final)
    def make_attempt_client():
        run_cmd = MagicMock()
        run_cmd.type = "tool_use"
        run_cmd.name = "run_command"
        run_cmd.id = "tool_x"
        run_cmd.input = {"command": "pytest"}

        tool_resp = MagicMock()
        tool_resp.content = [run_cmd]
        tool_resp.stop_reason = "tool_use"

        final_block = MagicMock()
        final_block.type = "text"
        final_block.text = "done"
        final_resp = MagicMock()
        final_resp.content = [final_block]
        final_resp.stop_reason = "end_turn"

        return [tool_resp, final_resp]

    client = MagicMock()
    client.messages.create.side_effect = make_attempt_client() + make_attempt_client()

    shell_result = json.dumps({"stdout": "", "stderr": "FAILED", "exit_code": 1})

    with (
        patch("bureau.nodes.builder.anthropic.Anthropic", return_value=client),
        patch("bureau.personas.builder.execute_shell_tool", return_value=shell_result),
    ):
        result = builder_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.RALPH_EXHAUSTED
