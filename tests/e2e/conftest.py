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

SKIP_NO_KEY = pytest.mark.skipif(
    not (
        os.environ.get("ANTHROPIC_API_KEY")
        or (_bureau_env_file.exists() and "ANTHROPIC_API_KEY" in dotenv_values(_bureau_env_file))
    ),
    reason="ANTHROPIC_API_KEY not set in shell or ~/.bureau/.env",
)


@pytest.fixture(scope="session")
def bureau_test_repo():
    repo_path = os.environ.get("BUREAU_TEST_REPO_PYTHON") or os.environ.get("BUREAU_TEST_REPO")
    assert repo_path, "BUREAU_TEST_REPO_PYTHON must be set"
    assert Path(repo_path).exists(), f"BUREAU_TEST_REPO_PYTHON path does not exist: {repo_path}"
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=True)
    subprocess.run(["git", "-C", repo_path, "pull"], check=True)
    yield repo_path
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=False)


def bureau_exe() -> str:
    exe = shutil.which("bureau")
    if exe:
        return exe
    candidate = Path(__import__("sys").executable).parent / "bureau"
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("bureau executable not found")


def run_bureau(spec_path: str, repo_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [bureau_exe(), "run", spec_path, "--repo", repo_path],
        capture_output=True,
        text=True,
        timeout=600,
    )
