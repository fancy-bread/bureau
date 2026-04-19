# Data Model: Bureau E2E Test Suite

This feature introduces no persistent entities. The relevant "data" is configuration loading order and the structure of the env file.

---

## Credential Resolution Order

```
1. os.environ["ANTHROPIC_API_KEY"]          ← shell / CI env var (wins)
2. ~/.bureau/.env → ANTHROPIC_API_KEY       ← local dev file (fallback)
3. KeyError → human-readable exit message   ← neither found
```

**Implemented by**: `load_dotenv(Path.home() / ".bureau" / ".env", override=False)` at CLI entrypoint.

---

## env.example Schema

| Variable | Required | Example Value | Description |
|----------|----------|---------------|-------------|
| `ANTHROPIC_API_KEY` | Yes | `sk-ant-api03-...` | Anthropic Console API key for bureau's persona nodes |

One variable today. New vars added here when new integrations are introduced.

---

## E2E Test Fixture State

Session-scoped, not persisted between runs.

| Name | Type | Source | Purpose |
|------|------|--------|---------|
| `bureau_test_repo` | `Path` | `BUREAU_TEST_REPO` env var | Path to local bureau-test clone |
| `anthropic_key` | `str` | `ANTHROPIC_API_KEY` (env or .env) | Verified present before tests run |

---

## CI Secrets

| Secret Name | Where Set | Consumed As |
|-------------|-----------|-------------|
| `ANTHROPIC_API_KEY` | GitHub repo → Settings → Secrets | `env: ANTHROPIC_API_KEY` in workflow step |
| `GITHUB_TOKEN` | Auto-provisioned by Actions | `env: GH_TOKEN` for `gh pr create` |
