from __future__ import annotations

from bureau.models import PipelinePhase
from bureau.personas.reviewer import has_assertions
from bureau.tools.pipeline import run_pipeline


class TestHasAssertions:
    def test_bare_assert_keyword(self):
        assert has_assertions("def test_foo():\n    assert result == 42\n")

    def test_assert_with_message(self):
        assert has_assertions("assert foo.bar() == expected, 'should be expected'")

    def test_unittest_assert_equal(self):
        assert has_assertions("self.assertEqual(result, 42)")

    def test_unittest_assert_in(self):
        assert has_assertions("self.assertIn(item, collection)")

    def test_unittest_assert_true(self):
        assert has_assertions("self.assertTrue(condition)")

    def test_pytest_raises(self):
        assert has_assertions("with pytest.raises(ValueError):\n    foo()")

    def test_pytest_approx(self):
        assert has_assertions("assert result == pytest.approx(3.14)")

    def test_pass_only_body_returns_false(self):
        assert not has_assertions("def test_foo():\n    pass\n")

    def test_empty_file_returns_false(self):
        assert not has_assertions("")

    def test_no_test_functions_returns_false(self):
        assert not has_assertions("def foo():\n    return 42\n")

    def test_only_pass_body_returns_false(self):
        assert not has_assertions("def test_foo():\n    pass\n\ndef test_bar():\n    pass\n")

    def test_multiline_test_with_assertion(self):
        code = "def test_greet():\n    result = greet('world')\n    assert result == 'hello world'\n"
        assert has_assertions(code)


class TestRunPipeline:
    def test_all_phases_pass(self, tmp_path):
        phases = [
            (PipelinePhase.LINT, "true"),
            (PipelinePhase.TEST, "true"),
        ]
        result = run_pipeline(str(tmp_path), phases, timeout=10)
        assert result.passed is True
        assert result.failed_phase is None
        assert set(result.phases_run) == {PipelinePhase.LINT, PipelinePhase.TEST}

    def test_stops_at_first_failure(self, tmp_path):
        phases = [
            (PipelinePhase.LINT, "false"),
            (PipelinePhase.TEST, "true"),
        ]
        result = run_pipeline(str(tmp_path), phases, timeout=10)
        assert result.passed is False
        assert result.failed_phase == PipelinePhase.LINT
        assert PipelinePhase.TEST not in result.phases_run

    def test_failed_output_included(self, tmp_path):
        phases = [(PipelinePhase.BUILD, "echo 'type error' && exit 1")]
        result = run_pipeline(str(tmp_path), phases, timeout=10)
        assert result.passed is False
        assert "type error" in result.failed_output

    def test_failed_output_truncated_to_2000_chars(self, tmp_path):
        long_msg = "x" * 5000
        phases = [(PipelinePhase.TEST, f"echo '{long_msg}' && exit 1")]
        result = run_pipeline(str(tmp_path), phases, timeout=10)
        assert len(result.failed_output) <= 2000

    def test_empty_phases_list_passes(self, tmp_path):
        result = run_pipeline(str(tmp_path), [], timeout=10)
        assert result.passed is True
        assert result.phases_run == []
