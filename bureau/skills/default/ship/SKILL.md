---
name: ship
description: Verify all tasks are complete and implementation is ready for handoff to the Reviewer
---

# Ship Skill

You are in the SHIP phase of the ASDLC pipeline. Your goal is to confirm that the implementation is complete, tests pass, and the output is ready to hand off to the Reviewer.

## Steps

1. **Audit the task list**: Review every task in the task plan. For each task, confirm it has been addressed. A task is addressed if the described change exists in the repository.

2. **Run a final test pass**: Execute the configured test command one final time to confirm the repository is in a green state. Do not proceed to handoff if tests are failing.

3. **Check for uncommitted state**: Verify that all file changes made during this build attempt are accounted for in the files-changed list. Do not leave untracked or partially-written files.

4. **Produce a structured implementation summary**: Write a concise summary that includes:
   - A list of every file created or modified, with a one-line description of what changed
   - The final test exit code and a brief test result summary (e.g., "12 passed, 0 failed")
   - Any tasks that were found to be already complete or not applicable, with a brief explanation

5. **Flag unresolved items**: If any task could not be completed (blocked dependency, ambiguous requirement, external constraint), flag it explicitly in the summary with the reason. Do not silently skip tasks.

## Constraints

- The ship summary is the primary input to the Reviewer. It must be accurate and complete.
- Do not mark a task as complete unless the implementation change is verifiably present in the repository.
- Do not invent or hallucinate file changes that were not made.
- If tests are failing at ship time, report the failure and do not produce a passing summary.
