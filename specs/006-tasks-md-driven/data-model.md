# Data Model: Tasks.md-Driven Execution

## Entities

### TaskItem (parsed from tasks.md line)

| Field | Type | Source |
|-------|------|--------|
| `id` | `str` | Extracted via `re.search(r"T\d+", line)`, e.g. `"T001"` |
| `description` | `str` | Full line text after stripping `- [ ] ` prefix |
| `fr_ids` | `list[str]` | Empty list (not parsed from tasks.md; FR mapping is in the task description text) |
| `depends_on` | `list[str]` | Empty list (order implied by line order) |
| `files_affected` | `list[str]` | Empty list |
| `done` | `bool` | `False` (only incomplete tasks are extracted) |

Maps directly to the existing `Task` pydantic model in `bureau/models.py`.

### TaskPlan (built from parsed TaskItems)

| Field | Type | Value |
|-------|------|-------|
| `tasks` | `list[Task]` | All incomplete TaskItems in line order |
| `spec_name` | `str` | Derived from spec folder name or `spec.md` H1 title |
| `fr_coverage` | `list[str]` | Empty list (not tracked at load time) |
| `uncovered_frs` | `list[str]` | Empty list |
| `created_at` | `str` | ISO timestamp at load time |

### State additions

| Key | Type | Description |
|-----|------|-------------|
| `spec_folder` | `str` | Absolute path to the spec folder |
| `tasks_path` | `str` | Absolute path to tasks.md |
| `plan_text` | `str` | Content of plan.md if present, else `""` |

### EscalationReason additions

| Value | Trigger |
|-------|---------|
| `TASKS_MISSING` | tasks.md not found, or found but no `- [ ]` lines parseable |
| `TASKS_COMPLETE` | tasks.md found but all tasks are `- [x]` (none incomplete) |
