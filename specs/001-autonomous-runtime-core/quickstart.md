# Quickstart: Bureau CLI Foundation

**Feature**: Bureau CLI Foundation | **Date**: 2026-04-16

This quickstart validates the foundation feature end-to-end. Steps use stub personas —
no LLM calls are made and no real PR is opened.

---

## Prerequisites

- Python 3.12
- A target repo with (or without) `.bureau/config.toml` — you'll create one with `bureau init`
- A valid Spec Kit spec file (e.g. `specs/001-autonomous-runtime-core/spec.md` in this repo)

---

## 1. Install bureau

```bash
cd bureau/
pip install -e .
bureau --help
```

Expected: Help text listing `run`, `resume`, `list`, `show`, `abort`, `init` commands.

---

## 2. Scaffold a target repo

```bash
bureau init --repo /path/to/target-repo
```

Expected output:
```
Created /path/to/target-repo/.bureau/config.toml
Edit it to fill in FILL_IN placeholders before running bureau.
```

Edit the scaffolded file to replace `FILL_IN` values with real values for your repo.

---

## 3. Run bureau against a spec

```bash
bureau run specs/001-autonomous-runtime-core/spec.md --repo /path/to/target-repo
```

Expected output (stub run):
```
[bureau] run.started  id=run-a3f2b1c9  spec=specs/001-autonomous-runtime-core/spec.md  repo=/path/to/target-repo
[bureau] phase.started  phase=validate_spec
[bureau] phase.completed  phase=validate_spec  duration=0.1s
[bureau] phase.started  phase=repo_analysis
[bureau] phase.completed  phase=repo_analysis  duration=0.0s
[bureau] phase.started  phase=memory
[bureau] phase.completed  phase=memory  duration=0.0s
[bureau] phase.started  phase=planner  stub=true
[bureau] phase.completed  phase=planner  duration=0.0s  stub=true
[bureau] phase.started  phase=builder  stub=true
[bureau] phase.completed  phase=builder  duration=0.0s  stub=true
[bureau] phase.started  phase=critic  stub=true
[bureau] phase.completed  phase=critic  duration=0.0s  stub=true
[bureau] phase.started  phase=pr_create  stub=true
[bureau] phase.completed  phase=pr_create  duration=0.0s  stub=true
[bureau] run.completed  id=run-a3f2b1c9  duration=0.3s
```

Note the run ID — you'll need it for the resume test.

---

## 4. Verify checkpointing and resume

Interrupt the run mid-graph by adding a temporary `assert False` in the `builder` stub node,
re-running, then resuming:

```bash
# After the interrupted run prints phase.completed for repo_analysis:
bureau resume run-<id>
```

Expected: Execution continues from `memory` node (or wherever it was interrupted); does not
replay `validate_spec` or `repo_analysis`.

---

## 5. Verify spec rejection

```bash
# Temporarily add [NEEDS CLARIFICATION: test] to a FR in the spec
bureau run specs/001-autonomous-runtime-core/spec.md --repo /path/to/target-repo
```

Expected output:
```
[bureau] run.started  id=run-b4e3a2d1  ...
[bureau] phase.started  phase=validate_spec
[bureau] run.escalated  id=run-b4e3a2d1  phase=validate_spec  reason=SPEC_INVALID

  What happened:  Spec contains [NEEDS CLARIFICATION] markers in functional requirements.
  ...
```

---

## 6. Verify `bureau init` does not overwrite

```bash
bureau init --repo /path/to/target-repo
```

Expected (config already exists):
```
Warning: .bureau/config.toml already exists. Not overwriting.
```
