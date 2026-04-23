# Contract: SKILL.md Format

**Applies to**: all files under `bureau/skills/default/{role}/`

## File Format

```markdown
---
name: <skill-name>
description: <one-line L1 summary shown in system prompt>
---

# <Skill Title>

<Full skill instructions — loaded on demand (L2)>
```

## Required Fields (YAML frontmatter)

| Field | Type | Constraint |
|-------|------|-----------|
| `name` | `str` | Unique within the role directory; lowercase, hyphens only (e.g. `build`, `run-tests`) |
| `description` | `str` | ≤120 characters; shown in system prompt at L1 |

## Optional Fields (YAML frontmatter)

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | Semver string for tracking vendor updates |
| `source` | `str` | Upstream URL (e.g. `https://github.com/addyosmani/agent-skills/...`) |

## Discovery Rules

- `SkillsMiddleware` scans all `.md` files in each configured `sources` directory.
- Files without valid YAML frontmatter are skipped with a warning.
- Files with frontmatter but missing `name` or `description` are skipped with a warning.
- Multiple files in the same directory are all loaded; name collisions within a directory produce a warning and the last file wins.

## Role Directory Mapping

| Directory | Agent | ASDLC Phase |
|-----------|-------|-------------|
| `bureau/skills/default/build/` | Builder | BUILD |
| `bureau/skills/default/test/` | Builder | VERIFY (test execution) |
| `bureau/skills/default/ship/` | Builder | SHIP |
| `bureau/skills/default/review/` | Reviewer | REVIEW |

## Validation at Runtime

Bureau's Builder initialisation MUST verify that at least one valid skill exists in each of `build/`, `test/`, and `ship/` before starting the first attempt. If any required role directory is empty or missing, bureau escalates with `EscalationReason.BLOCKER` and does not attempt any build.

Bureau's Reviewer initialisation MUST verify that `review/` contains at least one valid skill before invoking the Reviewer. Same escalation path on failure.
