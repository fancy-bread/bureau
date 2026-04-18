from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import anthropic

from bureau.models import BuildAttempt
from bureau.tools.file_tools import FILE_TOOLS, execute_file_tool
from bureau.tools.shell_tools import SHELL_TOOLS, execute_shell_tool

_ALL_TOOLS = FILE_TOOLS + SHELL_TOOLS

_SYSTEM_TEMPLATE = """\
You are Bureau's Builder persona. Implement the task plan by making code changes to \
the target repo and running the test suite.

## Bureau Constitution
{constitution}

## Specification
{spec_text}

## Task Plan
{task_plan_text}

## Instructions
1. Read relevant files to understand the existing code.
2. Implement the tasks in dependency order.
3. After making changes, run the test command to verify: `{test_cmd}`
4. If tests fail, read the output, fix the issues, and run again.
5. Stop when the test command exits with code 0.

IMPORTANT:
- Always provide complete file content when using write_file (no partial writes).
- Run `{test_cmd}` after each significant set of changes.
- Do not modify test files unless the task explicitly requires it.
"""

_RETRY_TEMPLATE = """\
The previous implementation attempt failed. Test output from last attempt:

```
{test_output}
```

Review the failure, fix the root cause, and run the tests again.
"""


def run_builder_attempt(
    client: anthropic.Anthropic,
    spec_text: str,
    task_plan_text: str,
    constitution: str,
    test_cmd: str,
    build_cmd: str,
    repo_path: str,
    model: str,
    ralph_round: int,
    attempt_num: int,
    previous_attempts: list[BuildAttempt],
    timeout: int = 300,
) -> BuildAttempt:
    now_str = datetime.now(timezone.utc).isoformat()

    system = _SYSTEM_TEMPLATE.format(
        constitution=constitution,
        spec_text=spec_text,
        task_plan_text=task_plan_text,
        test_cmd=test_cmd,
    )

    if previous_attempts:
        user_content = _RETRY_TEMPLATE.format(test_output=previous_attempts[-1].test_output)
    else:
        user_content = "Begin implementation per the task plan."

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

    files_changed: list[str] = []
    last_exit_code = -1
    last_test_output = ""

    for _ in range(50):
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=_ALL_TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name in {"read_file", "write_file", "list_directory"}:
                result = execute_file_tool(block.name, block.input, repo_path)
                if block.name == "write_file" and not result.startswith("Error"):
                    path = block.input.get("path", "")
                    if path and path not in files_changed:
                        files_changed.append(path)
            elif block.name == "run_command":
                result = execute_shell_tool(block.name, block.input, repo_path, timeout)
                parsed = json.loads(result)
                last_exit_code = parsed["exit_code"]
                last_test_output = parsed["stdout"]
                if parsed["stderr"]:
                    last_test_output += "\n" + parsed["stderr"]
            else:
                result = f"Error: unknown tool '{block.name}'"

            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )

        messages.append({"role": "user", "content": tool_results})

    # If the Builder never ran any command, run test_cmd explicitly
    if last_exit_code == -1:
        cmd = f"{build_cmd} && {test_cmd}" if build_cmd else test_cmd
        raw = execute_shell_tool("run_command", {"command": cmd}, repo_path, timeout)
        parsed = json.loads(raw)
        last_exit_code = parsed["exit_code"]
        last_test_output = parsed["stdout"]
        if parsed["stderr"]:
            last_test_output += "\n" + parsed["stderr"]

    truncated = last_test_output[-4000:] if len(last_test_output) > 4000 else last_test_output

    return BuildAttempt(
        round=ralph_round,
        attempt=attempt_num,
        files_changed=files_changed,
        test_output=truncated,
        test_exit_code=last_exit_code,
        passed=last_exit_code == 0,
        timestamp=now_str,
    )
