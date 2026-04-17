from __future__ import annotations

import re
from pathlib import Path

from bureau.state import FunctionalRequirement, Spec, UserStory


class SpecParseError(Exception):
    pass


_REQUIRED_SECTIONS = {
    "User Scenarios & Testing",
    "Requirements",
    "Success Criteria",
}

_FR_PATTERN = re.compile(r"\*\*FR-(\d{3})\*\*:\s*(.+)")
_NEEDS_CLARIFICATION_PATTERN = re.compile(r"\[NEEDS CLARIFICATION", re.IGNORECASE)
_PRIORITY_PATTERN = re.compile(r"\(Priority:\s*(P\d+)\)", re.IGNORECASE)
_BRANCH_PATTERN = re.compile(r"\*\*Feature Branch\*\*:\s*`([^`]+)`")
_STATUS_PATTERN = re.compile(r"\*\*Status\*\*:\s*(.+)")


def parse_spec(path: str) -> Spec:
    text = Path(path).read_text()
    lines = text.splitlines()

    name = _extract_h1(lines)
    branch = _extract_inline(text, _BRANCH_PATTERN)
    status = _extract_inline(text, _STATUS_PATTERN)

    _check_required_sections(text)

    user_stories = _parse_user_stories(lines)
    functional_requirements = _parse_functional_requirements(lines)
    success_criteria = _parse_list_section(text, "Success Criteria")
    edge_cases = _parse_list_section(text, "Edge Cases")
    assumptions = _parse_list_section(text, "Assumptions")

    return Spec(
        name=name,
        branch=branch,
        status=status,
        user_stories=user_stories,
        functional_requirements=functional_requirements,
        success_criteria=success_criteria,
        edge_cases=edge_cases,
        assumptions=assumptions,
    )


def _extract_h1(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    raise SpecParseError("No H1 title found in spec")


def _extract_inline(text: str, pattern: re.Pattern[str]) -> str:
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def _check_required_sections(text: str) -> None:
    missing = [s for s in _REQUIRED_SECTIONS if s not in text]
    if missing:
        raise SpecParseError(f"Missing required sections: {', '.join(missing)}")


def _parse_user_stories(lines: list[str]) -> list[UserStory]:
    stories: list[UserStory] = []
    in_stories = False
    current: dict | None = None
    scenarios: list[str] = []

    for line in lines:
        if "## User Scenarios" in line:
            in_stories = True
            continue
        if in_stories and line.startswith("## ") and "User Scenarios" not in line:
            if current is not None:
                stories.append(UserStory(**current, acceptance_scenarios=scenarios))
                current = None
            break
        if not in_stories:
            continue

        if line.startswith("### ") and "Edge Cases" not in line:
            if current is not None:
                stories.append(UserStory(**current, acceptance_scenarios=scenarios))
            title = re.sub(r"\s*\(Priority:.*?\)", "", line[4:]).strip()
            m = _PRIORITY_PATTERN.search(line)
            priority = m.group(1) if m else "P1"
            current = {"title": title, "priority": priority, "description": ""}
            scenarios = []
        elif current is not None:
            if line.strip().startswith("1. **Given**") or line.strip().startswith("2. **Given**"):
                scenarios.append(line.strip())
            elif not line.startswith("#") and not line.startswith("**"):
                current["description"] = (current["description"] + " " + line).strip()

    if current is not None:
        stories.append(UserStory(**current, acceptance_scenarios=scenarios))

    return stories


_CODE_SPAN_PATTERN = re.compile(r"`[^`]+`")


def _parse_functional_requirements(lines: list[str]) -> list[FunctionalRequirement]:
    reqs: list[FunctionalRequirement] = []
    for line in lines:
        m = _FR_PATTERN.search(line)
        if m:
            fr_id = f"FR-{m.group(1)}"
            text = m.group(2).strip()
            # Strip code spans before checking — backtick-wrapped text is documentation,
            # not an actual unresolved marker.
            text_outside_code = _CODE_SPAN_PATTERN.sub("", text)
            needs_clarification = bool(_NEEDS_CLARIFICATION_PATTERN.search(text_outside_code))
            reqs.append(FunctionalRequirement(id=fr_id, text=text, needs_clarification=needs_clarification))
    return reqs


def _parse_list_section(text: str, section_name: str) -> list[str]:
    pattern = re.compile(
        rf"##[#]?\s+{re.escape(section_name)}.*?\n(.*?)(?=\n##\s|\Z)",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return []
    block = m.group(1)
    return [
        line.lstrip("-* ").strip()
        for line in block.splitlines()
        if line.strip().startswith(("-", "*"))
    ]
