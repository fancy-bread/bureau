# Contract: reviewer_node (renamed from critic_node)

**Phase**: REVIEWER | **File**: `bureau/nodes/reviewer.py` (renamed from `critic.py`)

## Input (from RunState)

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `run_id` | `str` | ✅ | Run identifier |
| `spec_path` | `str` | ✅ | Path to spec.md |
| `repo_path` | `str` | ✅ | Absolute path to target git repo |
| `repo_context` | `RepoContext \| None` | ✅ | Config with `reviewer_model` |
| `ralph_round` | `int` | ✅ | Current round number |

## Output (merged into RunState)

| Key | Type | Description |
|-----|------|-------------|
| `ralph_rounds` | `list[dict]` | Appended with `RalphRound.model_dump()` |
| `reviewer_findings` | `list[dict]` | Findings from this round's `ReviewerVerdict` |
| `phase` | `Phase` | `Phase.GIT_COMMIT` (pass), `Phase.BUILDER` (revise), `Phase.ESCALATE` (constitution violation) |
| `_route` | `str` | `"pass"`, `"revise"`, or `"escalate"` |

## Behaviour Contract

1. Load `builder_summary` from `Memory(run_id).read("builder_summary")`.

2. Call `run_reviewer(client, spec_text, constitution, builder_summary, ralph_round, model)` — single structured Anthropic SDK call; no deepagents.

3. Parse `ReviewerVerdict` from JSON response.

4. Route: `violation` → `"escalate"`; all P1 met → `"pass"`; any P1 unmet → `"revise"` (up to `max_ralph_rounds`).

5. Write `reviewer_findings` to `Memory(run_id).write("reviewer_findings", ...)`.

## Events Emitted

```
[bureau] phase.completed  phase=reviewer  verdict=pass|revise|escalate
[bureau] ralph.completed  rounds=N  verdict=pass          (on pass only)
```

## Note on Skill Integration

The `review` ASDLC skill is loaded into the Reviewer's system prompt at construction time (read from `bureau/skills/default/review/SKILL.md` and prepended to the system template). It does not use `SkillsMiddleware` since the Reviewer makes a single SDK call, not an agentic loop.
