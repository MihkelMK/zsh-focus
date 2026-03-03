"""Data types for zsh-focus."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict


class ModeConfig(TypedDict):
    strict: bool
    whitelist: list[str]
    blacklist: list[str]


class AlwaysConfig(TypedDict):
    whitelist: list[str]


class Settings(TypedDict):
    block_notification: bool
    non_interactive_behavior: Literal["block", "allow"]


class Config(TypedDict):
    always: AlwaysConfig
    settings: Settings
    modes: dict[str, ModeConfig]


@dataclass
class State:
    active_mode: str = ""


Source = Literal["always whitelist", "mode whitelist", "mode blacklist"]
"""Which list a MatchedEntry was drawn from."""


@dataclass
class MatchedEntry:
    entry: Path
    source: Source
    is_winner: bool = False


@dataclass
class CheckResult:
    target: Path
    active_mode: str
    strict: bool
    matched: list[MatchedEntry]
    verdict: Literal["allow", "block", "prompt"]
