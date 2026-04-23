from __future__ import annotations

import pytest

from bureau.memory import Memory


def test_write_and_read(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.memory.Path.home", lambda: tmp_path)
    mem = Memory("run-abc")
    mem.write("key", "value")
    assert mem.read("key") == "value"


def test_read_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.memory.Path.home", lambda: tmp_path)
    mem = Memory("run-abc")
    with pytest.raises(KeyError):
        mem.read("missing")


def test_write_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.memory.Path.home", lambda: tmp_path)
    mem = Memory("run-abc")
    mem.write("k", 1)
    mem.write("k", 2)
    assert mem.read("k") == 2


def test_summary_returns_empty_string(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.memory.Path.home", lambda: tmp_path)
    mem = Memory("run-abc")
    assert mem.summary() == ""


def test_initialises_empty_json_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bureau.memory.Path.home", lambda: tmp_path)
    Memory("run-new")
    path = tmp_path / ".bureau" / "runs" / "run-new" / "memory.json"
    assert path.exists()
    assert path.read_text() == "{}"
