---
icon: octicons/database-24
---

# State Keys

The LangGraph state dictionary is passed between every node. Each node reads from it and returns a partial update. The full state is checkpointed to SQLite after every node.

This reference is for contributors and integrators who need to understand what data flows through the pipeline.

---

## Identity

| Key | Type | Set by | Description |
|---|---|---|---|
| `run_id` | `str` | `bureau run` | Unique run identifier (`run-<8hex>`) |
| `spec_path` | `str` | `bureau run` | Absolute path to `spec.md` |
| `spec_folder` | `str` | `bureau run` | Directory containing spec artifacts |
| `tasks_path` | `str` | `bureau run` | Absolute path to `tasks.md` |
| `repo_path` | `str` | `bureau run` | Absolute path to target repo |

---

## Pipeline control

| Key | Type | Set by | Description |
|---|---|---|---|
| `phase` | `Phase` | Each node | Current pipeline phase |
| `_route` | `str \| None` | Each node | Routing signal: `"ok"`, `"pass"`, `"revise"`, `"escalate"` |

---

## Spec content

| Key | Type | Set by | Description |
|---|---|---|---|
| `spec` | `ParsedSpec \| None` | `validate_spec` | Parsed spec object with stories and FRs |
| `spec_text` | `str` | `validate_spec` | Raw spec.md text |
| `plan_text` | `str` | `tasks_loader` | Raw plan.md text (empty if absent) |
| `task_plan` | `str \| None` | `tasks_loader` | Parsed task list for Builder |
| `repo_context` | `RepoContext \| None` | `repo_analysis` | Stack config from `.bureau/config.toml` |

---

## Branch and run state

| Key | Type | Set by | Description |
|---|---|---|---|
| `branch_name` | `str` | `prepare_branch` | Feature branch created for this run |
| `ralph_round` | `int` | `reviewer` | Current RALPH round (0-indexed) |
| `builder_attempts` | `int` | `builder` | Attempt count within the current round |

---

## History

| Key | Type | Set by | Description |
|---|---|---|---|
| `build_attempts` | `list[BuildAttempt]` | `builder` | All builder attempts across all rounds |
| `ralph_rounds` | `list[dict]` | `reviewer` | Summary record per completed RALPH round |
| `reviewer_findings` | `list[dict]` | `reviewer` | Latest Reviewer findings (FR-level detail) |
| `escalations` | `list[Escalation]` | Any node | All escalations raised during the run |
| `decisions` | `list` | Reserved | Unused; reserved for future planner output |
| `messages` | `list` | Reserved | Unused; reserved for agent message history |

---

## Output

| Key | Type | Set by | Description |
|---|---|---|---|
| `run_summary` | `dict \| None` | `pr_create`, `escalate_node` | Terminal run summary written to `run-summary.json` |
