from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from bureau.models import TaskPlan
from bureau.personas.planner import run_planner

_FIXTURE_PLAN = {
    "tasks": [
        {
            "id": "T001",
            "description": "Implement feature X in bureau/nodes/example.py",
            "fr_ids": ["FR-001", "FR-002"],
            "depends_on": [],
            "files_affected": ["bureau/nodes/example.py"],
            "done": False,
        }
    ],
    "spec_name": "Test Feature",
    "fr_coverage": ["FR-001", "FR-002"],
    "uncovered_frs": [],
    "created_at": "2026-04-18T00:00:00+00:00",
}


def _make_client(response_text: str, stop_reason: str = "end_turn") -> MagicMock:
    """Return a mock Anthropic client whose messages.create returns a fixed response."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = response_text

    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = stop_reason

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_run_planner_parses_json_code_block(tmp_path):
    plan_json = f"```json\n{json.dumps(_FIXTURE_PLAN)}\n```"
    client = _make_client(plan_json)

    result = run_planner(
        client=client,
        spec_text="# Test Feature\n\n## Requirements\n\n**FR-001**: Do X.\n**FR-002**: Do Y.",
        constitution="Constitution text.",
        repo_path=str(tmp_path),
        model="claude-opus-4-7",
    )

    assert isinstance(result, TaskPlan)
    assert result.spec_name == "Test Feature"
    assert result.fr_coverage == ["FR-001", "FR-002"]
    assert len(result.tasks) == 1
    assert result.tasks[0].id == "T001"
    assert "FR-001" in result.tasks[0].fr_ids


def test_run_planner_parses_bare_json(tmp_path):
    client = _make_client(json.dumps(_FIXTURE_PLAN))

    result = run_planner(
        client=client,
        spec_text="# Test Feature",
        constitution="",
        repo_path=str(tmp_path),
        model="claude-opus-4-7",
    )

    assert result.spec_name == "Test Feature"
    assert result.uncovered_frs == []


def test_run_planner_executes_tool_loop(tmp_path):
    """Verify the tool-use loop calls execute_file_tool and continues to end_turn."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "list_directory"
    tool_block.id = "tool_1"
    tool_block.input = {"path": "."}

    tool_response = MagicMock()
    tool_response.content = [tool_block]
    tool_response.stop_reason = "tool_use"

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = f"```json\n{json.dumps(_FIXTURE_PLAN)}\n```"

    final_response = MagicMock()
    final_response.content = [text_block]
    final_response.stop_reason = "end_turn"

    client = MagicMock()
    client.messages.create.side_effect = [tool_response, final_response]

    result = run_planner(
        client=client,
        spec_text="# Test Feature",
        constitution="",
        repo_path=str(tmp_path),
        model="claude-opus-4-7",
    )

    assert client.messages.create.call_count == 2
    assert result.spec_name == "Test Feature"


def test_run_planner_raises_on_invalid_json(tmp_path):
    client = _make_client("This is not JSON at all.")

    with pytest.raises(Exception):
        run_planner(
            client=client,
            spec_text="# Test Feature",
            constitution="",
            repo_path=str(tmp_path),
            model="claude-opus-4-7",
        )
