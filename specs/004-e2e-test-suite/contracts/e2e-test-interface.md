# Contract: E2E Test Suite Interface

Defines what the test suite reads from the environment and what it asserts on.

## Environment Variables Consumed

| Variable | Required | Fallback | Effect if absent |
|----------|----------|----------|-----------------|
| `BUREAU_TEST_REPO` | Yes | None | All E2E tests skip |
| `ANTHROPIC_API_KEY` | Yes | `~/.bureau/.env` | All E2E tests skip |

## Test Entry Points

```
pytest tests/e2e/                        # run all E2E tests
pytest tests/e2e/ -k test_smoke          # smoke test only
pytest tests/e2e/ -k test_escalation     # escalation test only
```

## Assertions Contract

### `test_smoke_hello_world`
- `run.completed` present in stdout
- Exit code 0
- Six phase events in order: `validate_spec` → `repo_analysis` → `planner` → `builder` → `critic` → `pr_create`
- At least one `ralph.attempt round=0 attempt=0 result=pass` event

### `test_escalation_missing_artifact` _(xfail strict=False)_
- `run.escalated` present in stdout
- No `https://github.com/` URL in stdout
- Escalation body contains `What happened`, `What's needed`, `Options`, `Resume:`

## CI Workflow Contract (`.github/workflows/e2e.yml`)

```yaml
trigger: workflow_dispatch
secrets_required:
  - ANTHROPIC_API_KEY       # Anthropic Console key, bureau's billing
  - GITHUB_TOKEN            # auto-provisioned; used as GH_TOKEN for gh pr create
env_vars_set:
  - BUREAU_TEST_REPO: ${{ github.workspace }}/bureau-test
  - ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  - GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
repos_checked_out:
  - fancy-bread/bureau       → .
  - fancy-bread/bureau-test  → bureau-test/
post_run_cleanup:
  - gh pr close any PRs created during the run (identified by run ID prefix in branch name)
```
