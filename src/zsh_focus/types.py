"""Data types for zsh-focus."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict


class ModeConfig(TypedDict):
    """Per-mode path rules stored under config['modes'][name]."""

    strict: bool
    """When True, unlisted directories prompt instead of being silently allowed."""
    whitelist: list[str]
    """Directories explicitly allowed for this mode (raw strings, may contain ~)."""
    blacklist: list[str]
    """Directories explicitly blocked for this mode (raw strings, may contain ~)."""


class AlwaysConfig(TypedDict):
    """Paths whitelisted regardless of which mode is active."""

    whitelist: list[str]
    """Directories allowed in every mode (raw strings, may contain ~)."""


class Settings(TypedDict):
    """Global behaviour settings stored under config['settings']."""

    block_notification: bool
    """Whether to show a notification when a cd is blocked."""
    non_interactive_behavior: Literal["block", "allow"]
    """What to do in non-interactive shells where prompting isn't possible."""


class Config(TypedDict):
    """Complete in-memory representation of config.toml."""

    always: AlwaysConfig
    settings: Settings
    modes: dict[str, ModeConfig]


@dataclass
class State:
    """Runtime state persisted to state.toml between shell sessions."""

    active_mode: str = ""
    """Name of the currently active focus mode, or '' when focus is off."""


Source = Literal["always whitelist", "mode whitelist", "mode blacklist"]
"""Which list a MatchedEntry was drawn from."""


@dataclass
class MatchedEntry:
    """A single list entry that prefix-matched the evaluated path."""

    entry: Path
    source: Source
    is_winner: bool = False
    """True for the single entry whose verdict was decisive (longest match)."""


@dataclass
class CheckResult:
    """Result of evaluating a path against the active focus mode."""

    target: Path
    """The path that was evaluated."""
    active_mode: str
    """Name of the mode that was active, or '' if no mode was active."""
    strict: bool
    """Whether the active mode was in strict mode at evaluation time."""
    matched: list[MatchedEntry]
    """All list entries that prefix-matched target, sorted most-specific first."""
    verdict: Literal["allow", "block", "prompt"]
    """Decision for the path. 'prompt' only arises in strict mode with no matching entry."""
