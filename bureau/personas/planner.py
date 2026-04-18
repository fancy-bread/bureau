from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import anthropic

from bureau.models import TaskPlan
from bureau.tools.file_tools import FILE_TOOLS, execute_file_tool

_PLANNER_TOOLS = [t for t in FILE_TOOLS if t["name"] in {"read_file", "list_directory"}]

_SYSTEM_TEMPLATE = """\
You are Bureau's Planner persona. Your job is to analyse the target repo and produce a \
dependency-ordered implementation task plan.

## Bureau Constitution
{constitution}

## Specification
{spec_text}

## Task
1. Use `read_file` and `list_directory` tools to understand the existing codebase structure.
2. Break every P1 functional requirement from the spec into concrete implementation tasks.
3. Map each task to one or more FR IDs from the spec.
4. Order tasks by dependency — prerequisite tasks listed first.
5. When your exploration is complete, respond with ONLY a JSON code block containing the TaskPlan.

The JSON must match this exact schema:
```
{{
  "tasks": [
    {{
      "id": "T001",
      "description": "Concrete implementation action with file path",
      "fr_ids": ["FR-001"],
      "depends_on": [],
      "files_affected": ["relative/path/to/file.py"],
      "done": false
    }}
  ],
  "spec_name": "Feature name from spec H1 title",
  "fr_coverage": ["FR-001", "FR-002"],
  "uncovered_frs": [],
  "created_at": "{created_at}"
}}
```

CRITICAL: All P1 FRs must appear in `fr_coverage`. If a P1 FR cannot be addressed, \
list it in `uncovered_frs`.
"""

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def run_planner(
    client: anthropic.Anthropic,
    spec_text: str,
    constitution: str,
    repo_path: str,
    model: str,
) -> TaskPlan:
    now = datetime.now(timezone.utc).isoformat()
    system = _SYSTEM_TEMPLATE.format(
        constitution=constitution,
        spec_text=spec_text,
        created_at=now,
    )

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "Begin exploration of the repo and produce the task plan."}
    ]

    response = None
    for _ in range(30):
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
            tools=_PLANNER_TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_file_tool(block.name, block.input, repo_path)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )

        messages.append({"role": "user", "content": tool_results})

    if response is None:
        raise RuntimeError("Planner produced no response")

    final_text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    m = _JSON_BLOCK.search(final_text)
    json_text = m.group(1) if m else final_text.strip()

    return TaskPlan.model_validate(json.loads(json_text))
