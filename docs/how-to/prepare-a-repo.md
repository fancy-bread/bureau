---
icon: octicons/repo-24
---

# Prepare a Repo

Two things need to be in place before bureau can run against a repo: a `.bureau/config.toml` telling bureau how to build and test the project, and a `.specify/` directory from Spec Kit providing the spec authoring toolchain.

---

## 1. Add .bureau/config.toml

```sh
cd /path/to/your/repo
bureau init
```

This creates `.bureau/config.toml` with `FILL_IN` placeholders. Edit it before running:

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

See [Config Reference](../getting-started/config-reference.md) for all fields and language examples.

---

## 2. Initialise Spec Kit

```sh
cd /path/to/your/repo
specify init . --ai claude
```

This scaffolds `.specify/` with:

```
.specify/
├── memory/
│   └── constitution.md    ← project-level architectural principles
├── templates/             ← spec, plan, tasks templates
└── extensions/
    └── git/               ← branch creation and commit hooks
```

The constitution in `.specify/memory/constitution.md` is appended to the bureau runtime constitution on every run — it is how your project's standards travel into every bureau run automatically. Edit it to capture the architectural rules, naming conventions, and constraints that matter for your project.

---

## 3. Commit both

```sh
git add .bureau/config.toml .specify/
git commit -m "chore: add bureau and speckit config"
```

Bureau reads `.bureau/config.toml` from the working tree during `repo_analysis`. Spec Kit reads `.specify/` during spec authoring. Both should be committed so the configuration is consistent across machines and CI.
