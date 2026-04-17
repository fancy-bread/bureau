from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BureauConfig:
    planner_model: str = "claude-opus-4-6"
    builder_model: str = "claude-haiku-4-5-20251001"
    critic_model: str = "claude-opus-4-6"
    github_token_env: str = "GITHUB_TOKEN"
    max_retries: int = 3

    def __post_init__(self) -> None:
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")


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

    return BureauConfig(
        planner_model=models.get("planner", "claude-opus-4-6"),
        builder_model=models.get("builder", "claude-haiku-4-5-20251001"),
        critic_model=models.get("critic", "claude-opus-4-6"),
        github_token_env=github.get("token_env", "GITHUB_TOKEN"),
        max_retries=int(bureau.get("max_retries", 3)),
    )
