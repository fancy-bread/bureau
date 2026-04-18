from __future__ import annotations

from pathlib import Path

FILE_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the full contents of a file. Path is relative to the repo root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to repo root (e.g. src/main.py)",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write full content to a file. Creates the file if it does not exist. "
            "Always provide the complete file content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to repo root"},
                "content": {
                    "type": "string",
                    "description": "Complete file content to write",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to repo root. Use '.' for root.",
                }
            },
            "required": ["path"],
        },
    },
]


def execute_file_tool(tool_name: str, tool_input: dict, repo_path: str) -> str:
    root = Path(repo_path).resolve()

    if tool_name == "read_file":
        try:
            target = (root / tool_input["path"]).resolve()
            if not str(target).startswith(str(root)):
                return "Error: path is outside repo root"
            if not target.exists():
                return f"Error: file not found: {tool_input['path']}"
            return target.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Error: {exc}"

    if tool_name == "write_file":
        try:
            target = (root / tool_input["path"]).resolve()
            if not str(target).startswith(str(root)):
                return "Error: path is outside repo root"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(tool_input["content"], encoding="utf-8")
            return "ok"
        except Exception as exc:
            return f"Error: {exc}"

    if tool_name == "list_directory":
        try:
            target = (root / tool_input["path"]).resolve()
            if not str(target).startswith(str(root)):
                return "Error: path is outside repo root"
            if not target.is_dir():
                return f"Error: not a directory: {tool_input['path']}"
            entries = []
            for p in sorted(target.iterdir()):
                prefix = "[dir]" if p.is_dir() else "[file]"
                entries.append(f"{prefix} {p.name}")
            return "\n".join(entries) if entries else "(empty directory)"
        except Exception as exc:
            return f"Error: {exc}"

    return f"Error: unknown tool '{tool_name}'"
