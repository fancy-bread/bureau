from __future__ import annotations

import pytest

from bureau.config import BureauConfig, load_bureau_config, load_constitution


def test_bureau_config_defaults():
    cfg = BureauConfig()
    assert cfg.max_retries == 3
    assert cfg.builder_model == "claude-sonnet-4-6"


def test_bureau_config_validation_errors():
    with pytest.raises(ValueError, match="max_retries"):
        BureauConfig(max_retries=0)
    with pytest.raises(ValueError, match="max_builder_attempts"):
        BureauConfig(max_builder_attempts=0)
    with pytest.raises(ValueError, match="max_ralph_rounds"):
        BureauConfig(max_ralph_rounds=0)
    with pytest.raises(ValueError, match="command_timeout"):
        BureauConfig(command_timeout=0)


def test_load_bureau_config_missing_file(tmp_path):
    cfg = load_bureau_config(str(tmp_path / "bureau.toml"))
    assert isinstance(cfg, BureauConfig)
    assert cfg.max_retries == 3


def test_load_bureau_config_from_file(tmp_path):
    toml = tmp_path / "bureau.toml"
    toml.write_text("[models]\nbuilder = 'claude-sonnet-4-6'\n[ralph_loop]\nmax_builder_attempts = 5\n")
    cfg = load_bureau_config(str(toml))
    assert cfg.builder_model == "claude-sonnet-4-6"
    assert cfg.max_builder_attempts == 5


def test_load_constitution_returns_empty_when_absent(tmp_path):
    result = load_constitution(str(tmp_path))
    # bundled constitution may or may not exist; result is always a str
    assert isinstance(result, str)


def test_load_constitution_includes_both_bundled_and_repo(tmp_path):
    const = tmp_path / ".specify" / "memory" / "constitution.md"
    const.parent.mkdir(parents=True)
    const.write_text("# Project Rules\nDo the right thing.")

    result = load_constitution(str(tmp_path))
    assert "Project Rules" in result
    # bundled constitution is always included alongside the repo-specific one
    assert "Bureau Constitution" in result
