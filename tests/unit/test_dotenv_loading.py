from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_key_loaded_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-from-file\n")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    import os

    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-from-file"
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_shell_env_takes_precedence(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-from-file\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-shell")

    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    import os

    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-from-shell"


def test_missing_env_file_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    missing = tmp_path / "nonexistent.env"

    from dotenv import load_dotenv

    load_dotenv(missing, override=False)


def test_missing_key_exits_with_readable_error(tmp_path, monkeypatch):
    import shutil

    bureau_exe = shutil.which("bureau") or str(Path(sys.executable).parent / "bureau")
    # Override HOME so dotenv cannot load the real ~/.bureau/.env
    env = {
        k: v for k, v in __import__("os").environ.items()
        if k != "ANTHROPIC_API_KEY"
    }
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        [bureau_exe, "run", "spec.md"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "ANTHROPIC_API_KEY" in result.stderr
    assert "~/.bureau/.env" in result.stderr
