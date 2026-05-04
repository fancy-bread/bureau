# Quickstart: Reviewer Hardening and Branch Lifecycle

**Feature**: 013-reviewer-hardening-branch-lifecycle

This feature ships as part of bureau core. No configuration changes are required for existing repos.

---

## What Changed

### Branch lifecycle

Bureau now opens the feature branch **before** the Builder starts, not after the Reviewer passes:

```
tasks_loader → prepare_branch → builder → reviewer → complete_branch → pr_create
```

Any commits the Builder makes during a run (e.g. phase checkpoints) land on the feature branch from the first commit.

### Reviewer observability

Two new events appear in every run output:

```
[bureau] reviewer.pipeline  passed=True  phases=['install', 'build', 'test']  failed_phase=None
[bureau] reviewer.verdict   verdict=pass  round=0  summary=All requirements met.  findings=[...]
```

### Reviewer correctness

- Findings with FR IDs not present in the spec are stripped before routing.
- If `install_cmd` fails, the run escalates immediately rather than looping through reviewer rounds.
- Internal diagnostic findings (`PIPELINE`, `FILES-MISSING`, `TEST-QUALITY`) no longer collide with spec FR numbers.

---

## Running the Dotnet E2E Test

**Prerequisites**: Kafka running locally, `BUREAU_TEST_REPO_DOTNET` pointing to a pre-seeded `bureau-test-dotnet` repo, `ANTHROPIC_API_KEY` set.

```bash
# Start Kafka
make bureau-kafka-up

# Run the dotnet smoke test
BUREAU_TEST_REPO_DOTNET=../bureau-test-dotnet make test-kafka-smoke-dotnet

# Or via pytest directly
BUREAU_TEST_REPO_DOTNET=../bureau-test-dotnet GH_TOKEN=... \
  pytest tests/e2e/test_bureau_e2e_dotnet.py -v --timeout=1800
```

**Important**: `bureau-test-dotnet` must have the solution scaffold committed to `main` (`src/BureauObservability.sln` etc.) before running. `install_cmd = "dotnet restore src/"` requires `src/` to exist.

---

## CI

Trigger the dedicated workflow from the GitHub Actions UI:

- `e2e-dotnet.yml` — Runs `test_bureau_e2e_dotnet.py` exclusively with .NET 10 SDK and a 60-minute timeout.
