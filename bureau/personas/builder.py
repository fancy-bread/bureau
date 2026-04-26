from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from bureau import events
from bureau.models import BuildAttempt

_SYSTEM_TEMPLATE = """\
You are Bureau's Builder persona. Implement the task plan by making code changes to \
the target repo and running the test suite.

## Target Repository
Your working directory is: {repo_path}
All file paths are relative to this directory. Do not read or write files outside it.

## Bureau Constitution
{constitution}

## Specification
{spec_text}

## Task Plan
{task_plan_text}

## Instructions
1. Start by listing files in {repo_path} to understand the project structure.
2. Implement the tasks in dependency order.
3. After making changes, run the test command to verify: `{test_cmd}`
4. If tests fail, read the output carefully, fix the root cause, and run again.
5. Stop when the test command exits with code 0.

IMPORTANT:
- Always provide complete file content when using write_file (no partial writes).
- Run `{test_cmd}` after each significant set of changes.
- Do not modify test files unless the task explicitly requires it.
- Work only within {repo_path}; never explore the broader filesystem.
- Never run `bureau run`, `bureau resume`, or any `bureau` subcommand. Recursive \
bureau invocations are forbidden. If a required artifact is missing (a schema, \
contract, or reference file named in the spec), stop — do not invent a substitute.
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

# deepagents execute tool returns plain text ending with this marker
_EXIT_CODE_RE = re.compile(r"\[Command (?:succeeded|failed) with exit code (\d+)\]")


def _parse_detail(input_str: str) -> str:
    """Extract a single meaningful value from a tool's input_str for logging."""
    try:
        parsed = json.loads(input_str)
        if isinstance(parsed, dict):
            return str(
                parsed.get("path")
                or parsed.get("command")
                or parsed.get("pattern")
                or next(iter(parsed.values()), "")
            )
    except (json.JSONDecodeError, TypeError):
        pass
    return input_str[:80] if input_str else ""


class _ProgressCallback(BaseCallbackHandler):
    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, *, run_id: UUID, **kwargs: Any
    ) -> None:
        tool = serialized.get("name", "unknown")
        if tool not in _LOGGABLE_TOOLS:
            return
        inputs: dict[str, Any] = kwargs.get("inputs") or {}
        detail = (
            inputs.get("path")
            or inputs.get("command")
            or inputs.get("pattern")
            or _parse_detail(input_str)
        )
        events.emit(events.BUILDER_TOOL, tool=tool, detail=str(detail)[:120] if detail else "")

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        match = _EXIT_CODE_RE.search(str(output))
        if match:
            events.emit(events.BUILDER_TOOL, tool="execute", exit_code=int(match.group(1)))


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
        repo_path=repo_path,
    )

    if previous_attempts:
        user_content = _RETRY_TEMPLATE.format(test_output=previous_attempts[-1].test_output)
    else:
        user_content = "Begin implementation per the task plan."

    skills = [str(skills_root / d) for d in _BUILDER_SKILL_DIRS] if skills_root is not None else None

    agent = create_deep_agent(
        model=model,
        system_prompt=system,
        backend=LocalShellBackend(root_dir=repo_path, virtual_mode=False, inherit_env=True),
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
                if call.get("name") in ("write_file", "edit_file"):
                    args = call.get("args", {})
                    path = args.get("file_path") or args.get("path", "")
                    if path and path not in files_changed:
                        files_changed.append(path)

        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            match = _EXIT_CODE_RE.search(content)
            if match:
                last_exit_code = int(match.group(1))
                last_test_output = content[: match.start()].rstrip()

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
