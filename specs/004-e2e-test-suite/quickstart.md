# Quickstart: Bureau E2E Test Suite

## Scenario 1: Local developer first-time setup

```bash
# 1. Get an Anthropic API key from console.anthropic.com
# 2. Create ~/.bureau/.env (never commit this file)
mkdir -p ~/.bureau
cat > ~/.bureau/.env <<EOF
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
EOF

# 3. Clone bureau-test alongside bureau
git clone git@github.com:fancy-bread/bureau-test.git ~/projects/software/bureau-test

# 4. Install bureau with dev deps
cd ~/projects/software/bureau
pip install -e ".[dev]"

# 5. Run the E2E suite
BUREAU_TEST_REPO=~/projects/software/bureau-test pytest tests/e2e/ -v
```

**Expected output**:
```
tests/e2e/test_bureau_e2e.py::test_smoke_hello_world PASSED
tests/e2e/test_bureau_e2e.py::test_escalation_missing_artifact xfail
```

---

## Scenario 2: Run without API key set

```bash
unset ANTHROPIC_API_KEY  # no shell key, no ~/.bureau/.env
BUREAU_TEST_REPO=~/projects/software/bureau-test pytest tests/e2e/ -v
```

**Expected output**:
```
tests/e2e/test_bureau_e2e.py::test_smoke_hello_world SKIPPED (ANTHROPIC_API_KEY not set)
tests/e2e/test_bureau_e2e.py::test_escalation_missing_artifact SKIPPED (ANTHROPIC_API_KEY not set)
```

---

## Scenario 3: Run without BUREAU_TEST_REPO

```bash
pytest tests/e2e/ -v  # BUREAU_TEST_REPO absent
```

**Expected output**:
```
tests/e2e/test_bureau_e2e.py::test_smoke_hello_world SKIPPED (BUREAU_TEST_REPO not set)
tests/e2e/test_bureau_e2e.py::test_escalation_missing_artifact SKIPPED (BUREAU_TEST_REPO not set)
```

---

## Scenario 4: Bureau run with key in ~/.bureau/.env only (no shell export)

```bash
# ~/.bureau/.env contains ANTHROPIC_API_KEY=sk-ant-...
# Shell does NOT have ANTHROPIC_API_KEY exported
bureau run specs/001-smoke-hello-world/spec.md --repo ~/projects/software/bureau-test
# Bureau loads ~/.bureau/.env at startup → key is available → run proceeds
```

---

## Scenario 5: CI via GitHub Actions

The workflow triggers on `workflow_dispatch`. No `.env` file is created in CI — the secret is injected directly as an env var by the runner:

```
GitHub repo → Settings → Secrets → ANTHROPIC_API_KEY → paste key
```

Then: Actions → E2E Tests → Run workflow.
