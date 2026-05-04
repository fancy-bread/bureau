from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BureauConfig:
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
        builder_model=models.get("builder", bureau.get("builder_model", "claude-sonnet-4-6")),
        reviewer_model=models.get("reviewer", bureau.get("reviewer_model", "claude-opus-4-7")),
        github_token_env=github.get("token_env", "GITHUB_TOKEN"),
        max_retries=int(bureau.get("max_retries", 3)),
        max_builder_attempts=int(ralph_loop.get("max_builder_attempts", 3)),
        max_ralph_rounds=int(ralph_loop.get("max_rounds", 3)),
        command_timeout=int(ralph_loop.get("command_timeout", 300)),
    )


_BUNDLED_CONSTITUTION = Path(__file__).parent / "data" / "constitution.md"


_SPECKIT_CONSTITUTION = ".specify/memory/constitution.md"


def load_constitution(repo_path: str) -> str:
    """Return the bureau runtime constitution plus any repo-specific constitution.

    The bundled constitution always applies — it contains the non-negotiable runtime
    rules (phase-end commits, escalation behaviour, verification gates). If the target
    repo has a speckit constitution, it is appended so the Builder respects both.
    """
    parts: list[str] = []

    if _BUNDLED_CONSTITUTION.exists():
        parts.append(_BUNDLED_CONSTITUTION.read_text(encoding="utf-8"))

    speckit = Path(repo_path) / _SPECKIT_CONSTITUTION
    if speckit.exists():
        parts.append(speckit.read_text(encoding="utf-8"))

    return "\n\n---\n\n".join(parts)
