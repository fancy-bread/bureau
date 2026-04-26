# Implementation Plan: Command Pipeline Formalization and Reviewer Depth

**Branch**: `012-pipeline-reviewer-depth` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-pipeline-reviewer-depth/spec.md`

## Summary

Formalize the four-phase command pipeline (install → lint → build → test) as sequential gates executed by both the builder and reviewer, and upgrade the reviewer to independently re-execute the pipeline and read actual changed files rather than trusting the builder's self-report.

## Technical Context

**Language/Version**: Python 3.14  
**Primary Dependencies**: anthropic>=0.25, pydantic>=2, langgraph 0.2+; no new runtime deps required  
**Storage**: Memory scratchpad (`~/.bureau/runs/<id>/memory.json`) — builder writes `builder_summary` with `files_changed`; reviewer reads it  
**Testing**: pytest (existing suite); new integration tests for pipeline execution and reviewer file-reading  
**Target Platform**: Runs inside Docker containers on the target repo; bureau host is any POSIX system  
**Project Type**: CLI / autonomous agent runtime (existing codebase extension)  
**Performance Goals**: SC-003 — reviewer independent pipeline adds ≤60 seconds for repos with sub-30s test suites  
**Constraints**: `command_timeout` (existing config) applies uniformly to all pipeline phases; no per-phase timeouts  
**Scale/Scope**: Affects builder and reviewer nodes plus their persona modules; no changes to event schema, state shape, or CLI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First Execution | ✅ PASS | Approved spec.md is the input contract |
| II. Escalate, Don't Guess | ✅ PASS | Pipeline gate failures produce structured escalations with phase name |
| III. Verification Gates Are Real Gates | ✅ PASS | This spec *is* about making lint/build real gates; reviewer independent execution enforces this |
| IV. Constitution-First Compliance | ✅ PASS | No constitution changes required |
| V. Terse, Structured Output | ✅ PASS | No event schema changes; existing structured events sufficient |
| VI. Autonomous Operation With Resumability | ✅ PASS | No new check-ins; reviewer pipeline execution is fully autonomous |

**Gate result**: All principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/012-pipeline-reviewer-depth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── pipeline_result.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
bureau/
├── nodes/
│   ├── builder.py       # Add lint_cmd + build_cmd gates before builder attempts
│   └── reviewer.py      # Add independent pipeline execution + file reading
├── personas/
│   ├── builder.py       # Add pipeline phase runner; update system prompt
│   └── reviewer.py      # Add pipeline execution + file content to reviewer context
├── models.py            # Add PipelinePhase, PipelineResult models
└── tools/
    └── shell_tools.py   # No changes needed (execute_shell_tool already exists)

tests/
├── integration/
│   ├── test_builder_node.py       # Add pipeline gate tests (lint fail, build fail)
│   └── test_reviewer_node.py      # Add independent pipeline + file reading tests
└── unit/
    └── test_pipeline.py           # Unit tests for pipeline phase execution logic
```

**Structure Decision**: Single project extension. All changes are contained within the existing `bureau/` package. No new top-level directories or packages required.

## Complexity Tracking

> No constitution violations to justify.
