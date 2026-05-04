from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from bureau.nodes.complete_branch import complete_branch_node

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "t@t.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "t@t.com",
}


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=_GIT_ENV)


@pytest.fixture()
def repo_with_remote(tmp_path: Path):
    """Local repo on a feature branch with a bare remote — no network needed."""
    bare = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    bare.mkdir()
    repo.mkdir()

    _git(["git", "init", "--bare"], bare)
    _git(["git", "init"], repo)
    _git(["git", "config", "user.email", "test@bureau.test"], repo)
    _git(["git", "config", "user.name", "Bureau Test"], repo)
    _git(["git", "remote", "add", "origin", str(bare)], repo)

    (repo / "README.md").write_text("scaffold\n")
    _git(["git", "add", "."], repo)
    _git(["git", "commit", "-m", "init"], repo)
    _git(["git", "push", "-u", "origin", "main"], repo)

    _git(["git", "checkout", "-b", "feat/test-feature-abc12345"], repo)
    return repo


def _make_state(repo_path: str, **overrides):
    base = {
        "run_id": "run-abc12345",
        "repo_path": repo_path,
        "spec_path": "specs/001-test/spec.md",
        "spec": None,
        "branch_name": "feat/test-feature-abc12345",
        "escalations": [],
        "_route": None,
    }
    return {**base, **overrides}


def test_complete_branch_commits_and_pushes_uncommitted_changes(repo_with_remote: Path):
    """Uncommitted changes are staged, committed, and pushed."""
    (repo_with_remote / "src.py").write_text("def hello(): return 'hi'\n")

    state = _make_state(str(repo_with_remote))
    result = complete_branch_node(state)

    assert result["_route"] == "ok"
    log = _git(["git", "log", "--oneline"], repo_with_remote)
    assert "bureau/abc12345" in log.stdout
    remote_log = _git(
        ["git", "log", "--oneline", "origin/feat/test-feature-abc12345"],
        repo_with_remote,
    )
    assert remote_log.returncode == 0


def test_complete_branch_skips_commit_when_builder_committed_everything(repo_with_remote: Path):
    """Builder committed all phases itself — complete_branch skips the empty commit and still pushes."""
    (repo_with_remote / "src.py").write_text("def hello(): return 'hi'\n")
    _git(["git", "add", "."], repo_with_remote)
    _git(["git", "commit", "-m", "feat: builder did all the work"], repo_with_remote)

    commit_count_before = len(
        _git(["git", "log", "--oneline"], repo_with_remote).stdout.strip().splitlines()
    )

    state = _make_state(str(repo_with_remote))
    result = complete_branch_node(state)

    assert result["_route"] == "ok"
    commit_count_after = len(
        _git(["git", "log", "--oneline"], repo_with_remote).stdout.strip().splitlines()
    )
    assert commit_count_after == commit_count_before, "no new commit should have been made"

    remote_log = _git(
        ["git", "log", "--oneline", "origin/feat/test-feature-abc12345"],
        repo_with_remote,
    )
    assert remote_log.returncode == 0
    assert "builder did all the work" in remote_log.stdout
