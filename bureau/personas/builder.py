from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from bureau import events
from bureau.models import BuildAttempt

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

_BUILDER_SKILL_DIRS = ("build", "test", "ship")

_LOGGABLE_TOOLS = {"write_file", "read_file", "edit_file", "glob", "grep", "execute", "ls"}


class _ProgressCallback(BaseCallbackHandler):
    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, *, run_id: UUID, **kwargs: Any
    ) -> None:
        tool = serialized.get("name", "unknown")
        if tool not in _LOGGABLE_TOOLS:
            return
        inputs: dict[str, Any] = kwargs.get("inputs") or {}
        detail = inputs.get("path") or inputs.get("command") or inputs.get("pattern") or ""
        events.emit(events.BUILDER_TOOL, tool=tool, detail=str(detail)[:120] if detail else "")

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        try:
            parsed = json.loads(str(output))
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(parsed, dict) and "exit_code" in parsed:
            events.emit(events.BUILDER_TOOL, tool="execute", exit_code=parsed["exit_code"])


def run_builder_attempt(
    spec_text: str,
    task_plan_text: str,
    constitution: str,
    test_cmd: str,
    repo_path: str,
    model: str,
    ralph_round: int,
    attempt_num: int,
    previous_attempts: list[BuildAttempt],
    skills_root: Path | None = None,
    timeout: int = 300,
) -> BuildAttempt:
    now_str = datetime.now(timezone.utc).isoformat()

    # Pre-flight: verify required skill directories have at least one .md file
    if skills_root is not None:
        for skill_dir_name in _BUILDER_SKILL_DIRS:
            skill_dir = skills_root / skill_dir_name
            if not any(skill_dir.glob("*.md")):
                raise ValueError(f"Required skill directory empty: {skill_dir}")

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

    skills = [str(skills_root / d) for d in _BUILDER_SKILL_DIRS] if skills_root is not None else None

    agent = create_deep_agent(
        model=model,
        system_prompt=system,
        backend=FilesystemBackend(root_dir=repo_path, virtual_mode=False),
        skills=skills,
    )

    # Cap agent steps to prevent unbounded loops; deepagents defaults to 9999.
    # At ~2-3s per API call, 120 steps ≈ 5-6 minutes, well within the timeout.
    step_limit = max(20, timeout // 3)

    try:
        result: dict[str, Any] = agent.invoke(
            {"messages": [HumanMessage(content=user_content)]},
            config={"recursion_limit": step_limit, "callbacks": [_ProgressCallback()]},
        )
    except Exception as exc:
        return BuildAttempt(
            round=ralph_round,
            attempt=attempt_num,
            files_changed=[],
            test_output=str(exc)[-4000:],
            test_exit_code=-1,
            passed=False,
            timestamp=now_str,
        )

    return _extract_build_attempt(result, ralph_round, attempt_num, now_str)


def _extract_build_attempt(
    agent_state: dict[str, Any],
    ralph_round: int,
    attempt_num: int,
    timestamp: str,
) -> BuildAttempt:
    messages = agent_state.get("messages", [])
    files_changed: list[str] = []
    last_exit_code = -1
    last_test_output = ""

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                if call.get("name") == "write_file":
                    path = call.get("args", {}).get("path", "")
                    if path and path not in files_changed:
                        files_changed.append(path)

        if isinstance(msg, ToolMessage):
            try:
                parsed = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, dict) and "exit_code" in parsed:
                last_exit_code = parsed["exit_code"]
                stdout = parsed.get("stdout", "")
                stderr = parsed.get("stderr", "")
                last_test_output = stdout + ("\n" + stderr if stderr else "")

    truncated = last_test_output[-4000:] if len(last_test_output) > 4000 else last_test_output

    return BuildAttempt(
        round=ralph_round,
        attempt=attempt_num,
        files_changed=files_changed,
        test_output=truncated,
        test_exit_code=last_exit_code,
        passed=last_exit_code == 0,
        timestamp=timestamp,
    )
