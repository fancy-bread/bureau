from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from bureau.models import BuildAttempt
from bureau.personas.builder import run_builder_attempt


def _make_tool_use_block(name: str, tool_id: str, input_data: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = input_data
    return block


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_response(content: list, stop_reason: str = "end_turn") -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.stop_reason = stop_reason
    return resp


def test_run_builder_attempt_passes_on_exit_code_zero(tmp_path):
    """Builder returns a passing BuildAttempt when run_command exits 0."""
    run_cmd_block = _make_tool_use_block("run_command", "tool_1", {"command": "pytest"})
    tool_response = _make_response([run_cmd_block], stop_reason="tool_use")

    final_response = _make_response([_make_text_block("Done.")], stop_reason="end_turn")

    client = MagicMock()
    client.messages.create.side_effect = [tool_response, final_response]

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "bureau.personas.builder.execute_shell_tool",
            lambda name, inp, path, timeout=300: json.dumps(
                {"stdout": "1 passed", "stderr": "", "exit_code": 0}
            ),
        )
        result = run_builder_attempt(
            client=client,
            spec_text="# Test",
            task_plan_text="- T001: do thing",
            constitution="",
            test_cmd="pytest",
            build_cmd="",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=0,
            previous_attempts=[],
        )

    assert isinstance(result, BuildAttempt)
    assert result.passed is True
    assert result.test_exit_code == 0
    assert result.round == 0
    assert result.attempt == 0


def test_run_builder_attempt_fails_on_nonzero_exit(tmp_path):
    """Builder returns a failing BuildAttempt when run_command exits non-zero."""
    run_cmd_block = _make_tool_use_block("run_command", "tool_1", {"command": "pytest"})
    tool_response = _make_response([run_cmd_block], stop_reason="tool_use")
    final_response = _make_response([_make_text_block("Done.")], stop_reason="end_turn")

    client = MagicMock()
    client.messages.create.side_effect = [tool_response, final_response]

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "bureau.personas.builder.execute_shell_tool",
            lambda name, inp, path, timeout=300: json.dumps(
                {"stdout": "", "stderr": "FAILED", "exit_code": 1}
            ),
        )
        result = run_builder_attempt(
            client=client,
            spec_text="# Test",
            task_plan_text="- T001: do thing",
            constitution="",
            test_cmd="pytest",
            build_cmd="",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=0,
            previous_attempts=[],
        )

    assert result.passed is False
    assert result.test_exit_code == 1


def test_run_builder_attempt_tracks_written_files(tmp_path):
    """Builder records files written via write_file tool."""
    write_block = _make_tool_use_block(
        "write_file", "tool_1", {"path": "src/foo.py", "content": "x = 1"}
    )
    tool_response = _make_response([write_block], stop_reason="tool_use")
    final_response = _make_response([_make_text_block("Done.")], stop_reason="end_turn")

    client = MagicMock()
    client.messages.create.side_effect = [tool_response, final_response]

    def fake_file_tool(name, inp, path):
        if name == "write_file":
            return "ok"
        return ""

    def fake_shell_tool(name, inp, path, timeout=300):
        return json.dumps({"stdout": "1 passed", "stderr": "", "exit_code": 0})

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("bureau.personas.builder.execute_file_tool", fake_file_tool)
        mp.setattr("bureau.personas.builder.execute_shell_tool", fake_shell_tool)
        result = run_builder_attempt(
            client=client,
            spec_text="# Test",
            task_plan_text="",
            constitution="",
            test_cmd="pytest",
            build_cmd="",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=1,
            attempt_num=2,
            previous_attempts=[],
        )

    assert "src/foo.py" in result.files_changed
    assert result.round == 1
    assert result.attempt == 2


def test_run_builder_attempt_includes_previous_failure_in_prompt(tmp_path):
    """Retry context from previous attempt appears in the user message."""
    prev = BuildAttempt(
        round=0,
        attempt=0,
        files_changed=[],
        test_output="FAILED: test_foo",
        test_exit_code=1,
        passed=False,
        timestamp="2026-04-18T00:00:00+00:00",
    )

    final_response = _make_response([_make_text_block("Done.")], stop_reason="end_turn")
    client = MagicMock()
    client.messages.create.return_value = final_response

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "bureau.personas.builder.execute_shell_tool",
            lambda name, inp, path, timeout=300: json.dumps(
                {"stdout": "1 passed", "stderr": "", "exit_code": 0}
            ),
        )
        run_builder_attempt(
            client=client,
            spec_text="# Test",
            task_plan_text="",
            constitution="",
            test_cmd="pytest",
            build_cmd="",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=1,
            previous_attempts=[prev],
        )

    call_args = client.messages.create.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0] if call_args.args else []
    if not messages:
        messages = call_args.kwargs.get("messages", [])
    first_user = next(m for m in messages if m["role"] == "user")
    assert "FAILED: test_foo" in first_user["content"]
