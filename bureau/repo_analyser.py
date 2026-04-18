from __future__ import annotations

import tomllib
from pathlib import Path

from bureau.state import RepoContext


class ConfigMissingError(Exception):
    pass


class ConfigInvalidError(Exception):
    pass


_REQUIRED_FIELDS = ("language", "base_image", "install_cmd", "test_cmd")


def parse_repo_config(repo_path: str) -> RepoContext:
    config_path = Path(repo_path) / ".bureau" / "config.toml"
    if not config_path.exists():
        raise ConfigMissingError(
            f".bureau/config.toml not found in {repo_path}. "
            "Run `bureau init --repo <path>` to create one."
        )
    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigInvalidError(f"Failed to parse .bureau/config.toml: {exc}") from exc

    runtime = data.get("runtime", {})
    missing = [f for f in _REQUIRED_FIELDS if not runtime.get(f, "").strip()]
    if missing:
        raise ConfigInvalidError(
            f".bureau/config.toml is missing required fields: {', '.join(missing)}"
        )

    bureau_section = data.get("bureau", {})
    ralph_loop = data.get("ralph_loop", {})

    max_ba = int(ralph_loop.get("max_builder_attempts", 3))
    max_rr = int(ralph_loop.get("max_rounds", 3))
    cmd_timeout = int(ralph_loop.get("command_timeout", 300))
    if max_ba < 1:
        raise ConfigInvalidError("ralph_loop.max_builder_attempts must be >= 1")
    if max_rr < 1:
        raise ConfigInvalidError("ralph_loop.max_rounds must be >= 1")
    if cmd_timeout <= 0:
        raise ConfigInvalidError("ralph_loop.command_timeout must be > 0")

    return RepoContext(
        language=runtime["language"],
        base_image=runtime["base_image"],
        install_cmd=runtime["install_cmd"],
        test_cmd=runtime["test_cmd"],
        build_cmd=runtime.get("build_cmd", ""),
        lint_cmd=runtime.get("lint_cmd", ""),
        constitution_path=bureau_section.get("constitution"),
        max_builder_attempts=max_ba,
        max_ralph_rounds=max_rr,
        command_timeout=cmd_timeout,
        planner_model=bureau_section.get("planner_model", "claude-opus-4-7"),
        builder_model=bureau_section.get("builder_model", "claude-sonnet-4-6"),
        critic_model=bureau_section.get("critic_model", "claude-opus-4-7"),
    )
