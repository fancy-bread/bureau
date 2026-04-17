from __future__ import annotations

import pytest

from bureau.spec_parser import SpecParseError, parse_spec

_VALID_SPEC = """\
# Test Feature

**Feature Branch**: `feature/test`
**Status**: Draft

## User Scenarios & Testing

### Story 1 (Priority: P1)
A user does a thing.

## Requirements

### Functional Requirements

- **FR-001**: System MUST handle the input.
- **FR-002**: System MUST validate the output.

## Success Criteria

### Measurable Outcomes

- SC-001: Task completes in under 1 second.
"""

_SPEC_WITH_CLARIFICATION = """\
# Feature With Clarification

## User Scenarios & Testing

### Story 1 (Priority: P1)
A user does something.

## Requirements

### Functional Requirements

- **FR-001**: System MUST handle [NEEDS CLARIFICATION: what exactly?] inputs.

## Success Criteria

- SC-001: Works correctly.
"""

_SPEC_WITH_CLARIFICATION_IN_CODE_SPAN = """\
# Feature Code Span

## User Scenarios & Testing

### Story 1 (Priority: P1)
Checks `[NEEDS CLARIFICATION]` markers.

## Requirements

### Functional Requirements

- **FR-001**: System MUST strip `[NEEDS CLARIFICATION]` markers from code spans.

## Success Criteria

- SC-001: Works correctly.
"""

_SPEC_MISSING_SECTION = """\
# Incomplete Feature

## User Scenarios & Testing

### Story 1 (Priority: P1)
A user does something.

## Requirements

### Functional Requirements

- **FR-001**: System MUST do something.
"""


def test_valid_spec_parses(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_VALID_SPEC)
    spec = parse_spec(str(spec_file))
    assert spec.name == "Test Feature"
    assert len(spec.functional_requirements) == 2
    assert spec.functional_requirements[0].id == "FR-001"
    assert not spec.functional_requirements[0].needs_clarification
    assert len(spec.user_stories) == 1
    assert spec.user_stories[0].priority == "P1"


def test_needs_clarification_sets_flag(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_SPEC_WITH_CLARIFICATION)
    spec = parse_spec(str(spec_file))
    assert spec.functional_requirements[0].needs_clarification


def test_clarification_in_code_span_ignored(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_SPEC_WITH_CLARIFICATION_IN_CODE_SPAN)
    spec = parse_spec(str(spec_file))
    assert not spec.functional_requirements[0].needs_clarification


def test_missing_required_section_raises(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_SPEC_MISSING_SECTION)
    with pytest.raises(SpecParseError, match="Missing required sections"):
        parse_spec(str(spec_file))


def test_missing_h1_raises(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(
        "No H1 here\n## User Scenarios & Testing\n## Requirements\n## Success Criteria\n"
    )
    with pytest.raises(SpecParseError, match="No H1 title"):
        parse_spec(str(spec_file))
