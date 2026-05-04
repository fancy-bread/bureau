# Implementation Plan: Reviewer Hardening and Branch Lifecycle

**Branch**: `013-reviewer-hardening-branch-lifecycle` | **Date**: 2026-05-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/013-reviewer-hardening-branch-lifecycle/spec.md`

> **Retrospective note**: All implementation described here is already on `main`. This plan documents the decisions and structure of work completed on the `test/dotnet-e2e` branch.

## Summary

Three coordinated improvements to bureau's correctness and observability: (1) the Reviewer is hardened against hallucinated FR IDs and masked builder escalations, with internal findings given sentinel ref_ids that cannot collide with spec FRs; (2) the pipeline is reordered so the feature branch is created before the Builder starts, with node names updated to `prepare_branch` / `complete_branch` to reflect their purpose; (3) dotnet e2e infrastructure is added at parity with Python and TypeScript, validated by an end-to-end run against `bureau-test-dotnet`.

## Technical Context

**Language/Version**: Python 3.14  
**Primary Dependencies**: LangGraph 0.2+, deepagents, anthropic>=0.25, pydantic>=2, pytest, confluent-kafka (optional)  
**Storage**: SQLite (LangGraph checkpoint), JSON (memory scratchpad)  
**Testing**: pytest — unit, integration, e2e tiers; `make ci` runs unit + integration  
**Target Platform**: Host (Linux/macOS); no container execution  
**Project Type**: CLI / autonomous agent runtime  
**Performance Goals**: Correctness gates are the constraint; no latency SLOs  
**Constraints**: LangGraph default recursion limit (100 steps); `max_rounds` / `max_builder_attempts` configurable per run  
**Scale/Scope**: Single-run sequential execution; parallel runs deferred to v2

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Spec-First Execution | ✅ Pass | Retrospective spec created; all changes traced to spec FRs |
| II. Escalate-Don't-Guess | ✅ Pass | Hallucination stripping surfaces real findings; builder pass-through prevents silent escalation masking |
| III. Verification Gates | ✅ Pass | 191 unit/integration tests pass; e2e validates end-to-end PR creation |
| IV. Constitution-First Compliance | ✅ Pass | No constitution violations introduced |
| V. Terse Structured Output | ✅ Pass | New events (`reviewer.pipeline`, `reviewer.verdict`) follow existing schema conventions |
| VI. Autonomous Operation | ✅ Pass | No new mid-run permission requests; branch creation is autonomous |

**Post-design re-check**: ✅ All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/013-reviewer-hardening-branch-lifecycle/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── events.md
└── tasks.md
```

### Source Code (affected files)

```text
bureau/
├── events.py                           # +REVIEWER_PIPELINE, +REVIEWER_VERDICT constants
├── graph.py                            # prepare_branch + complete_branch nodes wired
├── state.py                            # Phase.PREPARE_BRANCH, Phase.COMPLETE_BRANCH
├── nodes/
│   ├── prepare_branch.py               # NEW — creates feature branch before builder
│   ├── complete_branch.py              # RENAMED from git_commit.py — reads branch_name from state
│   └── reviewer.py                     # builder pass-through guard, pipeline + verdict events, sentinel ref_ids
├── personas/
│   └── reviewer.py                     # FR whitelist validation, TEST-QUALITY ref_id
tests/
├── unit/
│   ├── test_prepare_branch_node.py     # NEW — branch naming, collision, state output
│   ├── test_complete_branch_node.py    # RENAMED/UPDATED from test_git_commit_node.py
│   └── test_persona_reviewer.py       # +test_run_reviewer_strips_hallucinated_fr_ids
├── integration/
│   └── test_reviewer_node.py          # PIPELINE/FILES-MISSING ref_ids, +pass-through test
└── e2e/
    ├── test_bureau_e2e_dotnet.py       # NEW — smoke test for dotnet spec
    └── conftest.py                     # +SKIP_NO_DOTNET_REPO, +bureau_test_dotnet_repo fixture
.github/workflows/
└── e2e-dotnet.yml                      # NEW — dotnet SDK setup, 60-min timeout
Makefile                                # +test-kafka-smoke-dotnet target
```

## Complexity Tracking

No constitution violations. No entries required.
