"""Focus CLI — all commands."""

import pkgutil
import sys
from pathlib import Path

import click
import cloup

from zsh_focus.config import (
    COMPILED,
    PLUGIN_FILE,
    expand,
    load_config,
    load_state,
    save_config,
    save_state,
)
from zsh_focus.engine import check_path, compile_zsh
from zsh_focus.types import CheckResult, State

# ── Helpers ───────────────────────────────────────────────────────────────────


def _here_marker(ep: Path, result: CheckResult) -> str:
    """Return a styled '◀ here' marker if ep matches the current path check result."""
    matched_set = {m.entry for m in result.matched}
    winner_set = {m.entry for m in result.matched if m.is_winner}
    if ep in winner_set:
        color = "green" if result.verdict == "allow" else "red"
        return click.style("  ◀ here", fg=color)
    if ep in matched_set:
        return click.style("  ◀ here (overridden)", dim=True)
    return ""


# ── CLI sections ──────────────────────────────────────────────────────────────


class Sect:
    SESSION = cloup.Section("Session")
    MODES = cloup.Section("Modes")
    PATHS = cloup.Section("Paths")
    SETUP = cloup.Section("Setup")


# ── CLI ───────────────────────────────────────────────────────────────────────


@cloup.group(show_subcommand_aliases=True)
def cli() -> None:
    """Focus mode manager — keep your shell sessions intentional."""
    pass


# ── Session ───────────────────────────────────────────────────────────────────


@cli.command(section=Sect.SESSION)
@cloup.argument("mode")
def on(mode: str) -> None:
    """Activate a focus mode."""
    config = load_config()
    if mode not in config["modes"]:
        click.echo(
            f"Error: mode '{mode}' doesn't exist. Create it with:\n"
            f"  focus new {mode}",
            err=True,
        )
        sys.exit(1)
    state = State(active_mode=mode)
    save_state(state)
    compile_zsh(config, state)
    click.echo(f"✓ Focus mode '{mode}' activated.")


@cli.command(section=Sect.SESSION)
def off() -> None:
    """Deactivate focus mode (transparent shell)."""
    config = load_config()
    state = State()
    save_state(state)
    compile_zsh(config, state)
    click.echo("✓ Focus mode deactivated.")


@cli.command(section=Sect.SESSION)
def status() -> None:
    """Show active mode and directory lists."""
    config = load_config()
    state = load_state()
    result = check_path(config, state, Path.cwd())

    if state.active_mode:
        mc = config["modes"].get(state.active_mode)
        strict_label = (
            click.style(" strict", fg="yellow") if mc and mc["strict"] else ""
        )
        click.echo(
            f"Active mode: {click.style(state.active_mode, bold=True)}{strict_label}"
        )
        if mc:
            for label, key in (
                ("  Whitelist", "whitelist"),
                ("  Blacklist", "blacklist"),
            ):
                entries = mc[key]
                if entries:
                    click.echo(f"{label}:")
                    for e in entries:
                        click.echo(f"    {e}{_here_marker(expand(e), result)}")
    else:
        click.echo("No active focus mode.")

    if config["always"]["whitelist"]:
        click.echo("Always whitelist:")
        for e in config["always"]["whitelist"]:
            click.echo(f"  {e}{_here_marker(expand(e), result)}")

    click.echo("\nSettings:")
    click.echo(
        f"  block_notification:       {config['settings']['block_notification']}"
    )
    click.echo(
        f"  non_interactive_behavior: {config['settings']['non_interactive_behavior']}"
    )


# ── Modes ─────────────────────────────────────────────────────────────────────


@cli.command(name="list", aliases=["ls"], section=Sect.MODES)
def list_modes() -> None:
    """List all focus modes."""
    config = load_config()
    state = load_state()

    if not config["modes"]:
        click.echo("No modes yet. Create one with: focus new <mode>")
        return

    for name, mc in config["modes"].items():
        marker = (
            click.style(" ◀ active", fg="green") if name == state.active_mode else ""
        )
        strict_label = click.style(" strict", fg="yellow") if mc["strict"] else ""
        click.echo(
            f"  {name}{marker}{strict_label}  (allow: {len(mc['whitelist'])}, deny: {len(mc['blacklist'])})"
        )


@cli.command(name="new", section=Sect.MODES)
@cloup.argument("mode")
@cloup.option(
    "--strict/--no-strict",
    default=False,
    help="Prompt on unlisted dirs (default: allow them).",
)
def new_mode(mode: str, strict: bool) -> None:
    """Create a new focus mode."""
    config = load_config()
    if mode in config["modes"]:
        click.echo(f"Mode '{mode}' already exists.")
        return
    config["modes"][mode] = {"strict": strict, "whitelist": [], "blacklist": []}
    save_config(config)
    click.echo(f"✓ Mode '{mode}' created{' (strict)' if strict else ''}.")


@cli.command(name="set", section=Sect.MODES)
@cloup.argument("mode")
@cloup.option(
    "--strict/--no-strict",
    required=True,
    help="Prompt on unlisted dirs, or allow them silently.",
)
def set_mode(mode: str, strict: bool) -> None:
    """Update settings for an existing mode."""
    config = load_config()
    if mode not in config["modes"]:
        click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
        sys.exit(1)
    config["modes"][mode]["strict"] = strict
    save_config(config)
    state = load_state()
    if state.active_mode == mode:
        compile_zsh(config, state)
    click.echo(f"✓ Mode '{mode}' is now {'strict' if strict else 'lenient'}.")


# ── Paths ─────────────────────────────────────────────────────────────────────


@cli.group(name="path", section=Sect.PATHS, show_subcommand_aliases=True)
def path_group() -> None:
    """Manage whitelisted and blacklisted paths.

    All subcommands accept an optional PATH argument (default: current directory).
    """
    pass


@path_group.command(name="allow", aliases=["a"])
@cloup.argument("path", default="")
@cloup.option(
    "-m", "--mode", default=None, help="Mode to add to (default: always whitelist)"
)
def allow(path: str, mode: str | None) -> None:
    """
    Whitelist a directory. Defaults to current directory.

    Without -m, adds to the always whitelist (all modes).
    With -m <mode>, adds to that mode's whitelist.
    """
    target: Path = expand(path) if path else Path.cwd()
    config = load_config()
    state = load_state()

    if mode is None:
        wl = config["always"]["whitelist"]
        if str(target) in wl:
            click.echo(f"'{target}' is already in the always whitelist.")
            return
        wl.append(str(target))
        save_config(config)
        compile_zsh(config, state)
        click.echo(f"✓ '{target}' → always whitelist")
    else:
        if mode not in config["modes"]:
            click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
            sys.exit(1)
        wl = config["modes"][mode]["whitelist"]
        if str(target) in wl:
            click.echo(f"'{target}' is already in '{mode}' whitelist.")
            return
        wl.append(str(target))
        save_config(config)
        compile_zsh(config, state)
        click.echo(f"✓ '{target}' → mode '{mode}' whitelist")


@path_group.command(name="ban", aliases=["b"])
@cloup.argument("path", default="")
@cloup.option("-m", "--mode", required=True, help="Mode to add the ban rule to")
def ban(path: str, mode: str) -> None:
    """
    Blacklist a directory. Defaults to current directory.

    Always requires -m <mode> (blacklists are per-mode, never global).
    """
    target: Path = expand(path) if path else Path.cwd()
    config = load_config()
    state = load_state()

    if mode not in config["modes"]:
        click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
        sys.exit(1)

    bl = config["modes"][mode]["blacklist"]
    if str(target) in bl:
        click.echo(f"'{target}' is already in '{mode}' blacklist.")
        return
    bl.append(str(target))
    save_config(config)
    compile_zsh(config, state)
    click.echo(f"✓ '{target}' → mode '{mode}' blacklist")


@path_group.command(name="clear", aliases=["c"])
@cloup.argument("path", default="")
@cloup.option(
    "-m", "--mode", default=None, help="Mode to remove from (default: always whitelist)"
)
def clear(path: str, mode: str | None) -> None:
    """
    Remove a whitelist or blacklist entry. Defaults to current directory.

    Without -m, removes from the always whitelist.
    With -m <mode>, removes from that mode's whitelist and/or blacklist.
    """
    target: Path = expand(path) if path else Path.cwd()
    config = load_config()
    state = load_state()
    removed = False

    if mode is None:
        wl = config["always"]["whitelist"]
        if str(target) in wl:
            wl.remove(str(target))
            removed = True
            click.echo(f"✓ Removed '{target}' from always whitelist.")
    else:
        if mode not in config["modes"]:
            click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
            sys.exit(1)
        mc = config["modes"][mode]
        for list_name, lst in (
            ("whitelist", mc["whitelist"]),
            ("blacklist", mc["blacklist"]),
        ):
            if str(target) in lst:
                lst.remove(str(target))
                removed = True
                click.echo(f"✓ Removed '{target}' from mode '{mode}' {list_name}.")

    if removed:
        save_config(config)
        compile_zsh(config, state)
    else:
        click.echo(f"'{target}' wasn't found in any list.")


@path_group.command(name="why", aliases=["w"])
@cloup.argument("path", default="")
def why(path: str) -> None:
    """Explain the allow/block decision for a directory (default: current directory)."""
    target = expand(path) if path else Path.cwd()
    config = load_config()
    state = load_state()
    result = check_path(config, state, target)

    click.echo(f"Path:  {result.target}")

    if not result.active_mode:
        click.echo("Mode:  (none active)")
        click.echo(
            f"Result: {click.style('✓ allowed', fg='green')} — no focus mode active"
        )
        return

    strict_label = click.style(" strict", fg="yellow") if result.strict else ""
    click.echo(f"Mode:  {click.style(result.active_mode, bold=True)}{strict_label}")

    if result.matched:
        click.echo("Rules:")
        for m in result.matched:
            source_color = "red" if "blacklist" in m.source else "green"
            source_str = click.style(m.source, fg=source_color)
            if m.is_winner:
                winner_str = click.style(
                    " ← winner",
                    fg="green" if result.verdict == "allow" else "red",
                )
            else:
                winner_str = click.style(" (overridden)", dim=True)
            click.echo(f"  {m.entry}  [{source_str}]{winner_str}")
    else:
        click.echo("Rules:  (no list entries matched)")

    if result.verdict == "allow":
        click.echo(f"Result: {click.style('✓ allowed', fg='green')}")
    elif result.verdict == "block":
        click.echo(f"Result: {click.style('✗ blocked', fg='red')}")
    else:
        click.echo(f"Result: {click.style('? will prompt', fg='yellow')}")


# ── Setup ─────────────────────────────────────────────────────────────────────


@cli.command(name="compile", section=Sect.SETUP)
def compile_cmd() -> None:
    """Recompile the shell variable cache from current config and state.

    Runs automatically on the next prompt after editing config.toml directly.
    Use this to force an immediate recompile.
    """
    compile_zsh(load_config(), load_state())


@cli.command(name="init", section=Sect.SETUP)
@cloup.option(
    "--cmd",
    default=None,
    metavar="NAME",
    help="The command name passed to zoxide init (e.g. --cmd cd). "
    "Omit if you didn't pass --cmd to zoxide.",
)
def init_zsh(cmd: str | None) -> None:
    """Print zsh integration. Add to .zshrc: eval "$(focus init zsh)"

    If you initialise zoxide with a custom command name, mirror it here:

      eval "$(zoxide init zsh --cmd cd)"
      eval "$(focus init zsh --cmd cd)"
    """
    data = pkgutil.get_data("zsh_focus", PLUGIN_FILE)

    if not data:
        raise click.ClickException(
            f"Couldn't find packaged file {PLUGIN_FILE}. "
            "Contact the developer. This should not happen."
        )

    if not COMPILED.exists():
        compile_zsh(load_config(), load_state())

    zoxide_cmd = cmd if cmd else "z"
    click.echo(f'_FOCUS_ZOXIDE_CMD="{zoxide_cmd}"')
    click.echo(data.decode())
