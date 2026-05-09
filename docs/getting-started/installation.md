---
icon: octicons/download-24
---

# Installation

Bureau sits at the end of a short toolchain. This page installs everything in the right order and explains what each piece does.

---

## 1. uv

**uv** is a Python package manager — faster and more reliable than pip for installing CLI tools. Bureau and Spec Kit are both installed with it.

```sh
brew install uv
```

No Homebrew? Use the installer directly:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```sh
uv --version
```

---

## 2. GitHub CLI

**gh** is GitHub's official CLI. Bureau uses it to create pull requests at the end of a run. You need to be authenticated before bureau can open a PR on your behalf.

```sh
brew install gh
gh auth login
```

Follow the prompts to authenticate with your GitHub account.

```sh
gh auth status
```

---

## 3. Anthropic API key

Bureau's Builder and Reviewer are powered by Claude. You need an API key from Anthropic — this is separate from a Claude.ai subscription and is billed per-token.

Get one at [console.anthropic.com](https://console.anthropic.com) → API Keys.

Once you have the key, store it where bureau can find it:

```sh
mkdir -p ~/.bureau
cat > ~/.bureau/.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
EOF
```

Bureau loads `~/.bureau/.env` at startup. If `ANTHROPIC_API_KEY` is already exported in your shell, that takes precedence and the file is ignored.

For CI, inject from a repository secret — no `.env` file needed:

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## 4. Spec Kit

**Spec Kit** is the spec authoring tool. It provides a set of slash commands inside Claude Code (`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, etc.) that guide you through writing a spec bureau can execute. Bureau does not generate specs — it runs them.

Install the CLI:

```sh
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
```

Then initialise Spec Kit in your target repo — the repo you want bureau to work on:

```sh
cd /path/to/your/repo
specify init . --ai claude
```

This scaffolds a `.specify/` directory with templates, a constitution, and the hook configuration that wires the slash commands into Claude Code.

---

## 5. Bureau

Install bureau from source:

```sh
uv pip install git+https://github.com/fancy-bread/bureau.git
```

For local development or contributing:

```sh
git clone https://github.com/fancy-bread/bureau.git
cd bureau
uv pip install -e ".[dev]"
```

```sh
bureau --help
```

---

## Optional: Kafka

Kafka publishing is entirely opt-in and not needed for a basic run. If you want bureau to publish structured events to a Kafka topic — for monitoring, dashboards, or webhooks — set `BUREAU_KAFKA_BOOTSTRAP_SERVERS` in `~/.bureau/.env`. See [Monitor a Run](../how-to/monitor-a-run.md) for setup details.

---

## Next

[Quick Start →](quick-start.md){ .md-button .md-button--primary }
