from __future__ import annotations

import pytest

from bureau.repo_analyser import ConfigInvalidError, ConfigMissingError, parse_repo_config

_VALID_CONFIG = """\
[runtime]
language    = "python"
base_image  = "python:3.12-slim"
install_cmd = "pip install -e ."
test_cmd    = "pytest"
build_cmd   = ""
lint_cmd    = ""

[bureau]
"""


def test_valid_config_parses(tmp_path):
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(_VALID_CONFIG)
    ctx = parse_repo_config(str(tmp_path))
    assert ctx.language == "python"
    assert ctx.base_image == "python:3.12-slim"
    assert ctx.install_cmd == "pip install -e ."
    assert ctx.test_cmd == "pytest"


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigMissingError):
        parse_repo_config(str(tmp_path))


def test_missing_required_field_raises(tmp_path):
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(
        "[runtime]\nlanguage = 'python'\nbase_image = 'python:3.12-slim'\n"
    )
    with pytest.raises(ConfigInvalidError, match="missing required fields"):
        parse_repo_config(str(tmp_path))


def _write_config(tmp_path, extra: str) -> None:
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir(exist_ok=True)
    (bureau_dir / "config.toml").write_text(
        "[runtime]\n"
        'language = "python"\nbase_image = "python:3.14-slim"\n'
        'install_cmd = "pip install -e ."\ntest_cmd = "pytest"\n' + extra
    )


def test_invalid_toml_raises(tmp_path):
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text("[[not valid toml\n")
    with pytest.raises(ConfigInvalidError, match="Failed to parse"):
        parse_repo_config(str(tmp_path))


def test_max_builder_attempts_zero_raises(tmp_path):
    _write_config(tmp_path, "[ralph_loop]\nmax_builder_attempts = 0\n")
    with pytest.raises(ConfigInvalidError, match="max_builder_attempts"):
        parse_repo_config(str(tmp_path))


def test_max_rounds_zero_raises(tmp_path):
    _write_config(tmp_path, "[ralph_loop]\nmax_rounds = 0\n")
    with pytest.raises(ConfigInvalidError, match="max_rounds"):
        parse_repo_config(str(tmp_path))


def test_command_timeout_zero_raises(tmp_path):
    _write_config(tmp_path, "[ralph_loop]\ncommand_timeout = 0\n")
    with pytest.raises(ConfigInvalidError, match="command_timeout"):
        parse_repo_config(str(tmp_path))


def test_optional_fields_default_to_empty(tmp_path):
    bureau_dir = tmp_path / ".bureau"
    bureau_dir.mkdir()
    (bureau_dir / "config.toml").write_text(
        "[runtime]\n"
        'language    = "go"\n'
        'base_image  = "golang:1.22"\n'
        'install_cmd = "go mod download"\n'
        'test_cmd    = "go test ./..."\n'
    )
    ctx = parse_repo_config(str(tmp_path))
    assert ctx.build_cmd == ""
    assert ctx.lint_cmd == ""
    assert ctx.constitution_path is None
