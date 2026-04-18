from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bureau.nodes.planner import planner_node
from bureau.state import EscalationReason, RepoContext, make_initial_state

_SPEC_CONTENT = """\
# Test Feature

**Feature Branch**: `test-branch`
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Do the thing (Priority: P1)

A user does the thing.

**Acceptance Scenarios**:

1. **Given** a thing, **When** done, **Then** it is done.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST do the thing.
- **FR-002**: The system MUST do the other thing.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The thing is done.
"""

_FIXTURE_PLAN = {
    "tasks": [
        {
            "id": "T001",
            "description": "Do the thing in bureau/nodes/example.py",
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


def _make_mock_client() -> MagicMock:
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = f"```json\n{json.dumps(_FIXTURE_PLAN)}\n```"

    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_planner_node_writes_task_plan_to_state(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_SPEC_CONTENT)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="pip install -e .",
        test_cmd="pytest",
        planner_model="claude-opus-4-7",
    )

    state = make_initial_state("run-test-001", str(spec_file), str(tmp_path))
    # Simulate validate_spec having run
    from bureau.spec_parser import parse_spec
    state["spec"] = parse_spec(str(spec_file))
    state["spec_text"] = _SPEC_CONTENT
    state["repo_context"] = repo_context

    with patch("bureau.nodes.planner.anthropic.Anthropic", return_value=_make_mock_client()):
        result = planner_node(state)

    assert result["_route"] == "ok"
    assert result["task_plan"] is not None
    plan = result["task_plan"]
    assert plan["spec_name"] == "Test Feature"
    assert "FR-001" in plan["fr_coverage"]
    assert "FR-002" in plan["fr_coverage"]
    assert len(plan["tasks"]) == 1


def test_planner_node_escalates_on_uncovered_p1_fr(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_SPEC_CONTENT)

    incomplete_plan = {**_FIXTURE_PLAN, "fr_coverage": ["FR-001"], "uncovered_frs": ["FR-002"]}

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = f"```json\n{json.dumps(incomplete_plan)}\n```"
    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"
    client = MagicMock()
    client.messages.create.return_value = response

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="pip install -e .",
        test_cmd="pytest",
    )
    state = make_initial_state("run-test-002", str(spec_file), str(tmp_path))
    from bureau.spec_parser import parse_spec
    state["spec"] = parse_spec(str(spec_file))
    state["spec_text"] = _SPEC_CONTENT
    state["repo_context"] = repo_context

    with patch("bureau.nodes.planner.anthropic.Anthropic", return_value=client):
        result = planner_node(state)

    assert result["_route"] == "escalate"
    assert result["escalations"]
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.PLAN_INCOMPLETE
