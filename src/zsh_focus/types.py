"""Data types for zsh-focus."""

from dataclasses import dataclass
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
