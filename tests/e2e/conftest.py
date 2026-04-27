from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values

_bureau_env_file = Path.home() / ".bureau" / ".env"

SKIP_NO_REPO = pytest.mark.skipif(
    not (os.environ.get("BUREAU_TEST_REPO_PYTHON") or os.environ.get("BUREAU_TEST_REPO")),
    reason="BUREAU_TEST_REPO_PYTHON not set",
)

SKIP_NO_TYPESCRIPT_REPO = pytest.mark.skipif(
    not os.environ.get("BUREAU_TEST_REPO_TYPESCRIPT"),
    reason="BUREAU_TEST_REPO_TYPESCRIPT not set",
)

SKIP_NO_KEY = pytest.mark.skipif(
    not (
        os.environ.get("ANTHROPIC_API_KEY")
        or (_bureau_env_file.exists() and "ANTHROPIC_API_KEY" in dotenv_values(_bureau_env_file))
    ),
    reason="ANTHROPIC_API_KEY not set in shell or ~/.bureau/.env",
)


@pytest.fixture(scope="session")
def _bureau_test_repo_path():
    repo_path = os.environ.get("BUREAU_TEST_REPO_PYTHON") or os.environ.get("BUREAU_TEST_REPO")
    assert repo_path, "BUREAU_TEST_REPO_PYTHON must be set"
    assert Path(repo_path).exists(), f"BUREAU_TEST_REPO_PYTHON path does not exist: {repo_path}"
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=True)
    subprocess.run(["git", "-C", repo_path, "pull"], check=True)
    yield repo_path
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=False)


@pytest.fixture()
def bureau_test_repo(_bureau_test_repo_path):
    """Reset to main before each test so stale feature branches don't bleed across tests."""
    subprocess.run(["git", "-C", _bureau_test_repo_path, "checkout", "main"], check=True)
    subprocess.run(["git", "-C", _bureau_test_repo_path, "reset", "--hard", "origin/main"], check=True)
    return _bureau_test_repo_path


@pytest.fixture(scope="session")
def _bureau_test_typescript_repo_path():
    repo_path = os.environ.get("BUREAU_TEST_REPO_TYPESCRIPT")
    assert repo_path, "BUREAU_TEST_REPO_TYPESCRIPT must be set"
    assert Path(repo_path).exists(), f"BUREAU_TEST_REPO_TYPESCRIPT path does not exist: {repo_path}"
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=True)
    subprocess.run(["git", "-C", repo_path, "pull"], check=True)
    yield repo_path
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=False)


@pytest.fixture()
def bureau_test_typescript_repo(_bureau_test_typescript_repo_path):
    """Reset to main before each test so stale feature branches don't bleed across tests."""
    subprocess.run(["git", "-C", _bureau_test_typescript_repo_path, "checkout", "main"], check=True)
    subprocess.run(
        ["git", "-C", _bureau_test_typescript_repo_path, "reset", "--hard", "origin/main"], check=True
    )
    return _bureau_test_typescript_repo_path


def bureau_exe() -> str:
    exe = shutil.which("bureau")
    if exe:
        return exe
    candidate = Path(__import__("sys").executable).parent / "bureau"
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("bureau executable not found")


def run_bureau(spec_path: str, repo_path: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run bureau and stream its output to the console while also capturing it for assertions."""
    import io
    import threading

    proc = subprocess.Popen(
        [bureau_exe(), "run", spec_path, "--repo", repo_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    buf = io.StringIO()

    def _stream() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            buf.write(line)

    t = threading.Thread(target=_stream, daemon=True)
    t.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
    t.join()

    captured = buf.getvalue()
    return subprocess.CompletedProcess(
        args=proc.args,
        returncode=proc.returncode or 0,
        stdout=captured,
        stderr="",
    )
