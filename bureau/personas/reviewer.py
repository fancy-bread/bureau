from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import anthropic

from bureau.models import ReviewerFinding, ReviewerVerdict

_SYSTEM_TEMPLATE = """\
You are Bureau's Reviewer persona. Audit the Builder's implementation against the spec's \
functional requirements and the Spec Kit constitution.

## Spec Kit Constitution
{constitution}

## Spec Functional Requirements
{fr_list}

## Changed Files
{file_section}

## Instructions
Evaluate the Builder's implementation against EVERY functional requirement listed above.
Where file contents are provided, base your evaluation on those actual contents.
Also check for any constitution violations.

Respond ONLY with a JSON object (no other text, no code block markers) matching this schema:
{{
  "verdict": "pass" | "revise" | "escalate",
  "findings": [
    {{
      "type": "requirement" | "constitution",
      "ref_id": "FR-001",
      "verdict": "met" | "unmet" | "violation",
      "detail": "what you found in the implementation",
      "remediation": "what Builder must do (empty string if met)"
    }}
  ],
  "summary": "one-sentence summary of the verdict",
  "round": {round}
}}

Routing rules you MUST follow:
- If ANY finding has verdict "violation" → set overall verdict to "escalate"
- If all P1 requirements are "met" and no violations → set verdict to "pass"
- If any P1 requirement is "unmet" (and no violations) → set verdict to "revise"
- Precedence: escalate > revise > pass
"""

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
_FR_LINE = re.compile(r"- \*\*FR-\d{3}\*\*:")
_TEST_FILE_RE = re.compile(r"(^|/)test_.*\.py$|/.*_test\.py$")
_ASSERT_RE = re.compile(r"\bassert\s|self\.assert\w|pytest\.raises|pytest\.approx")


def has_assertions(content: str) -> bool:
    return bool(_ASSERT_RE.search(content))


def _is_test_file(path: str) -> bool:
    p = Path(path)
    return p.name.startswith("test_") or p.name.endswith("_test.py")


def _format_file_section(file_contents: dict[str, str]) -> str:
    if not file_contents:
        return "(no changed files available for review)"
    parts = []
    for path, content in file_contents.items():
        parts.append(f"### {path}\n```\n{content[:3000]}\n```")
    return "\n\n".join(parts)


def run_reviewer(
    client: anthropic.Anthropic,
    spec_text: str,
    constitution: str,
    builder_summary: str,
    ralph_round: int,
    model: str,
    file_contents: dict[str, str] | None = None,
) -> ReviewerVerdict:
    if file_contents is None:
        file_contents = {}

    # Test quality gate (FR-007): automatic revise for non-asserting test files
    quality_findings: list[ReviewerFinding] = []
    for path, content in file_contents.items():
        if _is_test_file(path) and not has_assertions(content):
            quality_findings.append(
                ReviewerFinding(
                    type="pipeline",
                    ref_id="TEST-QUALITY",
                    verdict="unmet",
                    detail=(
                        f"{path}: no assertions found. Test body appears trivially passing "
                        "(pass-only or missing assert statements)."
                    ),
                    remediation=(
                        "Add meaningful assertions that import the module under test, "
                        "call its functions, and verify expected outputs."
                    ),
                )
            )

    if quality_findings:
        return ReviewerVerdict(
            verdict="revise",
            findings=quality_findings,
            summary=f"{len(quality_findings)} test file(s) contain no assertions — automatic revise.",
            round=ralph_round,
        )

    fr_lines = [line.strip() for line in spec_text.splitlines() if _FR_LINE.match(line.strip())]
    fr_list = "\n".join(fr_lines) if fr_lines else spec_text
    _known_fr_ids = {m.group() for line in fr_lines for m in [re.search(r"FR-\d{3}", line)] if m}

    system = _SYSTEM_TEMPLATE.format(
        constitution=constitution,
        fr_list=fr_list,
        file_section=_format_file_section(file_contents),
        round=ralph_round,
    )

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": f"## Builder Implementation Summary (Round {ralph_round})\n\n{builder_summary}",
        }
    ]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )

    final_text = "".join(block.text for block in response.content if hasattr(block, "text"))

    m = _JSON_PATTERN.search(final_text)
    json_text = m.group(0) if m else final_text.strip()

    verdict = ReviewerVerdict.model_validate(json.loads(json_text))

    # Strip findings whose ref_id looks like an FR but isn't in this spec.
    # Prevents the LLM from hallucinating FR IDs that don't exist.
    _fr_ref = re.compile(r"^FR-\d+$")
    if _known_fr_ids:
        valid = [f for f in verdict.findings if not _fr_ref.match(f.ref_id) or f.ref_id in _known_fr_ids]
        if len(valid) < len(verdict.findings):
            has_violation = any(f.verdict == "violation" for f in valid)
            has_unmet = any(f.verdict == "unmet" for f in valid)
            new_v = "escalate" if has_violation else "revise" if has_unmet else "pass"
            verdict = ReviewerVerdict(
                verdict=new_v,
                findings=valid,
                summary=verdict.summary,
                round=verdict.round,
            )

    if any(f.verdict == "violation" for f in verdict.findings):
        return ReviewerVerdict(
            verdict="escalate",
            findings=verdict.findings,
            summary=verdict.summary,
            round=verdict.round,
        )

    return verdict
