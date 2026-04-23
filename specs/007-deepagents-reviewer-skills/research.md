# Research: deepagents Builder Integration, Reviewer Rename, and Skills Vendoring

**Date**: 2026-04-21 | **Branch**: `007-deepagents-reviewer-skills`

All decisions in this document are grounded in live introspection of `deepagents 0.5.3` installed at `.venv/lib/python3.14/site-packages/deepagents/`.

---

## Decision 1: deepagents entry point for the Builder

**Decision**: Use `create_deep_agent(model, system_prompt=..., middleware=(...))` to construct the Builder agent. Invoke with `.invoke({"messages": [HumanMessage(...)]})` per attempt, discarding state between attempts (stateless per-attempt).

**Rationale**: `create_deep_agent` returns a `CompiledStateGraph` that accepts `{"messages": [...]}` and returns a final `AgentState`. The `middleware` parameter accepts any sequence of `AgentMiddleware` instances — this is where `FilesystemMiddleware`, `SkillsMiddleware`, `MemoryMiddleware`, and `SummarizationMiddleware` are wired. The outer bureau `StateGraph` owns the retry loop; the deepagents graph handles a single attempt.

**Alternatives considered**:
- Using `deepagents` as the outer graph (replacing LangGraph entirely): rejected — bureau's existing checkpoint / resume / escalation model lives in the outer graph; replacing it wholesale is out of scope for v2.
- Sharing a `checkpointer` between the deepagents inner graph and the outer bureau graph: rejected — deepagents checkpointing is per-conversation; bureau's per-phase checkpointing is sufficient.

---

## Decision 2: FilesystemMiddleware replaces FILE_TOOLS + SHELL_TOOLS

**Decision**: Wire `FilesystemMiddleware(backend=FilesystemBackend(root_dir=repo_path))` as the first middleware. Remove `FILE_TOOLS`, `SHELL_TOOLS`, and the manual tool dispatch loop from `bureau/personas/builder.py`.

**Rationale**: `FilesystemMiddleware.__init__` accepts `backend: BackendProtocol | None`. `FilesystemBackend(root_dir=repo_path)` anchors the agent to the target repo. This provides `read_file`, `write_file`, `list_directory`, and `run_command` equivalents with built-in eviction (20k tokens for file content, 50k for human messages) and no manual tool dispatch loop required.

**Alternatives considered**:
- Keeping FILE_TOOLS + SHELL_TOOLS as `tools=` passed to `create_deep_agent`: possible but bypasses deepagents' eviction and context management; loses the benefit of FilesystemMiddleware.

---

## Decision 3: SkillsMiddleware with FilesystemBackend for role-specific skill assignment

**Decision**: Organise skills under `bureau/skills/default/{role}/` subdirectories. Wire separate `SkillsMiddleware` instances per agent:
- Builder: `SkillsMiddleware(backend=FilesystemBackend(root_dir=skills_root), sources=["bureau/skills/default/build", "bureau/skills/default/test", "bureau/skills/default/ship"])`
- Reviewer: `SkillsMiddleware(backend=FilesystemBackend(root_dir=skills_root), sources=["bureau/skills/default/review"])`

**Rationale**: `SkillsMiddleware.__init__` takes `backend` and `sources: list[str]`. Source paths are the leaf directories that contain SKILL.md files. By using role-named subdirectories, role-based skill assignment is declarative: add a path to Builder's `sources` to grant it a skill; remove it to revoke access. Skills are loaded in source order; later sources override earlier ones.

**Alternatives considered**:
- Flat `bureau/skills/default/` directory with all skills: rejected — no way to assign skills per-agent without code changes.
- Config file mapping agent names to skill paths: more flexible but over-engineered for the current scope; directory organisation is self-documenting.

---

## Decision 4: MemoryMiddleware for plan and repo context injection

**Decision**: Wire `MemoryMiddleware(backend=FilesystemBackend(root_dir=run_context_dir), sources=[run_context_dir])` where `run_context_dir` is a temporary directory written at Builder start containing `plan.md` content and `AGENTS.md` from the repo root (if it exists).

**Rationale**: `MemoryMiddleware.__init__` takes the same `backend + sources` signature as `SkillsMiddleware`. Writing plan text and repo context to a temp directory is the simplest way to inject them without modifying deepagents internals. This replaces the current `_SYSTEM_TEMPLATE` string interpolation.

**Alternatives considered**:
- Passing plan context via `system_prompt=` directly to `create_deep_agent`: simpler but bypasses MemoryMiddleware's progressive disclosure; fine for plan context but not for repo context that may be large.

---

## Decision 5: SummarizationMiddleware for auto context compaction

**Decision**: Wire `SummarizationMiddleware(model="claude-sonnet-4-6", backend=FilesystemBackend(), keep=("messages", 20))` with default trigger (context-size based).

**Rationale**: Replaces the current hard 50-turn loop exit. The default trigger activates summarisation when approaching token limits. `keep=("messages", 20)` retains the 20 most recent messages after summarisation. This is the direct replacement for the `for _ in range(50)` loop guard.

**Alternatives considered**:
- Keeping the 50-turn hard limit as a custom tool/wrapper: possible but loses auto-summarisation; the agent may still hit token limits.

---

## Decision 6: State bridge — AgentState → BuildAttempt

**Decision**: After `agent.invoke({"messages": [initial_message]})` returns a final `AgentState`, extract:
- `files_changed`: collect `path` args from all `write_file` tool calls in the message history
- `test_exit_code` + `test_output`: parse the last `run_command` tool result that matches the `test_cmd` pattern
- `passed`: `test_exit_code == 0`
- Construct `BuildAttempt(round, attempt, files_changed, test_output, test_exit_code, passed, timestamp)`

`AgentState` has three fields: `messages` (list of LangChain messages), `jump_to` (ephemeral), `structured_response` (optional). All extraction happens from `messages`.

**Rationale**: The bridge is ~30 lines: invoke the agent, walk the message history once, build the `BuildAttempt`. No schema changes to `RunState` are needed.

**Alternatives considered**:
- Using `response_format=BuildAttempt` in `create_deep_agent`: cleaner but forces the agent to produce structured JSON at end of run; adds prompt complexity and may interfere with tool-use mode.

---

## Decision 7: Critic → Reviewer rename scope

**Decision**: Rename all occurrences in the following files (no behaviour change):

| File | Change |
|------|--------|
| `bureau/state.py` | `Phase.CRITIC = "critic"` → `Phase.REVIEWER = "reviewer"`; `RepoContext.critic_model` → `reviewer_model` |
| `bureau/models.py` | `CriticFinding` → `ReviewerFinding`; `CriticVerdict` → `ReviewerVerdict`; `RalphRound.critic_verdict` → `reviewer_verdict`; `RalphRound.critic_findings` → `reviewer_findings` |
| `bureau/nodes/critic.py` | Rename to `reviewer.py`; `critic_node` → `reviewer_node`; all internal string literals |
| `bureau/personas/critic.py` | Rename to `reviewer.py`; `run_critic` → `run_reviewer` |
| `bureau/graph.py` | Import `reviewer_node`; node name `"critic"` → `"reviewer"`; `_route_critic` → `_route_reviewer` |
| `bureau/config.py` | `critic_model` → `reviewer_model` |
| `bureau/memory.py` | `"critic_findings"` key → `"reviewer_findings"` |
| `bureau/nodes/builder.py` | Any references to `Phase.CRITIC` → `Phase.REVIEWER` |
| `bureau/nodes/pr_create.py` | `critic_findings` → `reviewer_findings` references |
| `tests/unit/test_persona_critic.py` | Rename to `test_persona_reviewer.py`; update imports and assertions |
| `tests/integration/test_critic_node.py` | Rename to `test_reviewer_node.py`; update imports and assertions |
| `tests/integration/test_graph_run.py` | Update any "critic" phase string assertions |
| `tests/e2e/test_bureau_e2e.py` | Update `expected_phases` list: `"critic"` → `"reviewer"` |
| `.specify/memory/constitution.md` | PATCH amendment v1.1.0 → v1.2.0: "Critic" → "Reviewer" in Principle III and Agent Personas table |

**Rationale**: A name that more accurately describes the pair-programmer "reviewer" role. Isolated rename with no logic change minimises risk.

---

## Decision 8: ASDLC skills vendoring — addyosmani/agent-skills

**Decision**: Fetch SKILL.md files from `https://github.com/addyosmani/agent-skills` and copy the `build`, `test`, `ship`, and `review` skills (and any immediately useful supporting skills) into the corresponding `bureau/skills/default/{role}/` subdirectories.

**Rationale**: The `addyosmani/agent-skills` SKILL.md format uses YAML frontmatter + markdown body — the same format that `SkillsMiddleware` `FilesystemBackend` discovers. Skills are static files committed to the repo; no runtime download required.

**Alternatives considered**:
- Writing ASDLC skills from scratch: more control but unnecessary given the existing open-source collection is purpose-built for this use case.
- Symlinking or submoduling the upstream repo: rejected — vendoring ensures stability and avoids external dependency on upstream changes.

---

## Decision 9: deepagents as Builder-only, Reviewer stays native

**Decision**: deepagents is scoped exclusively to the Builder node. The Reviewer continues using the Anthropic SDK directly (`anthropic.Anthropic().messages.create()`). No deepagents wrapper around the Reviewer.

**Rationale**: The Reviewer makes a single structured LLM call (JSON verdict). There is no tool-use loop, no file access, and no context pressure. deepagents adds middleware overhead with no benefit for a single-call structured-output node.

---

## Dependency Resolution

deepagents 0.5.3 is already present in `.venv` (installed during the spike). Adding `deepagents>=0.5.3` to `pyproject.toml` formalises it. deepagents depends on `langchain`, `langgraph`, and `langchain-anthropic`; version compatibility with the existing `langgraph>=0.2` constraint must be verified at `pip install` time. No conflicts observed in the spike environment.
