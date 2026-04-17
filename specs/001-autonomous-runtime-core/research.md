# Research: Bureau CLI Foundation

**Branch**: `001-autonomous-runtime-core` | **Date**: 2026-04-16

All decisions below were resolved from the TDD (2026-04-15). No NEEDS CLARIFICATION items remain.

---

## 1. Orchestration: LangGraph

**Decision**: LangGraph `StateGraph` for workflow orchestration.

**Rationale**: LangGraph is Python-native, purpose-built for multi-step agent workflows with
state persistence. Its checkpointing model (compile-time `checkpointer` injection) maps
directly to bureau's resumability requirement. The `interrupt_before` compile option provides
the graph-pause mechanism needed for escalations without custom logic.

**Alternatives considered**:
- Prefect / Airflow: Too heavy; optimised for data pipelines, not agent loops
- Custom state machine (plain Python): Would require reimplementing checkpointing, interrupts, and conditional routing from scratch
- LangChain chains: No built-in interrupt/resume; not designed for multi-persona handoffs

---

## 2. Checkpointing: SqliteSaver (per-run)

**Decision**: `langgraph-checkpoint-sqlite` `SqliteSaver`, one SQLite file per run at
`~/.bureau/runs/<run-id>/checkpoint.db`.

**Rationale**: SQLite is zero-config, single-file, and sufficient for single-run sequential
execution. Per-run isolation (separate files) means one corrupt run cannot affect others.
LangGraph's `SqliteSaver` is the documented default checkpointer for v1 deployments.

**Alternatives considered**:
- `MemorySaver`: No disk persistence; fails resumability requirement on process kill
- `PostgresSaver`: Correct for parallel runs in v2; over-engineered for v1 single-run sequential execution

**v2 migration path**: Swap `SqliteSaver` for `PostgresSaver` at graph compile time; no graph logic changes required.

---

## 3. CLI Framework: Typer

**Decision**: Typer for the `bureau` CLI.

**Rationale**: Typer provides type-annotated command definitions (Python 3.12 type hints → argument validation), auto-generated `--help`, and a clean subcommand structure. Minimal boilerplate for the 6 commands bureau needs.

**Alternatives considered**:
- Click: Lower-level; Typer is built on Click and adds type safety with less code
- argparse: stdlib but verbose; no auto-help generation from type hints
- Fire: Too magical; auto-generates CLI from any Python object, not suitable for structured subcommand contracts

---

## 4. Spec Kit Markdown Parser

**Decision**: Custom parser using Python stdlib (`re`, string splitting on heading markers).
No external Markdown library.

**Rationale**: The Spec Kit format is a known, stable subset of Markdown with predictable
heading hierarchy. A focused parser that extracts specific sections by `## Heading` and
`### Sub-heading` markers is simpler and more maintainable than pulling in a full Markdown
AST library. The `validate_spec` node only needs to check for required section presence,
FR numbering, and `[NEEDS CLARIFICATION]` markers — all achievable with `re.search`.

**Alternatives considered**:
- `mistletoe` / `markdown-it-py`: Full Markdown parsers; more than needed for structured section extraction
- `frontmatter` library: Only handles YAML front matter, not body sections

---

## 5. Memory Store: JSON File

**Decision**: `Memory` class backed by a JSON file at `~/.bureau/runs/<run-id>/memory.json`.
`write(key, value)` serialises to JSON; `read(key)` deserialises. `summary()` returns `""` in this foundation release.

**Rationale**: JSON file gives persistence across process restarts without a database dependency. The Memory store is small (text summaries and structured dicts) — JSON is sufficient. The interface (`write`/`read`/`summary`) hides the storage backend; switching to a richer store later requires only changing `Memory` internals.

**Alternatives considered**:
- In-memory dict: Fails persistence requirement — lost on process kill; not resumable
- SQLite: Additional schema management for key-value data where JSON is simpler
- Redis: Requires a running server; over-engineered for single-run local execution

---

## 6. Configuration: tomllib (stdlib)

**Decision**: Python 3.11+ `tomllib` (stdlib) for parsing `bureau.toml` and `.bureau/config.toml`.

**Rationale**: TOML is the format specified in the TDD for both config files. `tomllib` is stdlib in Python 3.11+; zero additional dependency. Pydantic is used for schema validation and field coercion after parsing.

**Alternatives considered**:
- `tomli` (third-party backport): Unnecessary — Python 3.12 is the target runtime
- `configparser` (INI format): Wrong format for the specified TOML configs

---

## 7. Run ID Generation

**Decision**: `uuid4()` shortened to 8 hex characters (e.g., `run-a3f2b1c9`).

**Rationale**: Run IDs appear in terminal output and resume commands. Short IDs are easier to copy and type. UUID4 ensures no collision risk for local sequential runs. Full UUID is overkill for a local CLI tool.

---

## 8. Graph Escalation Pause Mechanism

**Decision**: LangGraph `interrupt_before=["escalate"]` at graph compile time.

**Rationale**: LangGraph's `interrupt_before` pauses graph execution before the named node and writes the checkpoint. `bureau resume <run-id>` reinitialises the graph with the same `thread_id` and the graph continues. This requires no custom pause/signal logic — it is the intended LangGraph pattern for human-in-the-loop interruptions.

---

## 9. Stub Node Implementation Pattern

**Decision**: Stub nodes emit `phase.started` and `phase.completed` events, write a clearly
labelled placeholder string to memory (e.g., `"[STUB] planner output — real implementation pending"`),
and return the state unchanged (except for the placeholder write and messages list update).

**Rationale**: Stubs must be clearly identifiable as stubs in run output — no silent pass-throughs
that could be mistaken for real outputs. The placeholder memory write ensures downstream
nodes (and future real implementations) can locate the key and know it's a stub.
