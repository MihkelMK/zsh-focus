"""Data types for zsh-focus."""

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


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


@dataclass
class MatchedEntry:
    entry: Path
    source: str  # "always whitelist" | "mode whitelist" | "mode blacklist"
    is_winner: bool = False


@dataclass
class CheckResult:
    target: Path
    active_mode: str
    strict: bool
    matched: list[MatchedEntry]
    verdict: str  # "allow" | "block" | "prompt"
