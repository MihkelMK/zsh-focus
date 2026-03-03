"""Disk I/O and path helpers for zsh-focus."""

import os
from dataclasses import asdict
from pathlib import Path

import toml

from zsh_focus.types import Config, State

# ── Paths ─────────────────────────────────────────────────────────────────────

CONFIG_DIR: Path = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zsh-focus"
)
CONFIG_FILE: Path = CONFIG_DIR / "config.toml"
STATE_FILE: Path = CONFIG_DIR / "state.toml"
COMPILED: Path = CONFIG_DIR / "compiled.zsh"

PLUGIN_FILE: str = "data/zsh_plugin.zsh"
"""Package-relative path to the bundled zsh integration snippet."""

# ── Helpers ───────────────────────────────────────────────────────────────────


def ensure_dir() -> None:
    """Create CONFIG_DIR (and any parents) if it doesn't exist yet."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def expand(p: str | Path) -> Path:
    """Expand ~ and resolve to an absolute path."""
    return Path(p).expanduser().resolve()


def default_config() -> Config:
    """Return a fresh config with all fields present and set to their defaults.

    Also used as the normalization baseline in load_config — any key missing
    from the file on disk falls back to the value returned here.
    """
    return {
        "always": {"whitelist": []},
        "settings": {
            "block_notification": True,
            "non_interactive_behavior": "block",  # "block" | "allow"
        },
        "modes": {},
    }


def load_config() -> Config:
    """Load and normalise config.toml, filling in defaults for any missing keys.

    Always returns a fully-populated Config so callers never need to guard
    against missing fields introduced in newer versions.
    """
    if not CONFIG_FILE.exists():
        return default_config()
    data = toml.load(CONFIG_FILE)
    config = default_config()
    config["always"]["whitelist"] = data.get("always", {}).get("whitelist", [])
    config["settings"].update(data.get("settings", {}))
    for name, mc in data.get("modes", {}).items():
        config["modes"][name] = {
            "strict": mc.get("strict", False),
            "whitelist": mc.get("whitelist", []),
            "blacklist": mc.get("blacklist", []),
        }
    return config


def save_config(config: Config) -> None:
    """Persist config to CONFIG_FILE, creating the config directory if needed."""
    ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        toml.dump(config, f)


def load_state() -> State:
    """Load runtime state from STATE_FILE, returning an empty State if absent."""
    if not STATE_FILE.exists():
        return State()
    data = toml.load(STATE_FILE)
    return State(active_mode=data.get("active_mode", ""))


def save_state(state: State) -> None:
    """Persist runtime state to STATE_FILE, creating the config directory if needed."""
    ensure_dir()
    with open(STATE_FILE, "w") as f:
        toml.dump(asdict(state), f)
