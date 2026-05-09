---
icon: octicons/gear-24
---

# Config Reference

`.bureau/config.toml` sits in the target repo and tells bureau how to work with that repo's stack. Bureau reads it during `repo_analysis` — the first phase after spec validation.

Scaffold a starter file with:

```sh
bureau init --repo /path/to/your/repo
```

---

## Full example

```toml
[runtime]
language    = "python"
base_image  = "python:3.14-slim"
install_cmd = "pip install -e '.[dev]'"
lint_cmd    = "ruff check ."
build_cmd   = ""
test_cmd    = "pytest"

[ralph_loop]
max_builder_attempts = 3
max_rounds           = 3
command_timeout      = 300

[bureau]
builder_model  = "claude-sonnet-4-6"
reviewer_model = "claude-opus-4-7"
```

---

## `[runtime]`

The commands bureau runs inside the target repo at each pipeline gate. All commands run from the repo root.

| Field | Required | Description |
|---|---|---|
| `language` | Yes | Stack identifier shown in events and run summaries (e.g. `python`, `typescript`, `dotnet`). Informational only — does not change runtime behaviour. |
| `base_image` | Yes | Docker base image label. Recorded in run metadata; not used to run commands in v1 (builder runs on host). |
| `install_cmd` | Yes | Command to install dependencies before any build or test step. Runs once per builder attempt. |
| `test_cmd` | Yes | Command to run the test suite. Exit code 0 = pass; anything else = fail. |
| `build_cmd` | No | Compilation or type-check step run before `test_cmd`. Leave empty if not needed. |
| `lint_cmd` | No | Lint step run before `build_cmd`. Leave empty if not needed. |

The pipeline gate order within each builder attempt is: `install → lint → build → test`. Any gate that returns a non-zero exit code blocks the subsequent gates and is reported in the reviewer findings.

---

## `[ralph_loop]`

Controls the Builder / Reviewer cycle.

| Field | Default | Description |
|---|---|---|
| `max_builder_attempts` | `3` | How many times the Builder retries within a single RALPH round before escalating. |
| `max_rounds` | `3` | How many full Builder → Reviewer cycles to allow before escalating with `RALPH_ROUNDS_EXCEEDED`. |
| `command_timeout` | `300` | Seconds before any individual shell command is killed. Increase for slow build or test suites. |

---

## `[bureau]`

Model selection. Both fields accept any Anthropic model ID.

| Field | Default | Description |
|---|---|---|
| `builder_model` | `claude-sonnet-4-6` | Model used by the Builder agent. Sonnet is the default — faster and cheaper for implementation work. |
| `reviewer_model` | `claude-opus-4-7` | Model used by the Reviewer. Opus is the default — more rigorous for structured verdict generation. |

---

## Language examples

=== "Python"

    ```toml
    [runtime]
    language    = "python"
    base_image  = "python:3.14-slim"
    install_cmd = "pip install -e '.[dev]'"
    lint_cmd    = "ruff check ."
    build_cmd   = ""
    test_cmd    = "pytest"
    ```

=== "TypeScript / Node"

    ```toml
    [runtime]
    language    = "typescript"
    base_image  = "node:24-slim"
    install_cmd = "npm install"
    lint_cmd    = "npx eslint . --max-warnings 0"
    build_cmd   = "npx tsc --noEmit"
    test_cmd    = "npx vitest run"
    ```

=== ".NET"

    ```toml
    [runtime]
    language    = "dotnet"
    base_image  = "mcr.microsoft.com/dotnet/sdk:10"
    install_cmd = "dotnet restore src/"
    lint_cmd    = "dotnet format src/ --verify-no-changes"
    build_cmd   = "dotnet build src/"
    test_cmd    = "dotnet test src/"
    ```
