# Research: Bureau Personas and PR Creation

**Date**: 2026-04-18 | **Branch**: `002-personas-pr-creation`

---

## Decision 1: Model selection per persona

**Decision**: Three distinct model assignments based on task complexity and call frequency.

| Persona | Model | Rationale |
|---------|-------|-----------|
| Planner | `claude-opus-4-7` | Architectural reasoning; complex dependency analysis; called once per run |
| Builder | `claude-sonnet-4-6` | Code generation; called many times per Ralph Loop round; cost-sensitive |
| Critic | `claude-opus-4-7` | High-stakes verdict; thorough requirement gap detection; called once per round |

All three configurable via `bureau.toml` `[bureau]` section (`planner_model`, `builder_model`, `critic_model`). Defaults baked into `BureauConfig`.

**Rationale**: Opus-class for reasoning-heavy, low-frequency calls; Sonnet-class for generative, high-frequency calls. Avoids spending Opus tokens on Builder retries.

**Alternatives considered**:
- All Opus: Too expensive for Builder inner loop; 3 rounds × 3 retries = up to 9 Builder calls
- All Sonnet: Critic quality degrades on subtle requirement gaps and constitution checks
- Haiku for Builder: Insufficient code quality for production-grade implementations

---

## Decision 2: Builder tool use interface

**Decision**: Anthropic tool use API with four custom tools: `read_file`, `write_file`, `list_directory`, `run_command`.

- File edits via **full file rewrites** (not diffs or patches)
- `run_command` runs subprocess with `cwd=repo_path`, captures stdout/stderr, returns to model
- Tools defined as pydantic models, serialised to Anthropic tool schema at call time
- Builder receives tool results and continues until it calls `run_command` with `test_cmd` and gets exit code 0

**Rationale**: Tool use gives the Builder a structured interface to the repo rather than relying on code blocks in responses. Full rewrites are simpler and more reliable than applying diffs — the model sees the full file before rewriting, reducing boundary errors.

**Alternatives considered**:
- Response parsing (extract code blocks from markdown): Fragile; model often produces partial files or wraps in explanation
- `str_replace_editor`-style diff tool: More token-efficient but significantly more complex to implement and verify correctly
- Filesystem MCP server: Adds an MCP dependency; tool use directly in the API call is simpler for a subprocess-based runtime

---

## Decision 3: Test and build execution

**Decision**: `subprocess.run()` with `cwd=repo_path`, `timeout=300`, `capture_output=True`. No Docker for this feature.

- `install_cmd` runs once at the start of each Ralph Loop round
- `build_cmd` runs before `test_cmd` when non-empty
- `test_cmd` run after each Builder attempt; non-zero exit = failure, stdout/stderr fed back to Builder
- Timeout 300s configurable via `bureau.toml` `[ralph_loop]` section

**Rationale**: subprocess is the simplest correct approach for a local CLI runtime. Docker sandboxing would prevent accidental host filesystem writes but adds significant setup complexity. The target repo's environment is explicitly configured by the developer via `.bureau/config.toml` — they own the trust boundary.

**Alternatives considered**:
- Docker container per run: Correct isolation model but out of scope for this feature; deferred to a future hardening spec
- Virtual environment creation per run: Redundant if repo already has its own venv; install_cmd handles this

---

## Decision 4: PR creation mechanism

**Decision**: `gh pr create` via `subprocess.run()`. No Python GitHub library dependency.

- PR title derived from spec name
- PR body rendered from `RunSummary` template (Markdown)
- Branch name taken from run state (`spec.branch` field or fallback to `bureau/<run-id>`)
- `gh` CLI auth assumed present in environment (same assumption as spec)

**Rationale**: `gh` CLI is already the established convention for bureau (README, spec assumptions). Adding PyGitHub or direct REST API calls would introduce auth complexity (token management) with no benefit over `gh`'s existing credential store.

**Alternatives considered**:
- PyGitHub: Additional dependency; `gh` CLI covers the use case cleanly
- GitHub REST API direct: Requires explicit token handling; `gh` handles auth transparently
- gitpython + REST: Two dependencies for what `gh` does in one command

---

## Decision 5: Ralph Loop state in LangGraph

**Decision**: Track `ralph_round` (int, 0-indexed) and `builder_attempts` (int, 0-indexed) in LangGraph state dict. Builder node handles its own inner retry loop; Critic node increments `ralph_round` on `revise` verdict.

- `builder_attempts` resets to 0 on each new Ralph Loop round
- Routing: existing conditional edge `critic → revise → builder` already in `graph.py`; just needs round counter check before routing
- A new `_route_critic` implementation reads `ralph_round` and returns `"escalate"` if `>= max_rounds`

**Rationale**: Keeping the inner loop (Builder retries) inside the Builder node avoids multiplying LangGraph nodes. The outer loop (Critic→Builder) maps naturally to LangGraph's existing conditional edge routing. State is serialisable (ints, not objects).

**Alternatives considered**:
- Model each Builder attempt as a separate LangGraph node: Cleanly resumable at the attempt level but produces an explosion of nodes; over-engineered for 3 retries
- Separate `ralph_loop_manager` node: Unnecessary indirection; the Critic already owns the routing decision

---

## Decision 6: Prompt caching strategy

**Decision**: Cache spec content and task plan as the system prompt prefix using `cache_control: {"type": "ephemeral"}` on the last static content block.

- Planner system prompt: bureau constitution + spec content (cached)
- Builder system prompt: bureau constitution + spec content + task plan + build attempt history (spec and plan cached; attempt history not cached — changes each retry)
- Critic system prompt: bureau constitution + spec content + task plan + builder summary (all cached except builder summary which changes per round)
- Cache TTL: 5 minutes (Anthropic ephemeral cache)

**Rationale**: Spec content and task plan are static across all retries within a round. Caching them avoids redundant input token costs on the Builder inner loop (up to 9 calls). Bureau's existing `anthropic>=0.25` dependency supports `cache_control`.

**Alternatives considered**:
- No caching: Works but wastes tokens on repeated spec content; costs increase linearly with retry count
- Cache everything including attempt history: History changes each call; caching it would invalidate immediately and waste cache write tokens

---

## Decision 7: Critic constitutional review approach

**Decision**: Critic checks both the spec's functional requirements (requirement-by-requirement pass/fail) and the bureau constitution (principle-by-principle check). Constitutional violations short-circuit to `escalate`; requirement gaps produce `revise` with specific findings.

- Critic prompt includes: spec FRs, constitution text, builder summary, previous round findings (if any)
- Critic response parsed into structured `CriticVerdict` with a `CriticFinding` list
- Pydantic model used for structured output parsing via `model.model_validate(json.loads(...))`

**Rationale**: Separating constitutional review from requirement review in the prompt allows the model to produce structured findings per category. Pydantic parsing ensures the verdict is machine-readable for LangGraph routing.

**Alternatives considered**:
- Free-text Critic response parsed with regex: Fragile; structured output via JSON is more reliable
- Separate constitutional review node: Adds pipeline complexity; the Critic can handle both in one call given clear prompt structure
