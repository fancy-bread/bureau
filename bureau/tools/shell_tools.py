from __future__ import annotations

import json
import subprocess

SHELL_TOOLS = [
    {
        "name": "run_command",
        "description": (
            "Run a shell command in the repo root. Returns stdout, stderr, and exit code. "
            "Use for install, build, and test commands only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (e.g. 'pytest tests/', 'npm test')",
                }
            },
            "required": ["command"],
        },
    }
]


def execute_shell_tool(tool_name: str, tool_input: dict, repo_path: str, timeout: int = 300) -> str:
    if tool_name == "run_command":
        try:
            result = subprocess.run(
                tool_input["command"],
                shell=True,
                cwd=repo_path,
                timeout=timeout,
                capture_output=True,
                text=True,
            )
            stdout = result.stdout[-4000:] if len(result.stdout) > 4000 else result.stdout
            stderr = result.stderr[-4000:] if len(result.stderr) > 4000 else result.stderr
            return json.dumps({"stdout": stdout, "stderr": stderr, "exit_code": result.returncode})
        except subprocess.TimeoutExpired:
            return json.dumps(
                {"stdout": "", "stderr": f"Command timed out after {timeout}s", "exit_code": -1}
            )
        except Exception as exc:
            return json.dumps({"stdout": "", "stderr": str(exc), "exit_code": -1})

    return f"Error: unknown tool '{tool_name}'"
