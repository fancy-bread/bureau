# Feature Specification: Enrich Vendored Skills with addyosmani/agent-skills Content

**Feature Branch**: `008-enrich-skills`
**Created**: 2026-04-22
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Four Upstream Skills Vendored Verbatim (Priority: P1)

The four hand-authored SKILL.md stubs in `bureau/skills/default/` are replaced with the actual skill files from `addyosmani/agent-skills`, copied verbatim. Only the YAML frontmatter `name` field is changed to match bureau's SkillsMiddleware discovery paths (`build`, `test`, `ship`, `review`). No other adaptation is needed — bureau-specific context (task plan, constitution, spec FRs) is already injected by the system prompt in `builder.py` and `reviewer.py`.

**Why this priority**: A verbatim copy requires no authoring, introduces no adaptation drift, and immediately gives both agents the full skill anatomy (When to Use, Common Rationalizations, Red Flags, Verification) that the stubs lack. This is the entire feature.

**Independent Test**: Read each of the four SKILL.md files and verify: (1) frontmatter `name` matches the directory name, (2) the body is the upstream content from `addyosmani/agent-skills`, (3) `make ci` passes with no code changes.

**Acceptance Scenarios**:

1. **Given** `bureau/skills/default/build/SKILL.md`, **When** its content is read, **Then** the frontmatter `name` is `build` and the body matches the upstream `incremental-implementation` SKILL.md body.
2. **Given** `bureau/skills/default/test/SKILL.md`, **When** its content is read, **Then** the frontmatter `name` is `test` and the body matches the upstream `test-driven-development` SKILL.md body.
3. **Given** `bureau/skills/default/ship/SKILL.md`, **When** its content is read, **Then** the frontmatter `name` is `ship` and the body matches the upstream `shipping-and-launch` SKILL.md body.
4. **Given** `bureau/skills/default/review/SKILL.md`, **When** its content is read, **Then** the frontmatter `name` is `review` and the body matches the upstream `code-review-and-quality` SKILL.md body.
5. **Given** all four skills replaced, **When** `make ci` runs, **Then** all tests pass and no production code changes are required.

---

### Edge Cases

- What if an upstream skill file is too large for the agent's context window? Flag it at runtime — do not pre-trim content in the vendored file. Trimming is a separate concern.
- What if addyosmani updates the upstream skill after bureau vendors it? The vendored copy is a point-in-time snapshot. Upstream updates are adopted manually and deliberately.
- What if the upstream frontmatter includes fields that conflict with bureau's SkillsMiddleware expectations? Only the `name` field is bureau-controlled; all other frontmatter fields are copied as-is.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `bureau/skills/default/build/SKILL.md` MUST contain the verbatim body of `addyosmani/agent-skills` `incremental-implementation/SKILL.md` with only the frontmatter `name` changed to `build`.
- **FR-002**: `bureau/skills/default/test/SKILL.md` MUST contain the verbatim body of `addyosmani/agent-skills` `test-driven-development/SKILL.md` with only the frontmatter `name` changed to `test`.
- **FR-003**: `bureau/skills/default/ship/SKILL.md` MUST contain the verbatim body of `addyosmani/agent-skills` `shipping-and-launch/SKILL.md` with only the frontmatter `name` changed to `ship`.
- **FR-004**: `bureau/skills/default/review/SKILL.md` MUST contain the verbatim body of `addyosmani/agent-skills` `code-review-and-quality/SKILL.md` with only the frontmatter `name` changed to `review`.
- **FR-005**: Directory names (`build/`, `test/`, `ship/`, `review/`) MUST remain unchanged.
- **FR-006**: No changes to production Python source files (`bureau/nodes/`, `bureau/personas/`) are permitted as part of this feature.
- **FR-007**: The full test suite MUST pass after all four skills are replaced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four SKILL.md files contain the upstream anatomy sections: When to Use, Common Rationalizations, Red Flags, and Verification.
- **SC-002**: Zero production Python source file changes — content replacement only.
- **SC-003**: `make ci` passes after replacement with no new test failures.

## Assumptions

- Bureau-specific context (task plan, constitution, spec FRs) is provided by the system prompt, not the skill file — no adaptation of skill body content is needed.
- The upstream `description` field in each skill's frontmatter will be updated to reflect bureau's role for that skill (the only authored change beyond `name`).
- `addyosmani/agent-skills` is a public repository and its content is freely reusable.
- The existing `skills/**/*.md` glob in `pyproject.toml` package-data covers the updated files without change.
