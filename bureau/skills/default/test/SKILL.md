---
name: test
description: Execute the configured test suite and interpret results, retrying on failure
---

# Test Skill

You are in the TEST phase of the ASDLC pipeline. Your goal is to run the configured test command, interpret the results, and ensure the test suite passes before handing off to the next phase.

## Steps

1. **Run the test command**: Execute the configured `test_cmd` exactly as specified. Do not modify or abbreviate it.

2. **Parse the exit code**: A zero exit code means all tests passed. Any non-zero exit code means the test run failed.

3. **Extract failing test names**: If the exit code is non-zero, read the output carefully to identify which specific tests failed and why. Look for assertion errors, import errors, or missing files.

4. **Locate root causes**: For each failing test, trace the failure back to its root cause in the implementation code. Do not modify tests to make them pass — fix the implementation.

5. **Apply targeted fixes**: Make the minimum change necessary to fix each root cause. Re-read affected files before editing.

6. **Re-run until green**: After each fix, re-run the full test command. Repeat until the exit code is 0.

7. **Report the outcome**: Once tests pass, report the final exit code, the number of tests that passed, and any warnings emitted by the test runner.

## Constraints

- Maximum retry attempts are set by the builder configuration. Stop retrying and report the last failure output when the limit is reached.
- Do not skip, ignore, or comment out failing tests.
- Do not modify test files to change assertions or expected values, unless a task explicitly requires updating tests.
- If a test failure reveals a genuine ambiguity in the spec, stop and report the ambiguity rather than guessing at the correct behavior.
