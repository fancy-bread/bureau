from __future__ import annotations

from unittest.mock import MagicMock, patch

from bureau.nodes.memory_node import memory_node
from bureau.state import Phase, make_initial_state


def _make_state(**overrides):
    state = make_initial_state("run-mem-001", "specs/001/spec.md", "/tmp/repo")
    return {**state, **overrides}


def test_memory_node_advances_to_tasks_loader():
    state = _make_state()
    with patch("bureau.nodes.memory_node.Memory"):
        result = memory_node(state)
    assert result["phase"] == Phase.TASKS_LOADER


def test_memory_node_writes_spec_name_when_spec_present():
    spec = MagicMock()
    spec.name = "My Feature"
    state = _make_state(spec=spec)
    mock_mem = MagicMock()
    with patch("bureau.nodes.memory_node.Memory", return_value=mock_mem):
        memory_node(state)
    mock_mem.write.assert_called_once_with("spec_summary", "My Feature")


def test_memory_node_no_write_when_no_spec():
    state = _make_state(spec=None)
    mock_mem = MagicMock()
    with patch("bureau.nodes.memory_node.Memory", return_value=mock_mem):
        memory_node(state)
    mock_mem.write.assert_not_called()
