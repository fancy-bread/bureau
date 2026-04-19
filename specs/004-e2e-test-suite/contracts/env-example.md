# Contract: bureau/data/env.example

Canonical list of environment variables bureau reads. Shipped with the package at `bureau/data/env.example`. Referenced in README as the credential setup guide.

## Format

Plain `.env` syntax — one `KEY=placeholder` per line, one `# comment` line above each key.

## Content

```dotenv
# Anthropic API key for bureau's persona nodes (Planner, Builder, Critic).
# Get yours at https://console.anthropic.com → API Keys.
# Bureau reads this from ~/.bureau/.env or from your shell environment.
# Shell environment takes precedence over the file.
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

## Rules

- No real keys ever committed here — placeholder values only
- Each new integration that reads from `os.environ` MUST add its var here
- Comments MUST explain where to obtain the value
