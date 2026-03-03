"""Shared fixtures for zsh-focus tests."""

import pytest


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect all config paths to a temporary directory."""
    d = tmp_path / "zsh-focus"
    d.mkdir()
    monkeypatch.setattr("zsh_focus.config.CONFIG_DIR", d)
    monkeypatch.setattr("zsh_focus.config.CONFIG_FILE", d / "config.toml")
    monkeypatch.setattr("zsh_focus.config.STATE_FILE", d / "state.toml")
    monkeypatch.setattr("zsh_focus.config.COMPILED", d / "compiled.zsh")
    # engine.py imports COMPILED directly, so patch it there too
    monkeypatch.setattr("zsh_focus.engine.COMPILED", d / "compiled.zsh")
    return d
