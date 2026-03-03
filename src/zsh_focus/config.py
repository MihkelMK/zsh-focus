"""Paths, config, and state helpers."""

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict

import toml

# ── Paths ─────────────────────────────────────────────────────────────────────

CONFIG_DIR: Path = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zsh-focus"
)
CONFIG_FILE: Path = CONFIG_DIR / "config.toml"
STATE_FILE: Path = CONFIG_DIR / "state.toml"
COMPILED: Path = CONFIG_DIR / "compiled.zsh"

PLUGIN_FILE: str = "data/zsh_plugin.zsh"


# ── Types ─────────────────────────────────────────────────────────────────────


class ModeConfig(TypedDict):
    strict: bool
    whitelist: list[str]
    blacklist: list[str]


class AlwaysConfig(TypedDict):
    whitelist: list[str]


class Settings(TypedDict):
    block_notification: bool
    non_interactive_behavior: str


class Config(TypedDict):
    always: AlwaysConfig
    settings: Settings
    modes: dict[str, ModeConfig]


@dataclass
class State:
    active_mode: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────


def ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def default_config() -> Config:
    return {
        "always": {"whitelist": []},
        "settings": {
            "block_notification": True,
            "non_interactive_behavior": "block",  # "block" | "allow"
        },
        "modes": {},
    }


def load_config() -> Config:
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
    ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        toml.dump(config, f)


def load_state() -> State:
    if not STATE_FILE.exists():
        return State()
    data = toml.load(STATE_FILE)
    return State(active_mode=data.get("active_mode", ""))


def save_state(state: State) -> None:
    ensure_dir()
    with open(STATE_FILE, "w") as f:
        toml.dump(asdict(state), f)


def expand(p: str | Path) -> Path:
    """Expand ~ and resolve to absolute path."""
    return Path(p).expanduser().resolve()
