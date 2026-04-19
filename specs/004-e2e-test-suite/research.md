# Research: Bureau E2E Test Suite

## Decision 1: python-dotenv loading strategy

**Decision**: `load_dotenv(Path.home() / ".bureau" / ".env", override=False)` called once at the typer CLI entrypoint (the `app` callback or top of `cli.py`) before any subcommand executes.

**Rationale**: `load_dotenv()` returns `False` silently when the file doesn't exist — no exception, no warning. `override=False` preserves shell env var precedence: keys already in `os.environ` are never overwritten. Placement at the CLI entrypoint ensures the load happens before any `os.environ.get("ANTHROPIC_API_KEY")` call in persona nodes. `dotenv_values()` returns a dict without touching `os.environ` — requires manual merge logic and is the wrong choice here.

**Alternatives considered**:
- `dotenv_values()` — explicit but requires manual `os.environ.update()` and doesn't respect precedence without extra logic
- Shell profile export — pollutes Claude Code's credential context, rejected per spec motivation
- Per-node load — redundant; loading once at CLI entry is sufficient

---

## Decision 2: pytest skip strategy for missing env vars

**Decision**: Module-level `pytest.mark.skipif` for `ANTHROPIC_API_KEY` and `BUREAU_TEST_REPO` checks; session-scoped `conftest.py` fixture that calls `pytest.skip(allow_module_level=True)` if vars are unresolvable after dotenv loading is attempted.

**Rationale**: `skipif` evaluates at collection time, producing clean "skipped" reporting without test failures. The fixture validates the bureau-test path exists on disk (not just that the env var is set). Module-level skip is cleaner than per-test skip for infrastructure prerequisites.

**Alternatives considered**:
- Per-test `pytest.skip()` — verbose, doesn't communicate clearly that the whole suite is gated
- `pytest.importorskip()` — for missing Python packages, not env vars

---

## Decision 3: E2E test timeout

**Decision**: `subprocess.run(..., timeout=600)` at the helper level, plus `pytest-timeout` plugin added to dev deps with `@pytest.mark.timeout(650)` on each E2E test (slightly above subprocess timeout to give subprocess time to raise `TimeoutExpired` cleanly).

**Rationale**: subprocess-level timeout raises `TimeoutExpired` and kills the child process reliably. `pytest-timeout` provides an outer guard and integrates with pytest reporting (shows as `TIMEOUT` not `ERROR`). Both together ensure no test hangs CI indefinitely.

**Alternatives considered**:
- subprocess timeout only — leaves pytest hanging if the process ignores SIGTERM
- pytest-timeout only — can't kill a subprocess that has spawned its own children

---

## Decision 4: GitHub Actions CI strategy

**Decision**: Two sequential `actions/checkout` steps (main repo to root, `fancy-bread/bureau-test` to `bureau-test/`). Use `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` for `gh pr create` — no PAT required. Add a post-test cleanup step using `gh pr close` on PRs created during the run to avoid polluting bureau-test's PR list.

**Rationale**: `gh` is pre-installed on `ubuntu-latest`. `GITHUB_TOKEN` is sufficient for creating and closing PRs on repos the workflow has access to. E2E runs on `workflow_dispatch` only (not every push) to control API spend and PR pollution.

**Alternatives considered**:
- PAT instead of GITHUB_TOKEN — more permissions than needed, security risk
- Never clean up PRs — acceptable for now but makes bureau-test's PR list noisy
- Run E2E on every push — too expensive in API credits and CI time

---

## Decision 5: Non-deterministic test (spec 004 escalation)

**Decision**: `@pytest.mark.xfail(strict=False, reason="Planner may complete spec 004 instead of escalating — AI behaviour is non-deterministic")`. The test still runs and asserts `run.escalated`; if it passes it counts as a pass, if it fails it counts as an expected failure.

**Rationale**: We want to know when bureau does escalate correctly (signal) without failing the suite when it doesn't (noise). `strict=False` is the correct setting for genuinely non-deterministic outcomes.
