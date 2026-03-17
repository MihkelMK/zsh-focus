"""Tests for check_path() — the core path decision engine."""

from pathlib import Path

from zsh_focus.engine import check_path
from zsh_focus.types import Config, State

# ── Helpers ───────────────────────────────────────────────────────────────────

W = "/focus"  # shallow root
WS = "/focus/sub"  # one level deeper
WSS = "/focus/sub/deep"  # deepest
OTHER = "/other"  # unrelated path


def make(
    always_wl: tuple[str, ...] = (),
    mode_wl: tuple[str, ...] = (),
    mode_bl: tuple[str, ...] = (),
    mode_warn: tuple[str, ...] = (),
    active: bool = True,
) -> tuple[Config, State]:
    config: Config = {
        "always": {"whitelist": list(always_wl)},
        "settings": {"block_notification": True, "non_interactive_behavior": "block"},
        "modes": {
            "test": {
                "whitelist": list(mode_wl),
                "blacklist": list(mode_bl),
                "warnlist": list(mode_warn),
            }
        },
    }
    state = State(active_mode="test" if active else "")
    return config, state


# ── Default behaviour for unlisted dirs ───────────────────────────────────────


def test_unlisted_allows():
    """Dirs not on any list should pass through silently."""
    config, state = make()
    assert check_path(config, state, Path(OTHER)).verdict == "allow"


# ── Warnlist ──────────────────────────────────────────────────────────────────


def test_warnlist_prompts():
    """A directory on the warnlist should yield 'prompt', not silently allow."""
    config, state = make(mode_warn=(W,))
    assert check_path(config, state, Path(W)).verdict == "prompt"


def test_warnlist_covers_subdirectories():
    """Warnlisting a parent should prompt for its subdirectories too."""
    config, state = make(mode_warn=(W,))
    assert check_path(config, state, Path(WS)).verdict == "prompt"


def test_deeper_whitelist_beats_warnlist():
    """A more-specific whitelist entry should override a shallower warnlist entry."""
    config, state = make(mode_wl=(WS,), mode_warn=(W,))
    assert check_path(config, state, Path(WS)).verdict == "allow"


def test_deeper_warnlist_beats_whitelist():
    """A more-specific warnlist entry should override a shallower whitelist entry."""
    config, state = make(mode_wl=(W,), mode_warn=(WS,))
    assert check_path(config, state, Path(WS)).verdict == "prompt"


def test_deeper_blacklist_beats_warnlist():
    """A more-specific blacklist entry should override a shallower warnlist entry."""
    config, state = make(mode_warn=(W,), mode_bl=(WS,))
    assert check_path(config, state, Path(WS)).verdict == "block"


def test_tie_warn_beats_white():
    """Same-length entries on warnlist and whitelist: warnlist wins."""
    config, state = make(mode_wl=(W,), mode_warn=(W,))
    assert check_path(config, state, Path(W)).verdict == "prompt"


def test_tie_black_beats_warn():
    """Same-length entries on blacklist and warnlist: blacklist wins."""
    config, state = make(mode_warn=(W,), mode_bl=(W,))
    assert check_path(config, state, Path(W)).verdict == "block"


def test_strict_mode_emulation():
    """Warnlist '/' emulates strict mode: prompts everywhere except whitelisted dirs.

    This is the recommended pattern for users who want 'prompt on everything unlisted'.
    A whitelist entry more specific than '/' overrides the catch-all warn.
    """
    config, state = make(mode_warn=("/",), mode_wl=(W,))
    assert check_path(config, state, Path(W)).verdict == "allow"    # whitelisted
    assert check_path(config, state, Path(WS)).verdict == "allow"   # subdir of whitelisted
    assert check_path(config, state, Path(OTHER)).verdict == "prompt"  # not whitelisted


# ── Prefix matching ───────────────────────────────────────────────────────────


def test_whitelist_covers_subdirectories():
    """Whitelisting a parent implicitly allows all its subdirectories."""
    config, state = make(always_wl=(W,))
    assert check_path(config, state, Path(WS)).verdict == "allow"


def test_no_prefix_bleed():
    """/focus should not match /focus-other."""
    config, state = make(mode_bl=(W,))
    assert check_path(config, state, Path("/focus-other")).verdict == "allow"


def test_no_partial_segment_match():
    """/focus/sub should not match /focus/subdir."""
    config, state = make(mode_bl=(WS,))
    assert check_path(config, state, Path("/focus/subdir")).verdict == "allow"


# ── Longest match wins ────────────────────────────────────────────────────────


def test_deeper_blacklist_beats_shallower_whitelist():
    """Banning a subdir of a whitelisted parent should work."""
    config, state = make(always_wl=(W,), mode_bl=(WS,))
    assert check_path(config, state, Path(WS)).verdict == "block"


def test_deeper_whitelist_beats_shallower_blacklist():
    """Whitelisting a subdir of a banned parent should work."""
    config, state = make(mode_wl=(WS,), mode_bl=(W,))
    assert check_path(config, state, Path(WS)).verdict == "allow"


def test_deeper_always_whitelist_beats_shallower_mode_blacklist():
    """A more-specific always-whitelist entry should rescue a subdir from a mode ban."""
    config, state = make(always_wl=(WS,), mode_bl=(W,))
    assert check_path(config, state, Path(WS)).verdict == "allow"


def test_three_level_exception():
    """whitelist > blacklist > whitelist — deepest wins at each level."""
    config, state = make(always_wl=(W,), mode_bl=(WS,), mode_wl=(WSS,))
    assert check_path(config, state, Path(WSS)).verdict == "allow"


def test_tie_blacklist_wins():
    """Same-length entries on both lists: blacklist wins."""
    config, state = make(always_wl=(W,), mode_bl=(W,))
    assert check_path(config, state, Path(W)).verdict == "block"


# ── Result structure ──────────────────────────────────────────────────────────


def test_winner_is_marked():
    """The deciding entry should have is_winner=True so 'path explain' can identify it."""
    config, state = make(always_wl=(W,), mode_bl=(WS,))
    result = check_path(config, state, Path(WSS))
    winners = [m for m in result.matched if m.is_winner]
    assert len(winners) == 1
    assert winners[0].source == "mode blacklist"
    assert str(winners[0].entry) == WS


def test_matched_sorted_most_specific_first():
    """matched is sorted most-specific-first so 'path explain' shows the winner at the top."""
    config, state = make(always_wl=(W,), mode_wl=(WS,))
    result = check_path(config, state, Path(WSS))
    assert str(result.matched[0].entry) == WS  # longer → first
    assert str(result.matched[1].entry) == W


def test_unmatched_entry_not_in_matched():
    """Entries that don't prefix-match the target should not appear in matched at all."""
    config, state = make(always_wl=(W,), mode_bl=(OTHER,))
    result = check_path(config, state, Path(W))
    assert all(m.source != "mode blacklist" for m in result.matched)
