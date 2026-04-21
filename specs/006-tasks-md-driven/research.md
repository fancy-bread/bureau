# Research: Tasks.md-Driven Execution

**Branch**: `006-tasks-md-driven` | **Date**: 2026-04-21

## Decision 1: tasks.md parsing strategy

**Decision**: Use `re.match(r"- \[ \]", line)` to identify incomplete tasks; strip the checkbox prefix and return the remainder as the task description. Parse task ID with `re.search(r"T\d+", line)` for the `id` field.

**Rationale**: The speckit checklist format is well-defined and consistent across all generated tasks.md files. A simple line-by-line regex is deterministic, fast, and has no failure modes beyond an empty file.

**Alternatives considered**: TOML/YAML structured task files — rejected because tasks.md is already the speckit standard and changing the format would break the developer workflow.

---

## Decision 2: TaskPlan compatibility vs. new model

**Decision**: Reuse the existing `TaskPlan` / `Task` pydantic models. Populate them from tasks.md parsing. The builder node reads `state["task_plan"]` as a dict — preserving this key means zero changes to builder.

**Rationale**: The builder already works with `task_plan_dict`. Reusing the model keeps the change surface minimal and avoids touching the builder node at all.

**Alternatives considered**: Replace TaskPlan with a simpler `list[str]` — rejected because it would require builder changes and lose the `id`/`fr_ids` structure that the Critic and PR summary use.

---

## Decision 3: CLI folder vs. file detection

**Decision**: Check `Path(arg).is_dir()`. If dir: `spec_path = arg / "spec.md"`, `tasks_path = arg / "tasks.md"`. If file: `spec_path = arg`, `tasks_path = Path(arg).parent / "tasks.md"`. Store `spec_folder` in state.

**Rationale**: Simple, zero-ambiguity detection. Backwards-compatible with existing `bureau run spec.md` invocations.

**Alternatives considered**: Require folder always — rejected because it breaks all existing tests and local workflows.

---

## Decision 4: Planner node deletion vs. keeping as no-op

**Decision**: Delete `bureau/nodes/planner.py` and `bureau/personas/planner.py` entirely. Remove `Phase.PLANNER` from the Phase enum or keep it for event compatibility — keep it to avoid breaking any stored checkpoint state that references it.

**Rationale**: Dead code is a maintenance liability. The planner persona files have no other callers. `Phase.PLANNER` can stay in the enum harmlessly.

**Alternatives considered**: Keep planner as a disabled no-op — rejected; adds confusion and violates the "no dead code" principle.

---

## Decision 5: plan.md as builder context

**Decision**: If `plan.md` exists in the spec folder, read it and add its content to `state["plan_text"]`. Pass it to the builder as additional system context alongside spec_text. If absent, `plan_text` is empty string.

**Rationale**: plan.md contains architecture decisions, constraints, and file structure that directly inform implementation quality. Cost: one file read. Benefit: builder has richer context without an LLM call.

**Alternatives considered**: Skip plan.md entirely — rejected; it's available and valuable.
