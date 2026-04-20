# Implementation Plan: Builder Git Workflow

**Branch**: `005-builder-git-workflow` | **Date**: 2026-04-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-builder-git-workflow/spec.md`

## Summary

Add a dedicated `git_commit` node between Critic pass and PR create that branches, stages, commits, and pushes Builder output to the remote. Also add a dirty repo check to `repo_analysis` to catch leftover files before any work begins. No new dependencies — `git` CLI via `subprocess`, same as the existing `gh` CLI pattern.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: `subprocess` (stdlib), `git` CLI (assumed present), `gh` CLI (existing)
**Storage**: LangGraph state (existing `SqliteSaver` checkpoint)
**Testing**: pytest (existing)
**Target Platform**: macOS/Linux (same as existing bureau)
**Project Type**: CLI extension — new LangGraph node + modifications to existing nodes
**Performance Goals**: Git operations complete in < 30s; no impact on LLM phases
**Constraints**: No new Python dependencies; `git` CLI must be on PATH in target environment

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md approved |
| II. Escalate Don't Guess | ✅ PASS | DIRTY_REPO, GIT_PUSH_FAILED, GIT_BRANCH_EXISTS all escalate with structured context |
| III. Verification Gates | ✅ PASS | git_commit node is a gate — PR create only runs after successful push |
| IV. Constitution-First | ✅ PASS | no violations |
| V. Terse Output | ✅ PASS | standard phase events only; no prose |
| VI. Autonomous + Resumability | ✅ PASS | git_commit is a checkpointed node; resumable after critic pass |

## Project Structure

### Documentation (this feature)

```text
specs/005-builder-git-workflow/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── git-commit-node.md
│   └── dirty-repo-check.md
└── tasks.md
```

### Source Code (repository root)

```text
bureau/
├── nodes/
│   ├── git_commit.py          ← new: git branch/add/commit/push node
│   ├── repo_analysis.py       ← modified: add dirty repo check
│   └── pr_create.py           ← modified: read branch_name from state
├── state.py                   ← modified: Phase.GIT_COMMIT, new EscalationReasons, branch_name in initial state
└── graph.py                   ← modified: wire git_commit between critic pass and pr_create

tests/
├── unit/
│   └── test_git_commit_node.py   ← new: unit tests for git_commit_node
└── integration/
    └── test_graph_run.py          ← modified: add dirty repo integration test
```

**Structure Decision**: Single new node file following the existing `bureau/nodes/` pattern. Minimal surface area — four existing files modified, one new file, one new test file.
