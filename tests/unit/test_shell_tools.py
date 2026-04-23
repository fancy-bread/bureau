from __future__ import annotations

import json
from unittest.mock import patch

from bureau.tools.shell_tools import execute_shell_tool


def test_run_command_success(tmp_path):
    result = json.loads(execute_shell_tool("run_command", {"command": "echo hello"}, str(tmp_path)))
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


def test_run_command_nonzero_exit(tmp_path):
    result = json.loads(execute_shell_tool("run_command", {"command": "exit 1"}, str(tmp_path)))
    assert result["exit_code"] == 1


def test_run_command_timeout(tmp_path):
    result = json.loads(
        execute_shell_tool("run_command", {"command": "sleep 10"}, str(tmp_path), timeout=1)
    )
    assert result["exit_code"] == -1
    assert "timed out" in result["stderr"]


def test_run_command_exception(tmp_path):
    with patch("subprocess.run", side_effect=OSError("no such file")):
        result = json.loads(execute_shell_tool("run_command", {"command": "x"}, str(tmp_path)))
    assert result["exit_code"] == -1
    assert "no such file" in result["stderr"]


def test_unknown_tool_returns_error(tmp_path):
    result = execute_shell_tool("unknown_tool", {}, str(tmp_path))
    assert "unknown tool" in result
