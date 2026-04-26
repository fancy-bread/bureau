# Contract: Pipeline Execution

**Module**: `bureau/tools/pipeline.py`  
**Feature**: 012-pipeline-reviewer-depth

## `run_pipeline(repo_path, phases, timeout) -> PipelineResult`

Executes a list of `(phase_name, command)` pairs in strict order. Stops at the first non-zero exit code.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo_path` | `str` | Absolute path to the target repo (passed to `execute_shell_tool`) |
| `phases` | `list[tuple[PipelinePhase, str]]` | Ordered list of (phase, command) pairs; empty-command phases must be pre-filtered by the caller |
| `timeout` | `int` | Seconds; applied uniformly to all phases via `execute_shell_tool` |

### Return value

```python
PipelineResult(
    passed=True,           # all phases exited 0
    failed_phase=None,
    failed_output="",
    phases_run=[PipelinePhase.LINT, PipelinePhase.TEST],
)

PipelineResult(
    passed=False,
    failed_phase=PipelinePhase.LINT,
    failed_output="ruff check . failed: ...",  # max 2000 chars
    phases_run=[PipelinePhase.LINT],            # only phases that ran
)
```

### Invariants

- Phases are executed in the order provided; caller is responsible for correct ordering.
- Phases whose command string is empty or whitespace-only MUST be excluded before calling (caller responsibility, not enforced inside).
- On first failure, subsequent phases are NOT executed.
- `failed_output` is truncated to 2000 characters if longer.

---

## Builder Integration Contract

The builder node calls `run_pipeline` within each attempt loop with phases `[LINT, BUILD]` (TEST is handled by `run_builder_attempt`). Install is called once per round before the loop.

```python
# Before each attempt
lint_build_phases = [
    (PipelinePhase.LINT, repo_context.lint_cmd),
    (PipelinePhase.BUILD, repo_context.build_cmd),
]
active = [(p, cmd) for p, cmd in lint_build_phases if cmd.strip()]
if active:
    result = run_pipeline(repo_path, active, timeout)
    if not result.passed:
        # escalate with result.failed_phase and result.failed_output
```

---

## Reviewer Integration Contract

The reviewer node calls `run_pipeline` with all four phases before its LLM review call.

```python
all_phases = [
    (PipelinePhase.INSTALL, repo_context.install_cmd),
    (PipelinePhase.LINT, repo_context.lint_cmd),
    (PipelinePhase.BUILD, repo_context.build_cmd),
    (PipelinePhase.TEST, repo_context.test_cmd),
]
active = [(p, cmd) for p, cmd in all_phases if cmd.strip()]
result = run_pipeline(repo_path, active, timeout)
if not result.passed:
    # issue revise verdict; do not proceed to LLM review
```

---

## Test Quality Gate Contract

Applied by the reviewer persona to every test file in `files_changed`.

```python
def has_assertions(file_content: str) -> bool:
    """Returns True if the file contains at least one assertion."""
    ...
```

**Assertion patterns detected**:
- `assert ` (bare keyword, word boundary)
- `self.assert` prefix (unittest-style)
- `pytest.raises` / `pytest.approx`

**Contract**: If `has_assertions()` returns False for any file whose path matches `test_*.py` or `*_test.py`, the reviewer MUST include a `TestQualityFinding` and set verdict to `revise`.
