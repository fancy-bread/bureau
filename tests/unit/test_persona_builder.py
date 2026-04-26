from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from bureau.models import BuildAttempt
from bureau.personas.builder import _extract_build_attempt, _ProgressCallback, run_builder_attempt


def _make_agent_state(messages: list) -> dict:
    return {"messages": messages}


def _ai_write_file(path: str, tool_call_id: str = "tc1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"id": tool_call_id, "name": "write_file", "args": {"path": path, "content": "x"}}],
    )


def _tool_run_command(
    exit_code: int, stdout: str, stderr: str = "", tool_call_id: str = "tc2"
) -> ToolMessage:
    status = "succeeded" if exit_code == 0 else "failed"
    marker = f"[Command {status} with exit code {exit_code}]"
    body = (stdout + ("\n" + stderr if stderr else "")).rstrip()
    content = f"{body}\n{marker}" if body else marker
    return ToolMessage(content=content, tool_call_id=tool_call_id)


def _fake_agent(agent_state: dict) -> MagicMock:
    agent = MagicMock()
    agent.invoke.return_value = agent_state
    return agent


# --- _extract_build_attempt unit tests ---


def test_extract_passes_on_exit_code_zero():
    state = _make_agent_state(
        [
            _tool_run_command(0, "1 passed"),
        ]
    )
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is True
    assert result.test_exit_code == 0
    assert result.test_output == "1 passed"


def test_extract_fails_on_nonzero_exit():
    state = _make_agent_state(
        [
            _tool_run_command(1, "", "FAILED"),
        ]
    )
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is False
    assert result.test_exit_code == 1


def test_extract_collects_written_files():
    state = _make_agent_state(
        [
            _ai_write_file("src/foo.py", "tc1"),
            _ai_write_file("src/bar.py", "tc2"),
            _tool_run_command(0, "2 passed", tool_call_id="tc3"),
        ]
    )
    result = _extract_build_attempt(state, ralph_round=1, attempt_num=2, timestamp="ts")
    assert "src/foo.py" in result.files_changed
    assert "src/bar.py" in result.files_changed
    assert result.round == 1
    assert result.attempt == 2


def test_extract_deduplicates_files():
    state = _make_agent_state(
        [
            _ai_write_file("src/foo.py", "tc1"),
            _ai_write_file("src/foo.py", "tc2"),
            _tool_run_command(0, "ok", tool_call_id="tc3"),
        ]
    )
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.files_changed.count("src/foo.py") == 1


def test_extract_last_run_command_wins():
    state = _make_agent_state(
        [
            _tool_run_command(1, "first fail", tool_call_id="tc1"),
            _tool_run_command(0, "second pass", tool_call_id="tc2"),
        ]
    )
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is True
    assert "second pass" in result.test_output


def test_extract_no_commands_returns_exit_minus_one():
    state = _make_agent_state([HumanMessage(content="begin")])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.test_exit_code == -1
    assert result.passed is False


def test_extract_collects_files_using_file_path_key():
    """deepagents write_file uses 'file_path', not 'path'."""
    msg = AIMessage(
        content="",
        tool_calls=[
            {"id": "tc1", "name": "write_file", "args": {"file_path": "src/greeting.py", "content": "x"}}
        ],
    )
    state = _make_agent_state([msg, _tool_run_command(0, "1 passed", tool_call_id="tc2")])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert "src/greeting.py" in result.files_changed


def test_extract_collects_edited_files():
    """edit_file calls also populate files_changed."""
    msg = AIMessage(
        content="",
        tool_calls=[
            {"id": "tc1", "name": "edit_file", "args": {"file_path": "src/foo.py", "new_str": "b"}}
        ],
    )
    state = _make_agent_state([msg, _tool_run_command(0, "ok", tool_call_id="tc2")])
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert "src/foo.py" in result.files_changed


# --- run_builder_attempt integration tests ---


def test_run_builder_attempt_returns_build_attempt(tmp_path):
    agent_state = _make_agent_state(
        [
            _ai_write_file("src/thing.py", "tc1"),
            _tool_run_command(0, "1 passed", tool_call_id="tc2"),
        ]
    )
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
        round=0,
        attempt=0,
        files_changed=[],
        test_output="FAILED: test_foo",
        test_exit_code=1,
        passed=False,
        timestamp="2026-04-18T00:00:00+00:00",
    )
    agent_state = _make_agent_state([_tool_run_command(0, "1 passed", tool_call_id="tc1")])
    fake_agent = _fake_agent(agent_state)

    with patch("bureau.personas.builder.create_deep_agent", return_value=fake_agent):
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


def test_run_builder_attempt_passes_recursion_limit_in_config(tmp_path):
    fake_agent = _fake_agent(_make_agent_state([_tool_run_command(0, "ok", tool_call_id="tc1")]))

    with patch("bureau.personas.builder.create_deep_agent", return_value=fake_agent):
        run_builder_attempt(
            spec_text="# Test",
            task_plan_text="",
            constitution="",
            test_cmd="pytest",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=0,
            previous_attempts=[],
            timeout=300,
        )

    _, kwargs = fake_agent.invoke.call_args
    assert "config" in kwargs
    assert "recursion_limit" in kwargs["config"]
    assert kwargs["config"]["recursion_limit"] == 100  # 300 // 3


def test_run_builder_attempt_api_error_returns_failed_attempt(tmp_path):
    fake_agent = MagicMock()
    fake_agent.invoke.side_effect = RuntimeError("Error code: 529 - Overloaded")

    with patch("bureau.personas.builder.create_deep_agent", return_value=fake_agent):
        result = run_builder_attempt(
            spec_text="# Test",
            task_plan_text="",
            constitution="",
            test_cmd="pytest",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=1,
            attempt_num=2,
            previous_attempts=[],
        )

    assert isinstance(result, BuildAttempt)
    assert result.passed is False
    assert result.test_exit_code == -1
    assert result.round == 1
    assert result.attempt == 2
    assert "529" in result.test_output


def test_run_builder_attempt_preflight_raises_on_empty_skill_dir(tmp_path):
    skills_root = tmp_path / "skills"
    (skills_root / "build").mkdir(parents=True)
    (skills_root / "test").mkdir(parents=True)
    (skills_root / "ship").mkdir(parents=True)
    # ship dir is empty — no .md files

    with pytest.raises(ValueError, match="Required skill directory empty"):
        run_builder_attempt(
            spec_text="# Test",
            task_plan_text="",
            constitution="",
            test_cmd="pytest",
            repo_path=str(tmp_path),
            model="claude-sonnet-4-6",
            ralph_round=0,
            attempt_num=0,
            previous_attempts=[],
            skills_root=skills_root,
        )


def test_extract_ignores_tool_message_with_invalid_json():
    state = _make_agent_state(
        [
            ToolMessage(content="not json", tool_call_id="tc1"),
            _tool_run_command(0, "passed", tool_call_id="tc2"),
        ]
    )
    result = _extract_build_attempt(state, ralph_round=0, attempt_num=0, timestamp="ts")
    assert result.passed is True


# --- _ProgressCallback tests ---


def _make_run_id():
    from uuid import uuid4

    return uuid4()


def test_progress_callback_on_tool_start_emits_event(capsys):
    cb = _ProgressCallback()
    cb.on_tool_start(
        {"name": "write_file"},
        "",
        run_id=_make_run_id(),
        inputs={"path": "src/foo.py", "content": "x"},
    )
    out = capsys.readouterr().out
    assert "builder.tool" in out
    assert "write_file" in out
    assert "src/foo.py" in out


def test_progress_callback_skips_non_loggable_tool(capsys):
    cb = _ProgressCallback()
    cb.on_tool_start({"name": "write_todos"}, "", run_id=_make_run_id())
    assert capsys.readouterr().out == ""


def test_progress_callback_on_tool_end_emits_exit_code(capsys):
    cb = _ProgressCallback()
    cb.on_tool_end(
        "1 passed in 0.3s\n[Command succeeded with exit code 0]",
        run_id=_make_run_id(),
    )
    out = capsys.readouterr().out
    assert "builder.tool" in out
    assert "exit_code=0" in out


def test_progress_callback_on_tool_end_ignores_non_execute_output(capsys):
    cb = _ProgressCallback()
    cb.on_tool_end("plain string output with no exit code marker", run_id=_make_run_id())
    assert capsys.readouterr().out == ""
