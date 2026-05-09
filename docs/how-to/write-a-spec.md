---
icon: octicons/pencil-24
---

# Write a Spec

Bureau does not generate specs — it executes them. A spec is authored using Spec Kit slash commands inside Claude Code before bureau runs.

---

## The Spec Kit workflow

```
/speckit-specify   ← describe the feature; generates spec.md
/speckit-plan      ← generates plan.md, research.md, data-model.md
/speckit-tasks     ← generates tasks.md
/speckit-analyze   ← cross-checks all artifacts for consistency
```

Each command builds on the previous. Bureau requires `spec.md` and `tasks.md` at minimum; the planning artifacts (`plan.md`, `research.md`, `data-model.md`) give the Builder richer context and produce better results.

---

## What bureau reads

### spec.md

Bureau's `validate_spec` node parses `spec.md` for three things:

| Element | Format | Required |
|---|---|---|
| User stories | `### Story Title (Priority: P1)` headings | At least one P1 |
| Functional requirements | `**FR-001**: description` bullets | Yes |
| Success criteria | `## Success Criteria` section | Yes |

Bureau rejects specs with `[NEEDS CLARIFICATION]` markers or missing P1 stories before any work begins.

### tasks.md

Bureau's `tasks_loader` node reads `tasks.md` and builds the Builder's task list. Tasks are expected in the checkbox format Spec Kit produces:

```
- [ ] T001 Create project structure
- [ ] T002 [P] Implement data model in src/models/user.py
- [ ] T003 [US1] Add authentication endpoint in src/routes/auth.py
```

### Functional requirement IDs

The Reviewer validates its findings against the FR IDs extracted from `spec.md`. Any finding the Reviewer returns with an FR ID not present in the spec is stripped. Keep FR IDs in the standard format (`FR-001`, `FR-002`, ...) and ensure `tasks.md` covers them.

---

## Spec quality checklist

Before running bureau, confirm:

- [ ] No `[NEEDS CLARIFICATION]` markers remain
- [ ] At least one P1 user story is defined
- [ ] Every FR has a corresponding task in `tasks.md`
- [ ] Success criteria are measurable and technology-agnostic
- [ ] `plan.md` exists and reflects the target repo's stack

Run `/speckit-analyze` in Claude Code to check consistency across all artifacts before handing to bureau.
