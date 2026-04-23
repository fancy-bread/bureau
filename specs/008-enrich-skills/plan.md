# Implementation Plan: Enrich Vendored Skills with addyosmani/agent-skills Content

**Branch**: `008-enrich-skills` | **Date**: 2026-04-22 | **Spec**: [spec.md](spec.md)

## Summary

Replace four hand-authored SKILL.md stubs in `bureau/skills/default/` with verbatim content from `addyosmani/agent-skills`. Only the YAML frontmatter `name` and `description` fields differ from upstream. No Python source changes. No new dependencies.

## Technical Context

**Language/Version**: Python 3.14 (no code changes)
**Primary Dependencies**: None new — file replacement only
**Storage**: `bureau/skills/default/{build,test,ship,review}/SKILL.md` (tracked in git)
**Testing**: pytest + ruff via `make ci`
**Target Platform**: N/A — static content files
**Project Type**: Content replacement — no executable logic
**Performance Goals**: N/A
**Constraints**: Frontmatter `name` and directory names must be unchanged; no production Python files may be modified
**Scale/Scope**: 4 files

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ Pass | Spec approved before this plan |
| II. Escalate, Don't Guess | ✅ Pass | No ambiguities — source content is fixed upstream |
| III. Verification Gates | ✅ Pass | `make ci` is the gate; must pass after replacement |
| IV. Constitution-First | ✅ Pass | No constitution violations introduced |
| V. Terse Structured Output | N/A | No runtime behaviour changed |
| VI. Autonomous Operation | N/A | No pipeline behaviour changed |

No violations. No Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/008-enrich-skills/
├── spec.md       ✅
├── plan.md       ✅ (this file)
└── tasks.md      ← /speckit-tasks output
```

*research.md, data-model.md, contracts/, and quickstart.md are not applicable — no unknowns, no entities, no external interfaces.*

### Source Files Changed

```text
bureau/skills/default/
├── build/SKILL.md    ← replaced with incremental-implementation body
├── test/SKILL.md     ← replaced with test-driven-development body
├── ship/SKILL.md     ← replaced with shipping-and-launch body
└── review/SKILL.md   ← replaced with code-review-and-quality body
```

All other files unchanged.

## Implementation Approach

**Source**: `https://github.com/addyosmani/agent-skills` — fetch each skill at implementation time via `gh api` to get the latest committed content.

**Per-file process**:
1. Fetch upstream SKILL.md body via `gh api repos/addyosmani/agent-skills/contents/skills/<upstream-name>/SKILL.md`
2. Strip the upstream frontmatter
3. Write new frontmatter with `name: <bureau-name>` and a bureau-scoped `description`
4. Write the upstream body verbatim

**Frontmatter mapping**:

| Bureau file | Upstream skill | `name` | `description` |
|---|---|---|---|
| `build/SKILL.md` | `incremental-implementation` | `build` | Implements tasks from the task plan by building in thin vertical slices, testing each increment before moving to the next |
| `test/SKILL.md` | `test-driven-development` | `test` | Proves implementation correctness by writing failing tests first and following the Red/Green/Refactor cycle |
| `ship/SKILL.md` | `shipping-and-launch` | `ship` | Verifies all tasks are addressed and the implementation is ready for handoff to the Reviewer |
| `review/SKILL.md` | `code-review-and-quality` | `review` | Reviews the Builder's implementation against spec functional requirements and the bureau constitution using a five-axis quality framework |

## Verification

- `make ci` passes (lint + unit + integration tests, 80% coverage gate)
- Each SKILL.md contains upstream anatomy sections: When to Use, Common Rationalizations, Red Flags, Verification
- No Python source files modified
