from __future__ import annotations

import json
from unittest.mock import MagicMock

from bureau.models import ReviewerVerdict
from bureau.personas.reviewer import run_reviewer

_PASS_VERDICT = {
    "verdict": "pass",
    "findings": [
        {
            "type": "requirement",
            "ref_id": "FR-001",
            "verdict": "met",
            "detail": "Feature X is implemented in bureau/nodes/example.py",
            "remediation": "",
        }
    ],
    "summary": "All requirements met.",
    "round": 0,
}

_REVISE_VERDICT = {
    "verdict": "revise",
    "findings": [
        {
            "type": "requirement",
            "ref_id": "FR-001",
            "verdict": "met",
            "detail": "Feature X implemented.",
            "remediation": "",
        },
        {
            "type": "requirement",
            "ref_id": "FR-002",
            "verdict": "unmet",
            "detail": "Feature Y is missing.",
            "remediation": "Implement Feature Y in bureau/nodes/y.py",
        },
    ],
    "summary": "FR-002 is unmet.",
    "round": 0,
}


def _make_client(response_json: dict) -> MagicMock:
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(response_json)

    response = MagicMock()
    response.content = [text_block]

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_run_reviewer_returns_pass_verdict(tmp_path):
    client = _make_client(_PASS_VERDICT)

    result = run_reviewer(
        client=client,
        spec_text="- **FR-001**: Do X.",
        constitution="Constitution.",
        builder_summary="Implemented X.",
        ralph_round=0,
        model="claude-opus-4-7",
    )

    assert isinstance(result, ReviewerVerdict)
    assert result.verdict == "pass"
    assert len(result.findings) == 1
    assert result.findings[0].verdict == "met"
    assert result.findings[0].ref_id == "FR-001"


def test_run_reviewer_returns_revise_verdict(tmp_path):
    client = _make_client(_REVISE_VERDICT)

    result = run_reviewer(
        client=client,
        spec_text="- **FR-001**: Do X.\n- **FR-002**: Do Y.",
        constitution="",
        builder_summary="Implemented X but not Y.",
        ralph_round=0,
        model="claude-opus-4-7",
    )

    assert result.verdict == "revise"
    unmet = [f for f in result.findings if f.verdict == "unmet"]
    assert len(unmet) == 1
    assert unmet[0].ref_id == "FR-002"
    assert unmet[0].remediation != ""


def test_run_reviewer_forces_escalate_on_constitution_violation():
    """Any 'violation' finding must force overall verdict to 'escalate'."""
    mixed = {
        "verdict": "revise",
        "findings": [
            {
                "type": "constitution",
                "ref_id": "III. Verification Gates",
                "verdict": "violation",
                "detail": "Gate skipped.",
                "remediation": "Do not skip.",
            }
        ],
        "summary": "Violation found.",
        "round": 0,
    }
    client = _make_client(mixed)

    result = run_reviewer(
        client=client,
        spec_text="",
        constitution="",
        builder_summary="",
        ralph_round=0,
        model="claude-opus-4-7",
    )

    assert result.verdict == "escalate"


def test_run_reviewer_passes_fr_lines_to_prompt():
    """Reviewer extracts FR lines from spec_text for the prompt."""
    spec_text = (
        "# My Feature\n\n## Requirements\n\n- **FR-001**: Do X.\n- **FR-002**: Do Y.\nSome other text.\n"
    )

    client = _make_client(_PASS_VERDICT)
    run_reviewer(
        client=client,
        spec_text=spec_text,
        constitution="",
        builder_summary="Done.",
        ralph_round=0,
        model="claude-opus-4-7",
    )

    call_system = client.messages.create.call_args.kwargs["system"]
    system_text = call_system[0]["text"]
    assert "FR-001" in system_text
    assert "FR-002" in system_text
