from __future__ import annotations

from unittest.mock import MagicMock, patch

from bureau.nodes.git_commit import git_commit_node
from bureau.state import EscalationReason


def _make_state(**overrides):
    base = {
        "run_id": "run-deaaf184",
        "repo_path": "/tmp/fake-repo",
        "spec_path": "specs/001-smoke-hello-world/spec.md",
        "spec": None,
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


class TestBranchNameDerivation:
    def test_branch_name_from_spec_path(self):
        state = _make_state()
        branch_calls = []

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if "checkout" in cmd:
                branch_calls.append(cmd)
            return result

        with patch("bureau.nodes.git_commit.subprocess.run", side_effect=mock_run):
            git_commit_node(state)

        assert branch_calls, "checkout -b not called"
        branch_arg = branch_calls[0][-1]
        assert branch_arg == "feat/smoke-hello-world-deaaf184", branch_arg

    def test_branch_name_truncation(self):
        state = _make_state(spec_path="specs/001-" + "a" * 60 + "/spec.md")
        branch_calls = []

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if "checkout" in cmd:
                branch_calls.append(cmd)
            return result

        with patch("bureau.nodes.git_commit.subprocess.run", side_effect=mock_run):
            git_commit_node(state)

        branch_arg = branch_calls[0][-1]
        assert len(branch_arg) <= 60, f"Branch too long: {len(branch_arg)} chars"

    def test_spec_name_kebab_case(self):
        spec = MagicMock()
        spec.name = "hello world_feature"
        state = _make_state(spec=spec)
        branch_calls = []

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if "checkout" in cmd:
                branch_calls.append(cmd)
            return result

        with patch("bureau.nodes.git_commit.subprocess.run", side_effect=mock_run):
            git_commit_node(state)

        branch_arg = branch_calls[0][-1]
        assert "hello-world-feature" in branch_arg, branch_arg


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
        with patch("bureau.nodes.git_commit.subprocess.run", side_effect=mock_run):
            out = git_commit_node(state)

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
            branch_name="feat/smoke-hello-world-deaaf184",
            run_summary=None,
            ralph_rounds=[],
            critic_findings=[],
        )
        with patch("bureau.nodes.pr_create.subprocess.run", side_effect=mock_run):
            out = pr_create_node(state)

        assert out["_route"] == "escalate"
        escalation = out["escalations"][-1]
        assert escalation.reason == EscalationReason.PR_FAILED
