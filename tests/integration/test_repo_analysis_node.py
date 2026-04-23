from __future__ import annotations

from unittest.mock import MagicMock, patch

from bureau.nodes.repo_analysis import repo_analysis_node
from bureau.state import EscalationReason, Phase, make_initial_state


def _make_state(repo_path: str, **overrides):
    state = make_initial_state("run-ra-001", "specs/001/spec.md", repo_path)
    return {**state, **overrides}


def _clean_git():
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    return result


def test_missing_config_escalates(tmp_path):
    state = _make_state(str(tmp_path))
    with patch("bureau.nodes.repo_analysis.subprocess.run", return_value=_clean_git()):
        result = repo_analysis_node(state)
    assert result["_route"] == "escalate"
    assert result["escalations"][-1].reason == EscalationReason.CONFIG_MISSING


def test_dirty_repo_escalates(tmp_path):
    _write_valid_config(tmp_path)
    dirty = MagicMock()
    dirty.returncode = 1
    dirty.stdout = "M some_file.py\n"
    with patch("bureau.nodes.repo_analysis.subprocess.run", return_value=dirty):
        state = _make_state(str(tmp_path))
        result = repo_analysis_node(state)
    assert result["_route"] == "escalate"
    assert result["escalations"][-1].reason == EscalationReason.DIRTY_REPO


def test_clean_repo_routes_ok(tmp_path, monkeypatch):
    _write_valid_config(tmp_path)
    monkeypatch.setattr("bureau.memory.Path.home", lambda: tmp_path)
    with patch("bureau.nodes.repo_analysis.subprocess.run", return_value=_clean_git()):
        with patch("bureau.nodes.repo_analysis.Memory"):
            state = _make_state(str(tmp_path))
            result = repo_analysis_node(state)
    assert result["_route"] == "ok"
    assert result["phase"] == Phase.MEMORY


def _write_valid_config(tmp_path):
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(
        "[runtime]\n"
        'language = "python"\n'
        'base_image = "python:3.14-slim"\n'
        'install_cmd = "pip install -e ."\n'
        'test_cmd = "pytest"\n'
    )
