# Contract: .bureau/config.toml (Repo Config) v2

**Feature**: Bureau Personas and PR Creation | **Date**: 2026-04-18
**Supersedes**: `specs/001-autonomous-runtime-core/contracts/bureau-config-toml.md`

Per-repo configuration file. Must exist at `.bureau/config.toml` in the target repo.
`bureau init` scaffolds this file. `repo_analysis` fails immediately if absent.

---

## Schema

```toml
[runtime]
language    = "python"
base_image  = "python:3.14-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"
build_cmd   = ""
lint_cmd    = "ruff check ."

[bureau]
constitution = ".bureau/constitution.md"   # optional: project-specific constitution
planner_model = "claude-opus-4-7"          # optional: override Planner model
builder_model = "claude-sonnet-4-6"        # optional: override Builder model
critic_model  = "claude-opus-4-7"          # optional: override Critic model

[ralph_loop]
max_builder_attempts = 3    # inner loop: retries per round (default: 3)
max_rounds           = 3    # outer loop: Builder-Critic cycles (default: 3)
command_timeout      = 300  # subprocess timeout in seconds (default: 300)
```

## Field Definitions

### [runtime]

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `language` | string | Yes | — | Primary language (e.g. `"python"`, `"typescript"`) |
| `base_image` | string | Yes | — | Docker base image for Builder environment |
| `install_cmd` | string | Yes | — | Dependency installation command |
| `test_cmd` | string | Yes | — | Test execution command |
| `build_cmd` | string | No | `""` | Build command; empty = no build step |
| `lint_cmd` | string | No | `""` | Lint command; empty = no lint step |

### [bureau]

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `constitution` | string | No | bureau default | Path to project constitution (relative to repo root) |
| `planner_model` | string | No | `"claude-opus-4-7"` | Anthropic model ID for Planner |
| `builder_model` | string | No | `"claude-sonnet-4-6"` | Anthropic model ID for Builder |
| `critic_model` | string | No | `"claude-opus-4-7"` | Anthropic model ID for Critic |

### [ralph_loop]

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_builder_attempts` | int | No | `3` | Maximum Builder retries per round before escalating |
| `max_rounds` | int | No | `3` | Maximum Builder-Critic rounds before escalating |
| `command_timeout` | int | No | `300` | Subprocess timeout in seconds for install/build/test commands |

## Validation Rules

- `runtime.language`, `runtime.base_image`, `runtime.install_cmd`, `runtime.test_cmd` required; `repo_analysis` fails with `CONFIG_MISSING` if absent or empty
- `ralph_loop.max_builder_attempts` must be ≥ 1; `ralph_loop.max_rounds` must be ≥ 1
- `ralph_loop.command_timeout` must be > 0
- Unknown keys are ignored
- `bureau.constitution` is optional; if absent, bureau uses its bundled default constitution

## Default Scaffolded by `bureau init`

```toml
[runtime]
language    = "FILL_IN"          # e.g. python, typescript, go
base_image  = "FILL_IN"          # e.g. python:3.14-slim, node:20-slim
install_cmd = "FILL_IN"          # e.g. pip install -e ., npm ci
test_cmd    = "FILL_IN"          # e.g. pytest, npm test
build_cmd   = ""
lint_cmd    = ""

[bureau]
# constitution = ".bureau/constitution.md"  # uncomment to use a project-specific constitution

[ralph_loop]
# max_builder_attempts = 3
# max_rounds           = 3
# command_timeout      = 300
```
