"""Paths, config, and state helpers."""

import os
from pathlib import Path

import toml

# ── Paths ─────────────────────────────────────────────────────────────────────

CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zsh-focus"
)
CONFIG_FILE = CONFIG_DIR / "config.toml"
STATE_FILE = CONFIG_DIR / "state.toml"
COMPILED = CONFIG_DIR / "compiled.zsh"

PLUGIN_FILE = "data/zsh_plugin.zsh"

# ── Helpers ───────────────────────────────────────────────────────────────────


def ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def default_config() -> dict:
    return {
        "global": {"whitelist": []},
        "settings": {
            "block_notification": True,
            "non_interactive_behavior": "block",  # "block" | "allow"
        },
        "modes": {},
    }


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return default_config()
    return toml.load(CONFIG_FILE)


def save_config(config: dict):
    ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        toml.dump(config, f)


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"active_mode": ""}
    return toml.load(STATE_FILE)


def save_state(state: dict):
    ensure_dir()
    with open(STATE_FILE, "w") as f:
        toml.dump(state, f)


def expand(p: str) -> str:
    """Expand ~ and resolve to absolute path."""
    return str(Path(p).expanduser().resolve())
