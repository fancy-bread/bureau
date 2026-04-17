# Contract: .bureau/config.toml (Repo Config)

**Feature**: Bureau CLI Foundation | **Date**: 2026-04-16

Per-repo configuration file. Must exist at `.bureau/config.toml` in the target repo.
`bureau init` scaffolds this file. `repo_analysis` fails immediately if absent.

---

## Schema

```toml
[runtime]
language    = "python"           # programming language of the repo
base_image  = "python:3.12-slim" # Docker base image for Builder container
install_cmd = "pip install -e ." # command to install dependencies
test_cmd    = "pytest"           # command to run tests
build_cmd   = ""                 # command to build (optional)
lint_cmd    = "ruff check ."     # command to run linter (optional)

[bureau]
constitution = ".bureau/constitution.md"  # optional: project-specific constitution
```

## Field Definitions

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `runtime.language` | string | Yes | — | Primary language (e.g. `"python"`, `"typescript"`) |
| `runtime.base_image` | string | Yes | — | Docker base image for Builder |
| `runtime.install_cmd` | string | Yes | — | Dependency installation command |
| `runtime.test_cmd` | string | Yes | — | Test execution command |
| `runtime.build_cmd` | string | No | `""` | Build command; empty string = no build step |
| `runtime.lint_cmd` | string | No | `""` | Lint command; empty string = no lint step |
| `bureau.constitution` | string | No | bureau default | Path to project constitution (relative to repo root) |

## Validation Rules

- `runtime.language`, `runtime.base_image`, `runtime.install_cmd`, `runtime.test_cmd` are required; `repo_analysis` fails with CONFIG_MISSING if any are absent or empty
- `bureau.constitution` is optional; if absent, bureau uses its bundled default constitution
- Unknown keys are ignored

## Default Scaffolded by `bureau init`

```toml
[runtime]
language    = "FILL_IN"          # e.g. python, typescript, go
base_image  = "FILL_IN"          # e.g. python:3.12-slim, node:20-slim
install_cmd = "FILL_IN"          # e.g. pip install -e ., npm ci
test_cmd    = "FILL_IN"          # e.g. pytest, npm test
build_cmd   = ""
lint_cmd    = ""

[bureau]
# constitution = ".bureau/constitution.md"  # uncomment to use a project-specific constitution
```
