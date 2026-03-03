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
    strict: bool = False,
    active: bool = True,
) -> tuple[Config, State]:
    config: Config = {
        "always": {"whitelist": list(always_wl)},
        "settings": {"block_notification": True, "non_interactive_behavior": "block"},
        "modes": {
            "test": {
                "strict": strict,
                "whitelist": list(mode_wl),
                "blacklist": list(mode_bl),
            }
        },
    }
    state = State(active_mode="test" if active else "")
    return config, state


# ── Strict / lenient for unlisted dirs ───────────────────────────────────────


def test_unlisted_strict_prompts():
    """Dirs not on any list in strict mode should prompt, not silently allow."""
    config, state = make(strict=True)
    assert check_path(config, state, Path(OTHER)).verdict == "prompt"


def test_unlisted_lenient_allows():
    """Dirs not on any list in lenient mode pass through silently — the default."""
    config, state = make(strict=False)
    assert check_path(config, state, Path(OTHER)).verdict == "allow"


def test_strict_mode_respects_always_whitelist():
    """Always whitelist should still allow in strict mode — not fall through to the prompt gate."""
    config, state = make(always_wl=(W,), strict=True)
    assert check_path(config, state, Path(WS)).verdict == "allow"


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
    """The deciding entry should have is_winner=True so 'path why' can identify it."""
    config, state = make(always_wl=(W,), mode_bl=(WS,))
    result = check_path(config, state, Path(WSS))
    winners = [m for m in result.matched if m.is_winner]
    assert len(winners) == 1
    assert winners[0].source == "mode blacklist"
    assert str(winners[0].entry) == WS


def test_matched_sorted_most_specific_first():
    """matched is sorted most-specific-first so 'path why' shows the winner at the top."""
    config, state = make(always_wl=(W,), mode_wl=(WS,))
    result = check_path(config, state, Path(WSS))
    assert str(result.matched[0].entry) == WS  # longer → first
    assert str(result.matched[1].entry) == W


def test_unmatched_entry_not_in_matched():
    """Entries that don't prefix-match the target should not appear in matched at all."""
    config, state = make(always_wl=(W,), mode_bl=(OTHER,))
    result = check_path(config, state, Path(W))
    assert all(m.source != "mode blacklist" for m in result.matched)
