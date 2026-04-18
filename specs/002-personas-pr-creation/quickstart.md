# Quickstart: Bureau Personas and PR Creation

**Date**: 2026-04-18 | **Branch**: `002-personas-pr-creation`

Integration scenarios for validating the full persona pipeline end-to-end.

---

## Prerequisites

- bureau installed: `pip install -e ".[dev]"`
- `ANTHROPIC_API_KEY` set in environment
- `gh` CLI installed and authenticated (`gh auth status`)
- A target test repo with:
  - `.bureau/config.toml` configured
  - At least one passing test (`test_cmd` exits 0 before bureau runs)
  - A GitHub remote (`git remote -v` shows `origin`)

---

## Scenario 1: Happy Path — Full Pipeline

**Goal**: Bureau runs the complete pipeline and opens a PR.

```sh
cd /path/to/target-repo
bureau run /path/to/specs/002-*/spec.md
```

**Expected output**:
```
[bureau] run.started  id=run-<id>  spec=...  repo=.
[bureau] phase.started  phase=validate_spec
[bureau] phase.completed  phase=validate_spec  duration=...
[bureau] phase.started  phase=repo_analysis
[bureau] phase.completed  phase=repo_analysis  duration=...
[bureau] phase.started  phase=memory
[bureau] phase.completed  phase=memory  duration=...
[bureau] phase.started  phase=planner
[bureau] phase.completed  phase=planner  duration=...
[bureau] ralph.started  phase=builder  round=0
[bureau] ralph.attempt  phase=builder  round=0  attempt=0  result=pass
[bureau] phase.started  phase=critic
[bureau] phase.completed  phase=critic  duration=...
[bureau] ralph.completed  rounds=1  verdict=pass
[bureau] phase.started  phase=pr_create
[bureau] phase.completed  phase=pr_create  duration=...
[bureau] run.completed  id=run-<id>  pr=https://github.com/org/repo/pull/<N>  duration=...
```

**Verify**:
- [ ] PR is open on GitHub with correct title and run summary in description
- [ ] PR description contains run ID, spec name, FRs addressed, Critic verdict
- [ ] `bureau show <run-id>` shows `status=complete`

---

## Scenario 2: Builder Retries Within a Round

**Goal**: Builder fails on first attempt, succeeds on second — Critic passes.

Arrange: Target repo has a test that will fail until a specific change is made. The spec requires that change.

**Expected events (partial)**:
```
[bureau] ralph.started  phase=builder  round=0
[bureau] ralph.attempt  phase=builder  round=0  attempt=0  result=fail
[bureau] ralph.attempt  phase=builder  round=0  attempt=1  result=pass
[bureau] phase.started  phase=critic
[bureau] phase.completed  phase=critic  ...
[bureau] ralph.completed  rounds=1  verdict=pass
```

**Verify**:
- [ ] `ralph.attempt round=0 attempt=0 result=fail` appears in stdout
- [ ] `ralph.attempt round=0 attempt=1 result=pass` appears in stdout
- [ ] Final PR is opened successfully

---

## Scenario 3: Critic Issues `revise`, Builder Succeeds on Round 2

**Goal**: First Critic round returns `revise`; Builder corrects; second Critic round returns `pass`.

Arrange: Spec has a requirement the Builder's first implementation misses.

**Expected events (partial)**:
```
[bureau] ralph.started  phase=builder  round=0
[bureau] ralph.attempt  phase=builder  round=0  attempt=0  result=pass
[bureau] phase.started  phase=critic
[bureau] phase.completed  phase=critic  duration=...
[bureau] ralph.started  phase=builder  round=1
[bureau] ralph.attempt  phase=builder  round=1  attempt=0  result=pass
[bureau] phase.started  phase=critic
[bureau] phase.completed  phase=critic  duration=...
[bureau] ralph.completed  rounds=2  verdict=pass
```

**Verify**:
- [ ] Two `ralph.started` events with `round=0` and `round=1`
- [ ] `ralph.completed rounds=2 verdict=pass`
- [ ] PR description shows `ralph_rounds=2`

---

## Scenario 4: Ralph Loop Exhaustion → Escalation

**Goal**: Builder never reaches passing tests; bureau escalates after max rounds.

Arrange: Target repo's `test_cmd` always exits non-zero regardless of changes.

**Expected output (partial)**:
```
[bureau] ralph.attempt  phase=builder  round=2  attempt=2  result=fail
[bureau] run.escalated  id=run-<id>  phase=builder  reason=RALPH_EXHAUSTED

  What happened:  Builder exhausted 3 attempts in round 2 without a passing test run.
  What's needed:  Review the failing tests and provide guidance on the approach.
  ...
```

**Verify**:
- [ ] `reason=RALPH_EXHAUSTED` in escalation
- [ ] `bureau show <run-id>` shows `status=paused`
- [ ] `bureau resume <run-id> --response "..."` restarts from the paused round

---

## Scenario 5: Constitution Violation → Escalation (no `revise`)

**Goal**: Critic detects a constitution violation and escalates rather than issuing `revise`.

Arrange: Spec requires a change that violates a constitution principle (e.g. skips a verification gate).

**Expected output (partial)**:
```
[bureau] run.escalated  id=run-<id>  phase=critic  reason=CONSTITUTION_VIOLATION

  What happened:  Critic detected a constitution violation: ...
  What's needed:  Revise the spec to remove the violating requirement.
  ...
```

**Verify**:
- [ ] `reason=CONSTITUTION_VIOLATION` — not `RALPH_ROUNDS_EXCEEDED`
- [ ] No PR is opened
- [ ] `bureau show <run-id>` shows `status=paused`
