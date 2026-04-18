from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bureau.nodes.critic import critic_node
from bureau.state import EscalationReason, RepoContext, make_initial_state

_PASS_JSON = json.dumps({
    "verdict": "pass",
    "findings": [
        {
            "type": "requirement",
            "ref_id": "FR-001",
            "verdict": "met",
            "detail": "Implemented.",
            "remediation": "",
        }
    ],
    "summary": "All good.",
    "round": 0,
})

_REVISE_JSON = json.dumps({
    "verdict": "revise",
    "findings": [
        {
            "type": "requirement",
            "ref_id": "FR-001",
            "verdict": "unmet",
            "detail": "Not implemented.",
            "remediation": "Implement it.",
        }
    ],
    "summary": "FR-001 unmet.",
    "round": 0,
})


def _make_client(response_text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = response_text

    resp = MagicMock()
    resp.content = [block]

    client = MagicMock()
    client.messages.create.return_value = resp
    return client


def _base_state(tmp_path, run_id: str = "run-c-001") -> dict:
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(
        "# Test\n\n## User Scenarios & Testing\n\n### US1 (Priority: P1)\nDo it.\n\n"
        "## Requirements\n\n- **FR-001**: Do X.\n\n## Success Criteria\n\n- SC-001: Done.\n"
    )
    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_ralph_rounds=3,
    )
    state = make_initial_state(run_id, str(spec_file), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = spec_file.read_text()
    state["ralph_round"] = 0
    state["build_attempts"] = [
        {
            "round": 0,
            "attempt": 0,
            "files_changed": ["bureau/nodes/example.py"],
            "test_output": "1 passed",
            "test_exit_code": 0,
            "passed": True,
            "timestamp": "2026-04-18T00:00:00+00:00",
        }
    ]
    return state


def test_critic_node_pass_routes_to_pr_create(tmp_path):
    state = _base_state(tmp_path)

    with (
        patch("bureau.nodes.critic.anthropic.Anthropic", return_value=_make_client(_PASS_JSON)),
        patch("bureau.nodes.critic.Memory") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = {"ralph_round": 0, "files_changed": [], "last_test_output": ""}
        mock_mem_cls.return_value = mock_mem

        result = critic_node(state)

    assert result["_route"] == "pass"
    assert len(result["ralph_rounds"]) == 1
    assert result["ralph_rounds"][0]["critic_verdict"] == "pass"
    assert result["critic_findings"][0]["ref_id"] == "FR-001"


def test_critic_node_revise_increments_ralph_round(tmp_path):
    state = _base_state(tmp_path)

    with (
        patch("bureau.nodes.critic.anthropic.Anthropic", return_value=_make_client(_REVISE_JSON)),
        patch("bureau.nodes.critic.Memory") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = {"ralph_round": 0, "files_changed": [], "last_test_output": ""}
        mock_mem_cls.return_value = mock_mem

        result = critic_node(state)

    assert result["_route"] == "revise"
    assert result["ralph_round"] == 1
    assert result["builder_attempts"] == 0


def test_critic_node_escalates_when_rounds_exceeded(tmp_path):
    state = _base_state(tmp_path)
    state["ralph_round"] = 2  # already at max_rounds - 1 (max=3, 0-indexed so round 2 is last)
    state["repo_context"] = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_ralph_rounds=3,
    )

    with (
        patch("bureau.nodes.critic.anthropic.Anthropic", return_value=_make_client(_REVISE_JSON)),
        patch("bureau.nodes.critic.Memory") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = {"ralph_round": 2, "files_changed": [], "last_test_output": ""}
        mock_mem_cls.return_value = mock_mem

        result = critic_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.RALPH_ROUNDS_EXCEEDED
