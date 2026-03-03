"""CLI integration tests — verify state changes, not just output strings."""

import pytest
from click.testing import CliRunner

from zsh_focus.cli import cli
from zsh_focus.config import load_config, load_state


@pytest.fixture
def runner(config_dir):
    return CliRunner()


# ── focus new ─────────────────────────────────────────────────────────────────


def test_new_creates_mode(runner):
    """Mode should be persisted to config after creation."""
    runner.invoke(cli, ["new", "work"])
    assert "work" in load_config()["modes"]


def test_new_strict_sets_flag(runner):
    """--strict flag should be stored in config, not just echoed."""
    runner.invoke(cli, ["new", "work", "--strict"])
    assert load_config()["modes"]["work"]["strict"] is True


def test_new_lenient_by_default(runner):
    """Modes are lenient unless --strict is passed explicitly."""
    runner.invoke(cli, ["new", "work"])
    assert load_config()["modes"]["work"]["strict"] is False


def test_new_duplicate_does_not_overwrite(runner):
    """Creating a mode that already exists should be a no-op, not reset its settings."""
    runner.invoke(cli, ["new", "work", "--strict"])
    runner.invoke(cli, ["new", "work"])
    assert load_config()["modes"]["work"]["strict"] is True


# ── focus on / off ────────────────────────────────────────────────────────────


def test_on_sets_active_mode(runner):
    """State file should record the newly activated mode."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["on", "work"])
    assert load_state().active_mode == "work"


def test_on_writes_compiled_zsh(runner, config_dir):
    """Activating a mode must produce compiled.zsh with the mode name embedded."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["on", "work"])
    compiled = config_dir / "compiled.zsh"
    assert compiled.exists()
    assert 'ZSH_FOCUS_ACTIVE_MODE="work"' in compiled.read_text()


def test_on_writes_mode_paths_to_compiled_zsh(runner, config_dir, tmp_path):
    """Whitelist and blacklist paths for the active mode should appear in compiled.zsh."""
    allow_dir = tmp_path / "allowed"
    ban_dir = tmp_path / "banned"
    allow_dir.mkdir()
    ban_dir.mkdir()
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["path", "allow", str(allow_dir), "-m", "work"])
    runner.invoke(cli, ["path", "ban", str(ban_dir), "-m", "work"])
    runner.invoke(cli, ["on", "work"])
    compiled = (config_dir / "compiled.zsh").read_text()
    assert str(allow_dir) in compiled
    assert str(ban_dir) in compiled


def test_on_unknown_mode_fails(runner):
    """Activating a non-existent mode must fail and leave state untouched."""
    result = runner.invoke(cli, ["on", "nonexistent"])
    assert result.exit_code != 0
    assert load_state().active_mode == ""


def test_off_clears_active_mode(runner):
    """After 'off', state should record no active mode (empty string)."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["on", "work"])
    runner.invoke(cli, ["off"])
    assert load_state().active_mode == ""


def test_off_clears_compiled_zsh(runner, config_dir):
    """'off' must recompile with an empty mode so the shell picks up the cleared state."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["on", "work"])
    runner.invoke(cli, ["off"])
    compiled = (config_dir / "compiled.zsh").read_text()
    assert 'ZSH_FOCUS_ACTIVE_MODE=""' in compiled


# ── focus set ─────────────────────────────────────────────────────────────────


def test_set_strict_updates_config(runner):
    """'set --strict' should persist the change, not just print a message."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["set", "work", "--strict"])
    assert load_config()["modes"]["work"]["strict"] is True


def test_set_no_strict_updates_config(runner):
    """'set --no-strict' should clear the flag that was set at creation."""
    runner.invoke(cli, ["new", "work", "--strict"])
    runner.invoke(cli, ["set", "work", "--no-strict"])
    assert load_config()["modes"]["work"]["strict"] is False


def test_set_unknown_mode_fails(runner):
    """Attempting to configure a non-existent mode must fail with a non-zero exit."""
    result = runner.invoke(cli, ["set", "nonexistent", "--strict"])
    assert result.exit_code != 0


def test_set_strict_on_active_mode_updates_compiled_zsh(runner, config_dir):
    """Setting strict on the active mode should recompile immediately."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["on", "work"])
    runner.invoke(cli, ["set", "work", "--strict"])
    assert 'ZSH_FOCUS_STRICT="true"' in (config_dir / "compiled.zsh").read_text()


# ── focus path allow ──────────────────────────────────────────────────────────


def test_allow_adds_to_always_whitelist(runner, tmp_path):
    """Without -m, 'path allow' should add to the always whitelist, not a mode."""
    d = tmp_path / "work"
    d.mkdir()
    runner.invoke(cli, ["path", "allow", str(d)])
    assert str(d) in load_config()["always"]["whitelist"]


def test_allow_adds_to_mode_whitelist(runner, tmp_path):
    """With -m, 'path allow' should store the path under that mode's whitelist."""
    d = tmp_path / "work"
    d.mkdir()
    runner.invoke(cli, ["new", "focus"])
    runner.invoke(cli, ["path", "allow", str(d), "-m", "focus"])
    assert str(d) in load_config()["modes"]["focus"]["whitelist"]


def test_allow_on_active_mode_updates_compiled_zsh(runner, config_dir, tmp_path):
    """Adding a path to the active mode's whitelist should recompile immediately."""
    d = tmp_path / "work"
    d.mkdir()
    runner.invoke(cli, ["new", "focus"])
    runner.invoke(cli, ["on", "focus"])
    runner.invoke(cli, ["path", "allow", str(d), "-m", "focus"])
    assert str(d) in (config_dir / "compiled.zsh").read_text()


def test_ban_on_active_mode_updates_compiled_zsh(runner, config_dir, tmp_path):
    """Adding a ban to the active mode should recompile immediately."""
    d = tmp_path / "social"
    d.mkdir()
    runner.invoke(cli, ["new", "focus"])
    runner.invoke(cli, ["on", "focus"])
    runner.invoke(cli, ["path", "ban", str(d), "-m", "focus"])
    assert str(d) in (config_dir / "compiled.zsh").read_text()


def test_allow_duplicate_not_added_twice(runner, tmp_path):
    """Calling 'path allow' twice for the same path should not create duplicate entries."""
    d = tmp_path / "work"
    d.mkdir()
    runner.invoke(cli, ["path", "allow", str(d)])
    runner.invoke(cli, ["path", "allow", str(d)])
    assert load_config()["always"]["whitelist"].count(str(d)) == 1


# ── focus path ban ────────────────────────────────────────────────────────────


def test_ban_adds_to_blacklist(runner, tmp_path):
    """'path ban -m <mode>' should persist the path under that mode's blacklist."""
    d = tmp_path / "social"
    d.mkdir()
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["path", "ban", str(d), "-m", "work"])
    assert str(d) in load_config()["modes"]["work"]["blacklist"]


def test_ban_unknown_mode_fails(runner, tmp_path):
    """Banning to a non-existent mode must fail rather than silently creating state."""
    d = tmp_path / "social"
    d.mkdir()
    result = runner.invoke(cli, ["path", "ban", str(d), "-m", "nonexistent"])
    assert result.exit_code != 0


# ── focus path clear ──────────────────────────────────────────────────────────


def test_clear_removes_from_always_whitelist(runner, tmp_path):
    """'path clear' should remove a previously allowed path from the always whitelist."""
    d = tmp_path / "work"
    d.mkdir()
    runner.invoke(cli, ["path", "allow", str(d)])
    runner.invoke(cli, ["path", "clear", str(d)])
    assert str(d) not in load_config()["always"]["whitelist"]


def test_clear_removes_from_blacklist(runner, tmp_path):
    """'path clear -m <mode>' should remove a path from that mode's blacklist."""
    d = tmp_path / "social"
    d.mkdir()
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["path", "ban", str(d), "-m", "work"])
    runner.invoke(cli, ["path", "clear", str(d), "-m", "work"])
    assert str(d) not in load_config()["modes"]["work"]["blacklist"]


def test_clear_removes_from_both_lists(runner, tmp_path):
    """A path on both whitelist and blacklist should be removed from each in one call."""
    d = tmp_path / "work"
    d.mkdir()
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["path", "allow", str(d), "-m", "work"])
    runner.invoke(cli, ["path", "ban", str(d), "-m", "work"])
    runner.invoke(cli, ["path", "clear", str(d), "-m", "work"])
    mc = load_config()["modes"]["work"]
    assert str(d) not in mc["whitelist"]
    assert str(d) not in mc["blacklist"]


def test_clear_nonexistent_entry_exits_cleanly(runner, tmp_path):
    """Clearing a path that was never added should succeed silently, not error."""
    d = tmp_path / "work"
    d.mkdir()
    result = runner.invoke(cli, ["path", "clear", str(d)])
    assert result.exit_code == 0


# ── focus compile ─────────────────────────────────────────────────────────────


def test_compile_regenerates_compiled_zsh(runner, config_dir):
    """'compile' should overwrite a corrupted or stale compiled.zsh from current state."""
    runner.invoke(cli, ["new", "work"])
    runner.invoke(cli, ["on", "work"])
    (config_dir / "compiled.zsh").write_text("corrupted")
    runner.invoke(cli, ["compile"])
    assert 'ZSH_FOCUS_ACTIVE_MODE="work"' in (config_dir / "compiled.zsh").read_text()
