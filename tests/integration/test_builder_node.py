from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, ToolMessage

from bureau.models import PipelinePhase, PipelineResult
from bureau.nodes.builder import builder_node
from bureau.state import EscalationReason, RepoContext, make_initial_state

_TASK_PLAN = {
    "tasks": [
        {
            "id": "T001",
            "description": "Add a hello function to bureau/nodes/example.py",
            "fr_ids": ["FR-001"],
            "depends_on": [],
            "files_affected": ["bureau/nodes/example.py"],
            "done": False,
        }
    ],
    "spec_name": "Test Feature",
    "fr_coverage": ["FR-001"],
    "uncovered_frs": [],
    "created_at": "2026-04-18T00:00:00+00:00",
}


def _make_agent(exit_code: int = 0, files: list[str] | None = None) -> MagicMock:
    files = files or []
    messages = []
    for path in files:
        messages.append(
            AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "write_file", "args": {"path": path, "content": "x"}}],
            )
        )
    status = "succeeded" if exit_code == 0 else "failed"
    body = "1 passed" if exit_code == 0 else "1 failed"
    messages.append(
        ToolMessage(
            content=f"{body}\n[Command {status} with exit code {exit_code}]",
            tool_call_id="tc2",
        )
    )
    agent = MagicMock()
    agent.invoke.return_value = {"messages": messages}
    return agent


def _make_skills_root(tmp_path):
    skills_root = tmp_path / "skills" / "default"
    for name in ("build", "test", "ship"):
        d = skills_root / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    return skills_root


def test_builder_node_appends_build_attempt_on_pass(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")
    skills_root = _make_skills_root(tmp_path)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_builder_attempts=3,
    )
    state = make_initial_state("run-b-001", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    with (
        patch("bureau.personas.builder.create_deep_agent", return_value=_make_agent(exit_code=0)),
        patch("bureau.nodes.builder.Memory"),
        patch("bureau.nodes.builder._SKILLS_ROOT", skills_root),
    ):
        result = builder_node(state)

    assert result.get("_route") != "escalate"
    assert len(result["build_attempts"]) == 1
    attempt = result["build_attempts"][0]
    assert attempt["passed"] is True
    assert attempt["round"] == 0
    assert attempt["attempt"] == 0


def test_builder_node_escalates_after_max_attempts(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")
    skills_root = _make_skills_root(tmp_path)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        max_builder_attempts=2,
    )
    state = make_initial_state("run-b-002", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    failing_agent = _make_agent(exit_code=1)

    with (
        patch("bureau.personas.builder.create_deep_agent", return_value=failing_agent),
        patch("bureau.nodes.builder._SKILLS_ROOT", skills_root),
    ):
        result = builder_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.RALPH_EXHAUSTED


def test_builder_node_escalates_on_lint_gate_failure(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")
    skills_root = _make_skills_root(tmp_path)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        lint_cmd="ruff check .",
        max_builder_attempts=3,
    )
    state = make_initial_state("run-b-003", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    failing_lint = PipelineResult(
        passed=False,
        failed_phase=PipelinePhase.LINT,
        failed_output="ruff: E501 line too long",
        phases_run=[PipelinePhase.LINT],
    )

    with (
        patch("bureau.nodes.builder.run_pipeline", return_value=failing_lint),
        patch("bureau.nodes.builder._SKILLS_ROOT", skills_root),
    ):
        result = builder_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.RALPH_EXHAUSTED
    assert "lint" in esc.what_happened


def test_builder_node_escalates_on_build_gate_failure(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")
    skills_root = _make_skills_root(tmp_path)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        build_cmd="tsc --noEmit",
        max_builder_attempts=3,
    )
    state = make_initial_state("run-b-004", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    failing_build = PipelineResult(
        passed=False,
        failed_phase=PipelinePhase.BUILD,
        failed_output="error TS2345: type mismatch",
        phases_run=[PipelinePhase.BUILD],
    )

    with (
        patch("bureau.nodes.builder.run_pipeline", return_value=failing_build),
        patch("bureau.nodes.builder._SKILLS_ROOT", skills_root),
    ):
        result = builder_node(state)

    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert "build" in esc.what_happened


def test_builder_node_gates_only_run_on_first_attempt(tmp_path):
    """Gate failure on attempt 1+ must not escalate — builder broke its own baseline."""
    (tmp_path / "spec.md").write_text("# Test\n")
    skills_root = _make_skills_root(tmp_path)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        build_cmd="tsc --noEmit",
        max_builder_attempts=2,
    )
    state = make_initial_state("run-b-gate-retry", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    passing_gate = PipelineResult(passed=True, phases_run=[PipelinePhase.BUILD])

    pipeline_calls = []

    def _track_pipeline(repo_path, phases, timeout):
        pipeline_calls.append(len(pipeline_calls))
        return passing_gate

    with (
        patch("bureau.nodes.builder.run_pipeline", side_effect=_track_pipeline),
        patch("bureau.personas.builder.create_deep_agent", return_value=_make_agent(exit_code=0)),
        patch("bureau.nodes.builder.Memory"),
        patch("bureau.nodes.builder._SKILLS_ROOT", skills_root),
    ):
        result = builder_node(state)

    assert len(pipeline_calls) == 1, "Gate must only run on attempt 0, not on attempt 1"
    assert result.get("_route") != "escalate"


def test_builder_node_skips_gates_when_lint_build_empty(tmp_path):
    (tmp_path / "spec.md").write_text("# Test\n")
    skills_root = _make_skills_root(tmp_path)

    repo_context = RepoContext(
        language="python",
        base_image="python:3.14-slim",
        install_cmd="",
        test_cmd="pytest",
        lint_cmd="",
        build_cmd="",
        max_builder_attempts=1,
    )
    state = make_initial_state("run-b-005", str(tmp_path / "spec.md"), str(tmp_path))
    state["repo_context"] = repo_context
    state["spec_text"] = "# Test\n"
    state["task_plan"] = _TASK_PLAN

    with (
        patch("bureau.personas.builder.create_deep_agent", return_value=_make_agent(exit_code=0)),
        patch("bureau.nodes.builder.run_pipeline") as mock_pipeline,
        patch("bureau.nodes.builder.Memory"),
        patch("bureau.nodes.builder._SKILLS_ROOT", skills_root),
    ):
        result = builder_node(state)

    mock_pipeline.assert_not_called()
    assert result.get("_route") != "escalate"
