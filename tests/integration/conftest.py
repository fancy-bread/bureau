import pytest


@pytest.fixture(autouse=True)
def isolate_runs_dir(tmp_path, monkeypatch):
    """Redirect all run storage to a temp directory for every integration test."""
    monkeypatch.setattr("bureau.run_manager._runs_dir", lambda: tmp_path / "runs")
