# Bureau

**Spec file in. Pull request out.**

Bureau is the autonomous runtime for [ASDLC](https://asdlc.io). Approve a spec — bureau creates a branch, implements it, verifies it, and opens a pull request. You review the PR. Everything in between is not your problem.

```
[bureau] run.started          id=run-a3f9c2b1  spec=specs/002-auth/spec.md
[bureau] phase.started        phase=builder
[bureau] builder.tool         tool=write_file  path=src/auth.py
[bureau] builder.tool         tool=run_command  exit_code=0
[bureau] reviewer.pipeline    passed=true
[bureau] reviewer.verdict     verdict=pass  findings=1
[bureau] pr.created           id=run-a3f9c2b1  pr=https://github.com/org/repo/pull/42
[bureau] run.completed        id=run-a3f9c2b1  duration=6m01s
```

## How it works

Bureau runs a LangGraph state machine — the **RALPH loop** (Recursive Autonomous Loop of Patch and Harden). The Builder implements the spec phase by phase, committing after each. The Reviewer independently re-executes the pipeline and scores the result against the spec's functional requirements. They alternate until the Reviewer returns `pass` or bureau escalates to the developer.

```
validate_spec → repo_analysis → tasks_loader → prepare_branch → builder ⇄ reviewer → complete_branch → pr_create
```

When bureau cannot proceed — ambiguous spec, failing tests after N retries, missing context — it pauses with a structured escalation describing exactly what it needs. Runs are checkpointed and resumable.

## Install

```sh
# Prerequisites
brew install uv gh
gh auth login

# Bureau
uv pip install git+https://github.com/fancy-bread/bureau.git

# Spec Kit (spec authoring)
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
```

Store your Anthropic API key at `~/.bureau/.env`:

```sh
mkdir -p ~/.bureau && echo "ANTHROPIC_API_KEY=sk-ant-..." > ~/.bureau/.env
```

## Run

```sh
# Scaffold .bureau/config.toml in the target repo
bureau init --repo /path/to/your/repo

# Run a spec
bureau run specs/001-my-feature --repo /path/to/your/repo
```

## Documentation

**[fancy-bread.github.io/bureau](https://fancy-bread.github.io/bureau)**

Getting Started · Concepts · How-To · Reference · Development

## Development

```sh
git clone https://github.com/fancy-bread/bureau.git
cd bureau
uv pip install -e ".[dev]"
make ci          # lint + tests
make docs-serve  # docs at localhost:8000
```

## License

MIT — see [LICENSE](LICENSE).
