from __future__ import annotations

from bureau.nodes.validate_spec import validate_spec_node
from bureau.state import EscalationReason, Phase, make_initial_state


def _make_state(spec_path: str, **overrides):
    state = make_initial_state("run-vs-001", spec_path, "/tmp/repo")
    return {**state, **overrides}


_VALID_SPEC = """\
# Feature: Test

## User Scenarios & Testing

### User Story 1 (Priority: P1)

A user does something.

**Acceptance Scenarios**:
1. **Given** X **When** Y **Then** Z.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST do something.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Something measurable.

## Assumptions

- None.
"""


def test_valid_spec_routes_ok(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_VALID_SPEC)
    state = _make_state(str(spec_file))
    result = validate_spec_node(state)
    assert result["_route"] == "ok"
    assert result["phase"] == Phase.REPO_ANALYSIS


def test_missing_p1_story_escalates(tmp_path):
    spec_file = tmp_path / "spec.md"
    # Spec with only P2 story
    spec_file.write_text(_VALID_SPEC.replace("Priority: P1", "Priority: P2"))
    state = _make_state(str(spec_file))
    result = validate_spec_node(state)
    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.SPEC_INVALID


def test_needs_clarification_escalates(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_VALID_SPEC.replace("MUST do something", "MUST [NEEDS CLARIFICATION: what?]"))
    state = _make_state(str(spec_file))
    result = validate_spec_node(state)
    assert result["_route"] == "escalate"
    esc = result["escalations"][-1]
    assert esc.reason == EscalationReason.SPEC_INVALID


def test_parse_error_escalates(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("# Not a real spec\n\nMissing all sections.\n")
    state = _make_state(str(spec_file))
    result = validate_spec_node(state)
    assert result["_route"] == "escalate"
