from __future__ import annotations

from unittest.mock import MagicMock, patch

from bureau.nodes.complete_branch import complete_branch_node
from bureau.state import EscalationReason


def _make_state(**overrides):
    base = {
        "run_id": "run-deaaf184",
        "repo_path": "/tmp/fake-repo",
        "spec_path": "specs/001-smoke-hello-world/spec.md",
        "spec": None,
        "branch_name": "feat/smoke-hello-world-deaaf184",
        "escalations": [],
        "_route": None,
    }
    return {**base, **overrides}


def _mock_run_success(cmd, **kwargs):
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


def _mock_run_with_staged_changes(cmd, **kwargs):
    """Simulate staged changes present (diff --cached exits 1) and all else succeeds."""
    result = MagicMock()
    result.returncode = 1 if "diff" in cmd else 0
    result.stdout = ""
    result.stderr = ""
    return result


def _mock_run_clean_tree(cmd, **kwargs):
    """Simulate clean working tree (diff --cached exits 0 = nothing staged)."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


class TestGitCommitNode:
    def test_commits_and_pushes_on_existing_branch(self):
        cmds = []

        def mock_run(cmd, **kwargs):
            cmds.append(cmd)
            return _mock_run_with_staged_changes(cmd, **kwargs)

        state = _make_state()
        with patch("bureau.nodes.complete_branch.subprocess.run", side_effect=mock_run):
            out = complete_branch_node(state)

        assert out["_route"] == "ok"
        assert out["phase"].value == "pr_create"
        add_cmds = [c for c in cmds if "add" in c]
        commit_cmds = [c for c in cmds if "commit" in c]
        push_cmds = [c for c in cmds if "push" in c]
        assert add_cmds
        assert commit_cmds
        assert push_cmds
        assert "feat/smoke-hello-world-deaaf184" in push_cmds[0]

    def test_skips_commit_when_tree_already_clean(self):
        """Builder committed everything incrementally — complete_branch skips commit, still pushes."""
        cmds = []

        def mock_run(cmd, **kwargs):
            cmds.append(cmd)
            return _mock_run_clean_tree(cmd, **kwargs)

        state = _make_state()
        with patch("bureau.nodes.complete_branch.subprocess.run", side_effect=mock_run):
            out = complete_branch_node(state)

        assert out["_route"] == "ok"
        commit_cmds = [c for c in cmds if "commit" in c and "diff" not in c]
        push_cmds = [c for c in cmds if "push" in c]
        assert not commit_cmds
        assert push_cmds

    def test_commit_message_format(self):
        commit_msgs = []

        def mock_run(cmd, **kwargs):
            if "commit" in cmd and "diff" not in cmd:
                commit_msgs.append(cmd)
            return _mock_run_with_staged_changes(cmd, **kwargs)

        state = _make_state()
        with patch("bureau.nodes.complete_branch.subprocess.run", side_effect=mock_run):
            complete_branch_node(state)

        assert commit_msgs
        msg = commit_msgs[0][-1]
        assert "smoke-hello-world" in msg
        assert "deaaf184" in msg


class TestPushFailureEscalation:
    def test_push_failure_escalation(self):
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if "push" in cmd:
                result.returncode = 1
                result.stderr = "fatal: 'origin' does not appear to be a git repository"
            return result

        state = _make_state()
        with patch("bureau.nodes.complete_branch.subprocess.run", side_effect=mock_run):
            out = complete_branch_node(state)

        assert out["_route"] == "escalate"
        escalation = out["escalations"][-1]
        assert escalation.reason == EscalationReason.GIT_PUSH_FAILED
        assert "git push" in escalation.what_happened
        assert "origin" in escalation.what_happened


class TestPrFailedEscalationIntact:
    def test_pr_failed_escalation_intact(self):
        from bureau.nodes.pr_create import pr_create_node

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 1
            result.stdout = ""
            result.stderr = "GraphQL: Not Found"
            return result

        state = _make_state(
            run_summary=None,
            ralph_rounds=[],
            reviewer_findings=[],
        )
        with patch("bureau.nodes.pr_create.subprocess.run", side_effect=mock_run):
            out = pr_create_node(state)

        assert out["_route"] == "escalate"
        escalation = out["escalations"][-1]
        assert escalation.reason == EscalationReason.PR_FAILED
