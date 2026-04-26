from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bureau.models import PipelinePhase, PipelineResult
from bureau.nodes.reviewer import reviewer_node
from bureau.personas.reviewer import run_reviewer as _real_run_reviewer
from bureau.state import EscalationReason, RepoContext, make_initial_state

_PASS_JSON = json.dumps(
    {
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
    }
)

_REVISE_JSON = json.dumps(
    {
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
    }
)


def _make_client(response_text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = response_text

    resp = MagicMock()
    resp.content = [block]

    client = MagicMock()
    client.messages.create.return_value = resp
    return client


def _passing_pipeline() -> PipelineResult:
    return PipelineResult(passed=True, phases_run=[PipelinePhase.TEST])


def _summary(files_changed: list[str], output: str = "") -> dict:
    return {"ralph_round": 0, "files_changed": files_changed, "last_test_output": output}


def _base_state(tmp_path, run_id: str = "run-r-001") -> dict:
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(
        "# Test\n\n## User Scenarios & Testing\n\n### US1 (Priority: P1)\nDo it.\n\n"
        "## Requirements\n\n- **FR-001**: Do X.\n\n## Success Criteria\n\n- SC-001: Done.\n"
    )
    (tmp_path / "src.py").write_text("def foo(): return 42\n")

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
            "files_changed": ["src.py"],
            "test_output": "1 passed",
            "test_exit_code": 0,
            "passed": True,
            "timestamp": "2026-04-26T00:00:00+00:00",
        }
    ]
    return state


def test_reviewer_node_pass_routes_to_pr_create(tmp_path):
    state = _base_state(tmp_path)

    with (
        patch("bureau.nodes.reviewer.anthropic.Anthropic", return_value=_make_client(_PASS_JSON)),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.run_pipeline", return_value=_passing_pipeline()),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py"])
        mock_mem_cls.return_value = mock_mem

        result = reviewer_node(state)

    assert result["_route"] == "pass"
    assert len(result["ralph_rounds"]) == 1
    assert result["ralph_rounds"][0]["reviewer_verdict"] == "pass"
    assert result["reviewer_findings"][0]["ref_id"] == "FR-001"


def test_reviewer_node_revise_increments_ralph_round(tmp_path):
    state = _base_state(tmp_path)

    with (
        patch("bureau.nodes.reviewer.anthropic.Anthropic", return_value=_make_client(_REVISE_JSON)),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.run_pipeline", return_value=_passing_pipeline()),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py"])
        mock_mem_cls.return_value = mock_mem

        result = reviewer_node(state)

    assert result["_route"] == "revise"
    assert result["ralph_round"] == 1
    assert result["builder_attempts"] == 0


def test_reviewer_node_escalates_when_rounds_exceeded(tmp_path):
    state = _base_state(tmp_path)
    state["ralph_round"] = 2
    state["repo_context"] = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_ralph_rounds=3,
    )

    with (
        patch("bureau.nodes.reviewer.anthropic.Anthropic", return_value=_make_client(_REVISE_JSON)),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.run_pipeline", return_value=_passing_pipeline()),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py"])
        mock_mem_cls.return_value = mock_mem
        mock_mem.read.return_value["ralph_round"] = 2

        result = reviewer_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.RALPH_ROUNDS_EXCEEDED


def test_reviewer_node_revises_when_independent_pipeline_fails(tmp_path):
    state = _base_state(tmp_path)

    failing_pipeline = PipelineResult(
        passed=False,
        failed_phase=PipelinePhase.TEST,
        failed_output="FAILED tests/test_foo.py - AssertionError",
        phases_run=[PipelinePhase.TEST],
    )

    with (
        patch("bureau.nodes.reviewer.run_pipeline", return_value=failing_pipeline),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.anthropic.Anthropic"),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py"], "1 passed")
        mock_mem_cls.return_value = mock_mem

        result = reviewer_node(state)

    assert result["_route"] == "revise"
    findings = result["reviewer_findings"]
    assert any(f["ref_id"] == "FR-009" for f in findings)
    assert any("test" in f["detail"] for f in findings)


def test_reviewer_node_revises_when_lint_fails_independently(tmp_path):
    state = _base_state(tmp_path)
    state["repo_context"] = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        lint_cmd="ruff check .",
        max_ralph_rounds=3,
    )

    failing_lint = PipelineResult(
        passed=False,
        failed_phase=PipelinePhase.LINT,
        failed_output="E501 line too long",
        phases_run=[PipelinePhase.LINT],
    )

    with (
        patch("bureau.nodes.reviewer.run_pipeline", return_value=failing_lint),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.anthropic.Anthropic"),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py"], "1 passed")
        mock_mem_cls.return_value = mock_mem

        result = reviewer_node(state)

    assert result["_route"] == "revise"
    findings = result["reviewer_findings"]
    assert any("lint" in f["detail"] for f in findings)


def test_reviewer_node_revises_when_no_files_changed(tmp_path):
    state = _base_state(tmp_path)

    with (
        patch("bureau.nodes.reviewer.run_pipeline", return_value=_passing_pipeline()),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.anthropic.Anthropic"),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary([])
        mock_mem_cls.return_value = mock_mem

        result = reviewer_node(state)

    assert result["_route"] == "revise"
    findings = result["reviewer_findings"]
    assert any(f["ref_id"] == "FR-006" for f in findings)


def test_reviewer_node_reads_changed_files_for_review(tmp_path):
    """Reviewer passes actual file contents to run_reviewer."""
    state = _base_state(tmp_path)
    (tmp_path / "src.py").write_text("def foo(): return 42\n")

    with (
        patch("bureau.nodes.reviewer.run_pipeline", return_value=_passing_pipeline()),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.anthropic.Anthropic", return_value=_make_client(_PASS_JSON)),
        patch(
            "bureau.nodes.reviewer.run_reviewer",
            wraps=_real_run_reviewer,
        ) as spy,
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py"], "1 passed")
        mock_mem_cls.return_value = mock_mem

        reviewer_node(state)

    call_kwargs = spy.call_args.kwargs if spy.call_args else {}
    file_contents = call_kwargs.get("file_contents", {})
    assert "src.py" in file_contents
    assert "def foo" in file_contents["src.py"]


def test_reviewer_node_notes_missing_files_but_continues(tmp_path):
    """Reviewer notes a missing file and downgrades pass to revise."""
    state = _base_state(tmp_path)
    (tmp_path / "src.py").write_text("def foo(): return 42\n")

    with (
        patch("bureau.nodes.reviewer.run_pipeline", return_value=_passing_pipeline()),
        patch("bureau.nodes.reviewer.Memory") as mock_mem_cls,
        patch("bureau.nodes.reviewer.anthropic.Anthropic", return_value=_make_client(_PASS_JSON)),
    ):
        mock_mem = MagicMock()
        mock_mem.read.return_value = _summary(["src.py", "missing_file.py"], "1 passed")
        mock_mem_cls.return_value = mock_mem

        result = reviewer_node(state)

    assert result["_route"] == "revise"
    findings = result["reviewer_findings"]
    assert any("missing_file.py" in f["detail"] for f in findings)
