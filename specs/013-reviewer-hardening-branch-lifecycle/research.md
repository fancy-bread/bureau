# Research: Reviewer Hardening and Branch Lifecycle

**Feature**: 013-reviewer-hardening-branch-lifecycle
**Date**: 2026-05-03

---

## Decision 1: FR Whitelist Validation Approach

**Decision**: After parsing the LLM's JSON response, extract all `FR-\d{3}` IDs from the spec's FR lines and filter any finding whose `ref_id` matches `FR-\d+` but is not in that set.

**Rationale**: The LLM has the spec's FR list in its system prompt but still hallucinates IDs outside the list (observed: FR-009 invented against a spec with only FR-001–FR-008). Post-processing validation is the correct layer — the LLM cannot self-police, but the calling code can enforce the whitelist deterministically. Constitution findings (`type="constitution"`) are exempt because their `ref_id` is a principle name, not a spec FR number.

**Alternatives considered**:
- Prompt-level constraint ("only reference FRs listed above") — unreliable; model still hallucinates under adversarial conditions.
- Structured output / tool use with enum validation — would require an API change to the Reviewer call; deferred to a future hardening pass.

---

## Decision 2: Builder Escalation Pass-Through Placement

**Decision**: Check `state.get("_route") == "escalate" and state.get("escalations")` at the top of `reviewer_node`, returning state unchanged if true.

**Rationale**: The `builder → reviewer` edge is unconditional in the LangGraph graph. The builder correctly sets `_route: "escalate"` when `install_cmd` fails, but the reviewer runs anyway and overwrites `_route` with `"revise"` after evaluating an empty codebase. The guard must be at reviewer entry, not at the graph edge, because changing the edge to conditional would require adding a new routing function and restructuring the graph — a larger change than warranted. An entry guard is the minimal correct fix.

**Alternatives considered**:
- Change `builder → reviewer` to a conditional edge — structurally cleaner but requires a new `_route_builder` function and changes the graph topology, creating risk for existing tests.
- Check for empty escalations list only — insufficient; `_route` alone could be set to "escalate" by other causes.

---

## Decision 3: Internal Finding Sentinel Ref_IDs

**Decision**: Replace hardcoded `FR-006`, `FR-007`, `FR-009` in bureau's own code with `type="pipeline"` findings using ref_ids `FILES-MISSING`, `TEST-QUALITY`, and `PIPELINE` respectively.

**Rationale**: The original hardcoded FR numbers collided with spec FRs — FR-006 in one spec means "retain 100 events", FR-007 means "display payload". Bureau's internal diagnostic findings must use identifiers that can never appear in a spec FR list. The `type="pipeline"` discriminant allows consumers (including the FR whitelist filter) to treat these differently from LLM-sourced findings.

**Alternatives considered**:
- Use `FR-000` as a sentinel — still technically matches `FR-\d+` and could be confused with a real FR.
- Use negative numbers (`FR-001-INTERNAL`) — non-standard, would break existing validators.

---

## Decision 4: Branch Lifecycle Split (prepare_branch / complete_branch)

**Decision**: Extract branch creation logic into a new `prepare_branch_node` inserted between `tasks_loader` and `builder`. The existing `git_commit_node` (renamed `complete_branch_node`) reads `branch_name` from state instead of creating it.

**Rationale**: A developer's first act after picking up a story is `git checkout -b feat/...`. Bureau's original design created the branch in `git_commit_node` — after the reviewer passed — meaning the Builder's phase-checkpoint commits landed on `main` (or whatever branch the repo was on). This is semantically wrong and leaves local `main` polluted during development runs. Moving branch creation to before the builder mirrors the correct workflow and makes all intermediate commits land on the feature branch from the start.

**Alternatives considered**:
- Create branch at start of `builder_node` — couples git concerns into the builder, which is already complex.
- Create branch in `memory_node` or `repo_analysis_node` — conceptually too early; branch name depends on spec name which is parsed later.
- Keep `git_commit_node` name — rejected for clarity; `complete_branch` better expresses that it closes the branch lifecycle.

---

## Decision 5: Reviewer Observability Events

**Decision**: Emit `reviewer.pipeline` immediately after the independent pipeline check and `reviewer.verdict` immediately before routing in `_process_verdict`.

**Rationale**: The reviewer was a black box — a single `phase.completed verdict=pass` line gave no indication of what was checked. Operators and CI could not distinguish a thorough review from a no-op (e.g., when no active phases are configured). Two targeted events at natural boundaries provide full visibility without restructuring the reviewer.

**Placement choices**:
- `reviewer.pipeline` after `run_pipeline()` — captures the actual phases run and pass/fail state before any verdict logic.
- `reviewer.verdict` in `_process_verdict` — emitted for all verdict paths (pass/revise/escalate) since all routing goes through that function.

---

## Decision 6: Dotnet E2E Timeout

**Decision**: Set `timeout-minutes: 60` on the `e2e-dotnet.yml` job and `@pytest.mark.timeout(1800)` on the test.

**Rationale**: The dotnet spec (`001-kafka-observability-dashboard`) is a 33-task, 5-phase greenfield implementation. The Python smoke test (4 tasks) ran in ~55s; dotnet ran in ~7.5 minutes in initial testing. 30 minutes headroom above observed time provides buffer for cold NuGet restores and LangGraph recursion retries. The GitHub Actions job timeout is set to 60 minutes (matching the test timeout with margin).
