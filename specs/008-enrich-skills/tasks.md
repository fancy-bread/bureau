# Tasks: Enrich Vendored Skills with addyosmani/agent-skills Content

**Input**: Design documents from `/specs/008-enrich-skills/`
**Prerequisites**: spec.md ✅ plan.md ✅

---

## Phase 1: User Story 1 — Four Upstream Skills Vendored Verbatim (Priority: P1)

**Goal**: Replace all four SKILL.md stubs with verbatim upstream content. Frontmatter `name` and `description` are the only fields that differ from upstream.

**Independent Test**: Read each of the four SKILL.md files and verify frontmatter `name` matches the directory name and the body contains "When to Use", "Common Rationalizations", "Red Flags", and "Verification" sections. Run `make ci` and confirm it passes with no code changes.

**Fetch method**: For each file, run:
```
gh api repos/addyosmani/agent-skills/contents/skills/<upstream-name>/SKILL.md --jq '.content' | base64 -d
```
Strip the upstream frontmatter block (`---` … `---`), then write the new frontmatter + upstream body to the target file.

- [x] T001 [P] [US1] Replace `bureau/skills/default/build/SKILL.md` — fetch `incremental-implementation` body from `addyosmani/agent-skills`; write frontmatter `name: build`, `description: Implements tasks from the task plan by building in thin vertical slices, testing each increment before moving to the next`; append verbatim upstream body
- [x] T002 [P] [US1] Replace `bureau/skills/default/test/SKILL.md` — fetch `test-driven-development` body from `addyosmani/agent-skills`; write frontmatter `name: test`, `description: Proves implementation correctness by writing failing tests first and following the Red/Green/Refactor cycle`; append verbatim upstream body
- [x] T003 [P] [US1] Replace `bureau/skills/default/ship/SKILL.md` — fetch `shipping-and-launch` body from `addyosmani/agent-skills`; write frontmatter `name: ship`, `description: Verifies all tasks are addressed and the implementation is ready for handoff to the Reviewer`; append verbatim upstream body
- [x] T004 [P] [US1] Replace `bureau/skills/default/review/SKILL.md` — fetch `code-review-and-quality` body from `addyosmani/agent-skills`; write frontmatter `name: review`, `description: Reviews the Builder implementation against spec functional requirements and the bureau constitution using a five-axis quality framework`; append verbatim upstream body

---

## Phase 2: Polish & Cross-Cutting Concerns

- [x] T005 Run `make ci` and confirm all tests pass and the 80% coverage gate holds with no production Python file changes

---

## Dependencies & Execution Order

- T001, T002, T003, T004 are fully parallel — different files, no shared state
- T005 depends on T001–T004 complete

## Parallel Opportunities

```
# All four skill replacements run simultaneously:
T001 — build/SKILL.md
T002 — test/SKILL.md
T003 — ship/SKILL.md
T004 — review/SKILL.md

# Then:
T005 — make ci
```

## Implementation Strategy

All five tasks in a single pass: fetch and write T001–T004 in parallel, then T005 to confirm the gate holds. No MVP sub-scope needed — the feature is atomic.
