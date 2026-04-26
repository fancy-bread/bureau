from __future__ import annotations

import json

from bureau.models import PipelinePhase, PipelineResult
from bureau.tools.shell_tools import execute_shell_tool


def run_pipeline(
    repo_path: str,
    phases: list[tuple[PipelinePhase, str]],
    timeout: int,
) -> PipelineResult:
    """Execute pipeline phases in order; stop on first non-zero exit."""
    phases_run: list[PipelinePhase] = []
    for phase, cmd in phases:
        phases_run.append(phase)
        raw = execute_shell_tool("run_command", {"command": cmd}, repo_path, timeout)
        parsed = json.loads(raw)
        if parsed["exit_code"] != 0:
            output = (parsed.get("stdout", "") + "\n" + parsed.get("stderr", "")).strip()
            return PipelineResult(
                passed=False,
                failed_phase=phase,
                failed_output=output[:2000],
                phases_run=list(phases_run),
            )
    return PipelineResult(passed=True, phases_run=list(phases_run))
