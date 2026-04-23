from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from bureau.models import BuildAttempt
from bureau.personas.builder import _extract_build_attempt, run_builder_attempt


def _make_agent_state(messages: list) -> dict:
    return {"messages": messages}


def _ai_write_file(path: str, tool_call_id: str = "tc1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"id": tool_call_id, "name": "write_file", "args": {"path": path, "content": "x"}}],
    )


def _tool_run_command(exit_code: int, stdout: str, stderr: str = "", tool_call_id: str = "tc2") -> ToolMessage:
    return ToolMessage(
        content=json.dumps({"exit_code": exit_code, "stdout": stdout, "stderr": stderr}),
        tool_call_id=tool_call_id,
    )


def _fake_agent(agent_state: dict) -> MagicMock:
    agent = MagicMock()
    agent.invoke.return_value = agent_state
    return agent


# --- _extract_build_attempt unit tests ---

def test_extract_passes_on_exit_code_zero():
    state = _make_agent_state([
        _tool_run_command(0, "1 passed"),
    ])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is True
    assert result.test_exit_code == 0
    assert result.test_output == "1 passed"


def test_extract_fails_on_nonzero_exit():
    state = _make_agent_state([
        _tool_run_command(1, "", "FAILED"),
    ])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is False
    assert result.test_exit_code == 1


def test_extract_collects_written_files():
    state = _make_agent_state([
        _ai_write_file("src/foo.py", "tc1"),
        _ai_write_file("src/bar.py", "tc2"),
        _tool_run_command(0, "2 passed", tool_call_id="tc3"),
    ])
    result = _extract_build_attempt(state, ralph_round=1, attempt_num=2, timestamp="ts")
    assert "src/foo.py" in result.files_changed
    assert "src/bar.py" in result.files_changed
    assert result.round == 1
    assert result.attempt == 2


def test_extract_deduplicates_files():
    state = _make_agent_state([
        _ai_write_file("src/foo.py", "tc1"),
        _ai_write_file("src/foo.py", "tc2"),
        _tool_run_command(0, "ok", tool_call_id="tc3"),
    ])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.files_changed.count("src/foo.py") == 1


def test_extract_last_run_command_wins():
    state = _make_agent_state([
        _tool_run_command(1, "first fail", tool_call_id="tc1"),
        _tool_run_command(0, "second pass", tool_call_id="tc2"),
    ])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is True
    assert "second pass" in result.test_output


def test_extract_no_commands_returns_exit_minus_one():
    state = _make_agent_state([HumanMessage(content="begin")])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.test_exit_code == -1
    assert result.passed is False


# --- run_builder_attempt integration tests ---

def test_run_builder_attempt_returns_build_attempt(tmp_path):
    agent_state = _make_agent_state([
        _ai_write_file("src/thing.py", "tc1"),
        _tool_run_command(0, "1 passed", tool_call_id="tc2"),
    ])
    fake_agent = _fake_agent(agent_state)

    with patch("bureau.personas.builder.create_deep_agent", return_value=fake_agent):
        result = run_builder_attempt(
            spec_text="# Test",
            task_plan_text="- T001: do thing",
            constitution="",
            test_cmd="pytest",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=0,
            previous_attempts=[],
        )

    assert isinstance(result, BuildAttempt)
    assert result.passed is True
    assert result.test_exit_code == 0
    assert "src/thing.py" in result.files_changed


def test_run_builder_attempt_retry_passes_previous_output(tmp_path):
    prev = BuildAttempt(
        round=0, attempt=0, files_changed=[],
        test_output="FAILED: test_foo", test_exit_code=1,
        passed=False, timestamp="2026-04-18T00:00:00+00:00",
    )
    agent_state = _make_agent_state([_tool_run_command(0, "1 passed", tool_call_id="tc1")])
    fake_agent = _fake_agent(agent_state)

    with patch("bureau.personas.builder.create_deep_agent", return_value=fake_agent) as mock_create:
        run_builder_attempt(
            spec_text="# Test",
            task_plan_text="",
            constitution="",
            test_cmd="pytest",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=1,
            previous_attempts=[prev],
        )

    invoke_call = fake_agent.invoke.call_args
    messages = invoke_call[0][0]["messages"]
    assert any("FAILED: test_foo" in str(m.content) for m in messages)
