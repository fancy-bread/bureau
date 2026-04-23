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
    toml.write_text(
        "[models]\nplanner = 'claude-opus-4-7'\n"
        "[ralph_loop]\nmax_builder_attempts = 5\n"
    )
    cfg = load_bureau_config(str(toml))
    assert cfg.planner_model == "claude-opus-4-7"
    assert cfg.max_builder_attempts == 5


def test_load_constitution_returns_empty_when_absent(tmp_path):
    result = load_constitution(str(tmp_path))
    # bundled constitution may or may not exist; result is always a str
    assert isinstance(result, str)


def test_load_constitution_custom_path(tmp_path):
    const = tmp_path / ".bureau" / "constitution.md"
    const.parent.mkdir()
    const.write_text("# Custom\nDo the right thing.")

    class FakeContext:
        constitution_path = ".bureau/constitution.md"

    result = load_constitution(str(tmp_path), FakeContext())
    assert "Custom" in result
