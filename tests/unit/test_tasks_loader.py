from __future__ import annotations

from pathlib import Path

from bureau.nodes.tasks_loader import tasks_loader_node
from bureau.state import EscalationReason


def _state(tasks_path: str, spec_folder: str = "") -> dict:
    return {
        "run_id": "run-test-001",
        "spec_path": "",
        "repo_path": "",
        "tasks_path": tasks_path,
        "spec_folder": spec_folder,
        "plan_text": "",
        "escalations": [],
    }


def test_tasks_missing_no_file():
    result = tasks_loader_node(_state(tasks_path="/nonexistent/tasks.md"))
    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.TASKS_MISSING


def test_tasks_complete_all_checked(tmp_path: Path):
    tasks_md = tmp_path / "tasks.md"
    tasks_md.write_text("- [x] T001 Done task\n- [x] T002 Also done\n")
    result = tasks_loader_node(_state(tasks_path=str(tasks_md), spec_folder=str(tmp_path)))
    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.TASKS_COMPLETE


def test_tasks_parsed_correctly(tmp_path: Path):
    tasks_md = tmp_path / "tasks.md"
    tasks_md.write_text(
        "- [ ] T001 First task\n"
        "- [ ] T002 Second task\n"
        "- [ ] T003 Third task\n"
    )
    result = tasks_loader_node(_state(tasks_path=str(tasks_md), spec_folder=str(tmp_path)))
    assert result["_route"] == "ok"
    tasks = result["task_plan"]["tasks"]
    assert len(tasks) == 3
    assert [t["id"] for t in tasks] == ["T001", "T002", "T003"]


def test_plan_text_loaded(tmp_path: Path):
    tasks_md = tmp_path / "tasks.md"
    tasks_md.write_text("- [ ] T001 A task\n")
    plan_md = tmp_path / "plan.md"
    plan_md.write_text("# Plan\n\nThis is the implementation plan.\n")
    result = tasks_loader_node(_state(tasks_path=str(tasks_md), spec_folder=str(tmp_path)))
    assert result["_route"] == "ok"
    assert "implementation plan" in result["plan_text"]


def test_file_with_no_checkboxes(tmp_path: Path):
    tasks_md = tmp_path / "tasks.md"
    tasks_md.write_text("# Tasks\n\nSome prose with no checkboxes.\n")
    result = tasks_loader_node(_state(tasks_path=str(tasks_md), spec_folder=str(tmp_path)))
    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.TASKS_MISSING
