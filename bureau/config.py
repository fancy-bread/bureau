from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BureauConfig:
    planner_model: str = "claude-opus-4-7"
    builder_model: str = "claude-sonnet-4-6"
    reviewer_model: str = "claude-opus-4-7"
    github_token_env: str = "GITHUB_TOKEN"
    max_retries: int = 3
    max_builder_attempts: int = 3
    max_ralph_rounds: int = 3
    command_timeout: int = 300

    def __post_init__(self) -> None:
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if self.max_builder_attempts < 1:
            raise ValueError("max_builder_attempts must be >= 1")
        if self.max_ralph_rounds < 1:
            raise ValueError("max_ralph_rounds must be >= 1")
        if self.command_timeout <= 0:
            raise ValueError("command_timeout must be > 0")


def load_bureau_config(path: str | None = None) -> BureauConfig:
    """Load bureau.toml from path; return defaults if file absent."""
    config_path = Path(path) if path else Path("bureau.toml")
    if not config_path.exists():
        return BureauConfig()

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    models = data.get("models", {})
    github = data.get("github", {})
    bureau = data.get("bureau", {})
    ralph_loop = data.get("ralph_loop", {})

    return BureauConfig(
        planner_model=models.get("planner", bureau.get("planner_model", "claude-opus-4-7")),
        builder_model=models.get("builder", bureau.get("builder_model", "claude-sonnet-4-6")),
        reviewer_model=models.get("reviewer", bureau.get("reviewer_model", "claude-opus-4-7")),
        github_token_env=github.get("token_env", "GITHUB_TOKEN"),
        max_retries=int(bureau.get("max_retries", 3)),
        max_builder_attempts=int(ralph_loop.get("max_builder_attempts", 3)),
        max_ralph_rounds=int(ralph_loop.get("max_rounds", 3)),
        command_timeout=int(ralph_loop.get("command_timeout", 300)),
    )


_BUNDLED_CONSTITUTION = Path(__file__).parent / "data" / "constitution.md"


def load_constitution(repo_path: str, repo_context: Any = None) -> str:
    """Return the project-specific constitution if configured, otherwise the bundled default."""
    if repo_context and getattr(repo_context, "constitution_path", None):
        custom = Path(repo_path) / repo_context.constitution_path
        if custom.exists():
            return custom.read_text(encoding="utf-8")

    if _BUNDLED_CONSTITUTION.exists():
        return _BUNDLED_CONSTITUTION.read_text(encoding="utf-8")

    return ""
