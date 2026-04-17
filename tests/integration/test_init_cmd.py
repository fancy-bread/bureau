from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _bureau_exe() -> str:
    return str(Path(sys.executable).parent / "bureau")


def _run_bureau(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bureau_exe(), *args],
        capture_output=True,
        text=True,
    )


def test_init_creates_config(tmp_path: Path) -> None:
    result = _run_bureau("init", "--repo", str(tmp_path))
    assert result.returncode == 0, result.stderr
    config_path = tmp_path / ".bureau" / "config.toml"
    assert config_path.exists(), "config.toml was not created"
    content = config_path.read_text()
    assert "[runtime]" in content
    assert "[bureau]" in content
    assert "language" in content
    assert "base_image" in content
    assert "install_cmd" in content
    assert "test_cmd" in content


def test_init_does_not_overwrite_existing(tmp_path: Path) -> None:
    _run_bureau("init", "--repo", str(tmp_path))
    config_path = tmp_path / ".bureau" / "config.toml"
    original_content = config_path.read_text()
    config_path.write_text("[runtime]\nlanguage = 'python'\n")

    result = _run_bureau("init", "--repo", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "warning" in result.stdout.lower() or "already exists" in result.stdout.lower()
    assert config_path.read_text() != original_content  # our custom content preserved
    assert "language = 'python'" in config_path.read_text()
