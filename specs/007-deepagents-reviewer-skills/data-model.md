# Data Model: deepagents Builder Integration, Reviewer Rename, and Skills Vendoring

**Branch**: `007-deepagents-reviewer-skills` | **Date**: 2026-04-21

---

## Changed Entities

### ReviewerFinding (renamed from CriticFinding)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"requirement"` or `"constitution"` |
| `ref_id` | `str` | e.g. `"FR-001"` |
| `verdict` | `str` | `"met"`, `"unmet"`, or `"violation"` |
| `detail` | `str` | What the Reviewer observed in the implementation |
| `remediation` | `str` | What the Builder must fix; empty string if met |

**Validation**: If any `verdict == "violation"`, overall `ReviewerVerdict.verdict` must be `"escalate"`.

### ReviewerVerdict (renamed from CriticVerdict)

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | `str` | `"pass"`, `"revise"`, or `"escalate"` |
| `findings` | `list[ReviewerFinding]` | Per-requirement assessments |
| `summary` | `str` | One-sentence summary of the verdict |
| `round` | `int` | Ralph round number |

### RalphRound (updated field names)

| Field | Type | Change |
|-------|------|--------|
| `round` | `int` | unchanged |
| `build_attempts` | `list[BuildAttempt]` | unchanged |
| `reviewer_verdict` | `str` | renamed from `critic_verdict` |
| `reviewer_findings` | `list[ReviewerFinding]` | renamed from `critic_findings` |
| `completed_at` | `str` | unchanged |

### Phase (enum — updated value)

| Key | Old value | New value |
|-----|-----------|-----------|
| `Phase.REVIEWER` | `Phase.CRITIC = "critic"` | `Phase.REVIEWER = "reviewer"` |

### RepoContext (updated field)

| Field | Old name | New name |
|-------|----------|---------|
| `reviewer_model` | `critic_model` | `reviewer_model` |

### RunState (updated keys)

| Key | Old | New |
|-----|-----|-----|
| `reviewer_findings` | `critic_findings` | `reviewer_findings` |

---

## New Entities

### Skill (on-disk representation)

A SKILL.md file in `bureau/skills/default/{role}/`. Discovered at Builder/Reviewer initialisation by `SkillsMiddleware`.

| Attribute | Source | Description |
|-----------|--------|-------------|
| `name` | YAML frontmatter `name:` | Unique skill identifier within a role directory |
| `description` | YAML frontmatter `description:` | L1 summary shown in system prompt |
| `body` | Markdown body | Full skill instructions (L2, loaded on demand) |
| `role` | Parent directory name | `build`, `test`, `ship`, or `review` |

**Validation**: A file without valid YAML frontmatter produces a warning and is skipped; the agent does not fail.

### BuilderAgent (runtime, not persisted)

Constructed at the start of each `builder_node` invocation. Not stored in `RunState`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent` | `CompiledStateGraph` | Returned by `create_deep_agent(...)` |
| `middleware` | tuple | `(FilesystemMiddleware, SkillsMiddleware, MemoryMiddleware, SummarizationMiddleware)` |
| `skills_sources` | `list[str]` | `["bureau/skills/default/build", "bureau/skills/default/test", "bureau/skills/default/ship"]` |

### ReviewerAgent (runtime, not persisted)

Constructed at the start of each `reviewer_node` invocation. Uses native Anthropic SDK; no deepagents wrapper.

| Attribute | Type | Description |
|-----------|------|-------------|
| `client` | `anthropic.Anthropic` | SDK client |
| `model` | `str` | from `repo_context.reviewer_model` |
| `skills_sources` | `list[str]` | `["bureau/skills/default/review"]` (loaded into system prompt, not middleware) |

---

## Filesystem Layout — Skills Directory

```text
bureau/skills/default/
├── build/
│   └── SKILL.md          ← /build ASDLC skill
├── test/
│   └── SKILL.md          ← /test ASDLC skill
├── ship/
│   └── SKILL.md          ← /ship ASDLC skill
└── review/
    └── SKILL.md          ← /review ASDLC skill
```

Each role directory may contain multiple SKILL.md files as the library grows. The `SkillsMiddleware` discovers all `.md` files in each source directory.

---

## State Transition Notes

- `RunState["reviewer_findings"]` replaces `RunState["critic_findings"]`; existing persisted runs that used the old key are not migrated (only new runs use `reviewer_findings`)
- `Phase.REVIEWER = "reviewer"` replaces `Phase.CRITIC = "critic"` in all new checkpoints
- `BuildAttempt` schema is unchanged; the state bridge populates the same fields from deepagents `AgentState.messages`
