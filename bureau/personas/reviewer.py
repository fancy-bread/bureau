from __future__ import annotations

import json
import re
from typing import Any

import anthropic

from bureau.models import ReviewerVerdict

_SYSTEM_TEMPLATE = """\
You are Bureau's Reviewer persona. Audit the Builder's implementation against the spec's \
functional requirements and the Spec Kit constitution.

## Spec Kit Constitution
{constitution}

## Spec Functional Requirements
{fr_list}

## Instructions
Evaluate the Builder's implementation summary against EVERY functional requirement listed above.
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


def run_reviewer(
    client: anthropic.Anthropic,
    spec_text: str,
    constitution: str,
    builder_summary: str,
    ralph_round: int,
    model: str,
) -> ReviewerVerdict:
    fr_lines = [line.strip() for line in spec_text.splitlines() if _FR_LINE.match(line.strip())]
    fr_list = "\n".join(fr_lines) if fr_lines else spec_text

    system = _SYSTEM_TEMPLATE.format(
        constitution=constitution,
        fr_list=fr_list,
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

    if any(f.verdict == "violation" for f in verdict.findings):
        return ReviewerVerdict(
            verdict="escalate",
            findings=verdict.findings,
            summary=verdict.summary,
            round=verdict.round,
        )

    return verdict
