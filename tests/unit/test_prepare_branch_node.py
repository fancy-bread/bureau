from __future__ import annotations

from unittest.mock import MagicMock, patch

from bureau.nodes.prepare_branch import prepare_branch_node
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


def _mock_checkout_success(cmd, **kwargs):
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

        with patch("bureau.nodes.prepare_branch.subprocess.run", side_effect=mock_run):
            out = prepare_branch_node(state)

        assert branch_calls, "checkout -b not called"
        assert out["branch_name"] == "feat/smoke-hello-world-deaaf184"

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

        with patch("bureau.nodes.prepare_branch.subprocess.run", side_effect=mock_run):
            out = prepare_branch_node(state)

        assert len(out["branch_name"]) <= 60

    def test_spec_name_kebab_case(self):
        spec = MagicMock()
        spec.name = "hello world_feature"
        state = _make_state(spec=spec)

        with patch("bureau.nodes.prepare_branch.subprocess.run", side_effect=_mock_checkout_success):
            out = prepare_branch_node(state)

        assert "hello-world-feature" in out["branch_name"]

    def test_branch_name_stored_in_state(self):
        state = _make_state()

        with patch("bureau.nodes.prepare_branch.subprocess.run", side_effect=_mock_checkout_success):
            out = prepare_branch_node(state)

        assert out["branch_name"] == "feat/smoke-hello-world-deaaf184"
        assert out["_route"] == "ok"


class TestBranchCollisionHandling:
    def test_retries_on_already_exists(self):
        attempts = []

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if "checkout" in cmd:
                attempts.append(cmd[-1])
                if len(attempts) == 1:
                    result.returncode = 1
                    result.stderr = "fatal: A branch named 'feat/...' already exists."
                else:
                    result.returncode = 0
                    result.stderr = ""
            else:
                result.returncode = 0
                result.stderr = ""
            result.stdout = ""
            return result

        state = _make_state()
        with patch("bureau.nodes.prepare_branch.subprocess.run", side_effect=mock_run):
            out = prepare_branch_node(state)

        assert out["_route"] == "ok"
        assert len(attempts) == 2
        assert attempts[1].endswith("-2")

    def test_escalates_after_three_collisions(self):
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 1
            result.stderr = "fatal: A branch named 'feat/...' already exists."
            result.stdout = ""
            return result

        state = _make_state()
        with patch("bureau.nodes.prepare_branch.subprocess.run", side_effect=mock_run):
            out = prepare_branch_node(state)

        assert out["_route"] == "escalate"
        assert out["escalations"][-1].reason == EscalationReason.GIT_BRANCH_EXISTS
