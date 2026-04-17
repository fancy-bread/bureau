# Data Model: Bureau CLI Foundation

**Branch**: `001-autonomous-runtime-core` | **Date**: 2026-04-16

---

## RunState

LangGraph shared state. Passed between all graph nodes. Defined as a `TypedDict`.

```python
class RunState(TypedDict):
    run_id: str                          # e.g. "run-a3f2b1c9"
    spec_path: str                       # absolute path to spec.md
    repo_path: str                       # absolute path to target repo
    phase: Phase                         # current phase enum value
    spec: Optional[Spec]                 # populated by validate_spec node
    repo_context: Optional[RepoContext]  # populated by repo_analysis node
    escalations: list[Escalation]        # accumulated across run
    decisions: list[str]                 # plain-text decision log entries
    messages: Annotated[list, add_messages]  # current-phase messages (LangGraph managed)
```

**Validation rules**:
- `run_id` is immutable after creation
- `phase` transitions are one-directional; no node may set `phase` to an earlier value
- `spec` must be non-None before `planner` node executes (enforced by graph routing)
- `repo_context` must be non-None before `planner` node executes (enforced by graph routing)

---

## Phase

```python
from enum import StrEnum

class Phase(StrEnum):
    VALIDATE_SPEC  = "validate_spec"
    REPO_ANALYSIS  = "repo_analysis"
    MEMORY         = "memory"
    PLANNER        = "planner"
    BUILDER        = "builder"
    CRITIC         = "critic"
    PR_CREATE      = "pr_create"
    ESCALATE       = "escalate"
    COMPLETE       = "complete"
    FAILED         = "failed"
```

---

## Spec

Parsed from the spec.md Spec Kit Markdown file.

```python
@dataclass
class Spec:
    name: str                                    # from H1 heading
    branch: str                                  # from "Feature Branch" metadata line
    status: str                                  # from "Status" metadata line
    user_stories: list[UserStory]
    functional_requirements: list[FunctionalRequirement]
    success_criteria: list[str]
    edge_cases: list[str]
    assumptions: list[str]

@dataclass
class UserStory:
    title: str
    priority: str                                # "P1", "P2", "P3"
    description: str
    acceptance_scenarios: list[str]

@dataclass
class FunctionalRequirement:
    id: str                                      # "FR-001"
    text: str
    needs_clarification: bool                    # True if text contains "[NEEDS CLARIFICATION"
```

**Validation rules** (enforced by `validate_spec` node):
- At least one `UserStory` with `priority == "P1"` must exist
- All `FunctionalRequirement.id` must match pattern `FR-\d{3}`
- No `FunctionalRequirement` may have `needs_clarification == True`
- Required sections must be present: User Scenarios, Requirements, Success Criteria

---

## RepoContext

Parsed from `.bureau/config.toml` in the target repo.

```python
@dataclass
class RepoContext:
    language: str           # e.g. "python", "typescript"
    base_image: str         # e.g. "python:3.12-slim"
    install_cmd: str        # e.g. "pip install -e ."
    build_cmd: str          # e.g. "python -m build"
    test_cmd: str           # e.g. "pytest"
    lint_cmd: str           # e.g. "ruff check ."
    constitution_path: Optional[str]  # relative path; None if not specified
```

**Validation rules**:
- `language`, `base_image`, `install_cmd`, `test_cmd` are required; `build_cmd` and `lint_cmd` default to `""`
- `constitution_path` is optional; defaults to bureau's bundled constitution if absent

---

## Escalation

Structured record of a blocker surfaced to the operator.

```python
@dataclass
class Escalation:
    run_id: str
    phase: Phase
    reason: EscalationReason
    what_happened: str
    what_is_needed: str
    options: list[str]
    timestamp: str           # ISO 8601

class EscalationReason(StrEnum):
    SPEC_INVALID         = "SPEC_INVALID"
    CONFIG_MISSING       = "CONFIG_MISSING"
    BLOCKER              = "BLOCKER"
    CONSTITUTION_CRITICAL = "CONSTITUTION_CRITICAL"
    MAX_RETRIES          = "MAX_RETRIES"
```

---

## Memory

Shared scratchpad for a run. Backed by `~/.bureau/runs/<run-id>/memory.json`.

```python
class Memory:
    def write(self, key: str, value: Any) -> None: ...
    def read(self, key: str) -> Any: ...           # raises KeyError if not found
    def summary(self) -> str: ...                  # returns "" in this foundation release
```

**Well-known keys** (by convention; not enforced by schema):

| Key | Written by | Type |
|-----|-----------|------|
| `repo_context` | `repo_analysis` | `RepoContext` (serialised) |
| `spec_summary` | `validate_spec` | `str` |
| `plan` | `planner` (stub) | `str` (placeholder) |
| `task_list` | `planner` (stub) | `str` (placeholder) |
| `constitution_self_check` | `planner` (stub) | `str` (placeholder) |
| `implementation_notes` | `builder` (stub) | `str` (placeholder) |
| `critic_findings` | `critic` (stub) | `str` (placeholder) |
| `decisions` | all nodes | `list[str]` |

---

## BureauConfig

Operator-level config loaded from `bureau.toml` in the working directory.

```python
@dataclass
class BureauConfig:
    github_token_env: str = "GITHUB_TOKEN"   # env var name holding GitHub token
    planner_model: str = "claude-opus-4-6"
    builder_model: str = "claude-haiku-4-5-20251001"
    critic_model: str = "claude-opus-4-6"
    max_retries: int = 3
```

**Validation rules**:
- `max_retries` must be >= 1
- All model values must be non-empty strings
- File is optional in this foundation feature; defaults apply when absent

---

## RunRecord

Persisted run metadata (separate from LangGraph checkpoint state). Stored at
`~/.bureau/runs/<run-id>/run.json` for `bureau list` and `bureau show`.

```python
@dataclass
class RunRecord:
    run_id: str
    spec_path: str
    repo_path: str
    status: RunStatus
    current_phase: Phase
    started_at: str          # ISO 8601
    updated_at: str          # ISO 8601
    pr_url: Optional[str]    # None until pr_create completes

class RunStatus(StrEnum):
    RUNNING  = "running"
    PAUSED   = "paused"      # awaiting escalation response
    COMPLETE = "complete"
    FAILED   = "failed"
    ABORTED  = "aborted"
```
