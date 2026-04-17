# Contract: bureau.toml (Operator Config)

**Feature**: Bureau CLI Foundation | **Date**: 2026-04-16

Operator-level config file. Placed in the directory from which `bureau run` is invoked,
or specified via `--config`. Optional in this foundation release; all fields have defaults.

---

## Schema

```toml
[models]
planner = "claude-opus-4-6"               # model for Planner node
builder = "claude-haiku-4-5-20251001"     # model for Builder node
critic  = "claude-opus-4-6"               # model for Critic node

[github]
token_env = "GITHUB_TOKEN"                # env var name holding GitHub PAT

[bureau]
max_retries = 3                           # max Critic send-backs before escalating
```

## Field Definitions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `models.planner` | string | `"claude-opus-4-6"` | Model ID for Planner LLM calls |
| `models.builder` | string | `"claude-haiku-4-5-20251001"` | Model ID for Builder LLM calls |
| `models.critic` | string | `"claude-opus-4-6"` | Model ID for Critic LLM calls |
| `github.token_env` | string | `"GITHUB_TOKEN"` | Name of env var holding GitHub token |
| `bureau.max_retries` | int | `3` | Max Critic send-backs before escalating to operator |

## Validation Rules

- `max_retries` must be an integer >= 1
- Model ID fields must be non-empty strings
- Unknown keys are ignored (forward-compatible)
- File is optional; missing file applies all defaults
