"""Focus CLI — all commands."""

import os
import pkgutil
import sys

import click
import cloup

from .compiler import compile_zsh
from .config import (
    COMPILED,
    PLUGIN_FILE,
    expand,
    load_config,
    load_state,
    save_config,
    save_state,
)

# ── CLI sections ──────────────────────────────────────────────────────────────


class Sect:
    SESSION = cloup.Section("Session")
    MODES = cloup.Section("Modes")
    PATHS = cloup.Section("Paths")
    SETUP = cloup.Section("Setup")


# ── CLI ───────────────────────────────────────────────────────────────────────


@cloup.group(show_subcommand_aliases=True)
def cli():
    """Focus mode manager — keep your shell sessions intentional."""
    pass


# ── Session ───────────────────────────────────────────────────────────────────


@cli.command(section=Sect.SESSION)
@cloup.argument("mode")
def on(mode):
    """Activate a focus mode."""
    config = load_config()
    if mode not in config.get("modes", {}):
        click.echo(
            f"Error: mode '{mode}' doesn't exist. Create it with:\n"
            f"  focus new {mode}",
            err=True,
        )
        sys.exit(1)
    state = {"active_mode": mode}
    save_state(state)
    compile_zsh(config, state)
    click.echo(f"✓ Focus mode '{mode}' activated.")


@cli.command(section=Sect.SESSION)
def off():
    """Deactivate focus mode (transparent shell)."""
    config = load_config()
    state = {"active_mode": ""}
    save_state(state)
    compile_zsh(config, state)
    click.echo("✓ Focus mode deactivated.")


@cli.command(section=Sect.SESSION)
def status():
    """Show active mode and directory lists."""
    config = load_config()
    state = load_state()
    active = state.get("active_mode", "")

    if active:
        click.echo(f"Active mode: {click.style(active, bold=True)}")
        mc = config.get("modes", {}).get(active, {})
        for label, key in (("  Whitelist", "whitelist"), ("  Blacklist", "blacklist")):
            entries = mc.get(key, [])
            if entries:
                click.echo(f"{label}:")
                for e in entries:
                    click.echo(f"    {e}")
    else:
        click.echo("No active focus mode.")

    global_wl = config.get("global", {}).get("whitelist", [])
    if global_wl:
        click.echo("Global whitelist:")
        for e in global_wl:
            click.echo(f"  {e}")

    settings = config.get("settings", {})
    click.echo("\nSettings:")
    click.echo(
        f"  block_notification:       {settings.get('block_notification', True)}"
    )
    click.echo(
        f"  non_interactive_behavior: {settings.get('non_interactive_behavior', 'block')}"
    )


# ── Modes ─────────────────────────────────────────────────────────────────────


@cli.command(name="list", aliases=["ls"], section=Sect.MODES)
def list_modes():
    """List all focus modes."""
    config = load_config()
    state = load_state()
    active = state.get("active_mode", "")
    modes = config.get("modes", {})

    if not modes:
        click.echo("No modes yet. Create one with: focus new <mode>")
        return

    for name, mc in modes.items():
        marker = click.style(" ◀ active", fg="green") if name == active else ""
        wl_count = len(mc.get("whitelist", []))
        bl_count = len(mc.get("blacklist", []))
        click.echo(f"  {name}{marker}  (allow: {wl_count}, deny: {bl_count})")


@cli.command(name="new", section=Sect.MODES)
@cloup.argument("mode")
def new_mode(mode):
    """Create a new focus mode."""
    config = load_config()
    config.setdefault("modes", {})
    if mode in config["modes"]:
        click.echo(f"Mode '{mode}' already exists.")
        return
    config["modes"][mode] = {"whitelist": [], "blacklist": []}
    save_config(config)
    click.echo(f"✓ Mode '{mode}' created.")


# ── Paths ─────────────────────────────────────────────────────────────────────


@cli.group(name="path", section=Sect.PATHS, show_subcommand_aliases=True)
def path_group():
    """Manage whitelisted and blacklisted paths.

    All subcommands accept an optional PATH argument (default: current directory).
    """
    pass


@path_group.command(name="allow", aliases=["a"])
@cloup.argument("path", default="")
@cloup.option(
    "-m", "--mode", default=None, help="Mode to add to (default: global whitelist)"
)
def allow(path, mode):
    """
    Whitelist a directory. Defaults to current directory.

    Without -m, adds to the global whitelist (all modes).
    With -m <mode>, adds to that mode's whitelist.
    """
    target = expand(path) if path else os.getcwd()
    config = load_config()
    state = load_state()

    if mode is None:
        wl = config.setdefault("global", {}).setdefault("whitelist", [])
        if target in wl:
            click.echo(f"'{target}' is already in the global whitelist.")
            return
        wl.append(target)
        save_config(config)
        compile_zsh(config, state)
        click.echo(f"✓ '{target}' → global whitelist")
    else:
        if mode not in config.get("modes", {}):
            click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
            sys.exit(1)
        wl = config["modes"][mode].setdefault("whitelist", [])
        if target in wl:
            click.echo(f"'{target}' is already in '{mode}' whitelist.")
            return
        wl.append(target)
        save_config(config)
        compile_zsh(config, state)
        click.echo(f"✓ '{target}' → mode '{mode}' whitelist")


@path_group.command(name="ban", aliases=["b"])
@cloup.argument("path", default="")
@cloup.option("-m", "--mode", required=True, help="Mode to add the ban rule to")
def ban(path, mode):
    """
    Blacklist a directory. Defaults to current directory.

    Always requires -m <mode> (blacklists are per-mode, never global).
    """
    target = expand(path) if path else os.getcwd()
    config = load_config()
    state = load_state()

    if mode not in config.get("modes", {}):
        click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
        sys.exit(1)

    bl = config["modes"][mode].setdefault("blacklist", [])
    if target in bl:
        click.echo(f"'{target}' is already in '{mode}' blacklist.")
        return
    bl.append(target)
    save_config(config)
    compile_zsh(config, state)
    click.echo(f"✓ '{target}' → mode '{mode}' blacklist")


@path_group.command(name="clear", aliases=["c"])
@cloup.argument("path", default="")
@cloup.option(
    "-m", "--mode", default=None, help="Mode to remove from (default: global)"
)
def clear(path, mode):
    """
    Remove a whitelist or blacklist entry. Defaults to current directory.

    Without -m, removes from the global whitelist.
    With -m <mode>, removes from that mode's whitelist and/or blacklist.
    """
    target = expand(path) if path else os.getcwd()
    config = load_config()
    state = load_state()
    removed = False

    if mode is None:
        wl = config.get("global", {}).get("whitelist", [])
        if target in wl:
            wl.remove(target)
            removed = True
            click.echo(f"✓ Removed '{target}' from global whitelist.")
    else:
        if mode not in config.get("modes", {}):
            click.echo(f"Error: mode '{mode}' doesn't exist.", err=True)
            sys.exit(1)
        mc = config["modes"][mode]
        for list_name in ("whitelist", "blacklist"):
            lst = mc.get(list_name, [])
            if target in lst:
                lst.remove(target)
                removed = True
                click.echo(f"✓ Removed '{target}' from mode '{mode}' {list_name}.")

    if removed:
        save_config(config)
        compile_zsh(config, state)
    else:
        click.echo(f"'{target}' wasn't found in any list.")


# ── Setup ─────────────────────────────────────────────────────────────────────


@cli.command(name="init", section=Sect.SETUP)
@cloup.option(
    "--cmd",
    default=None,
    metavar="NAME",
    help="The command name passed to zoxide init (e.g. --cmd cd). "
    "Omit if you didn't pass --cmd to zoxide.",
)
def init_zsh(cmd):
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

    # Ensure the compiled cache exists so the first source doesn't fail silently
    if not COMPILED.exists():
        config = load_config()
        state = load_state()
        compile_zsh(config, state)

    zoxide_cmd = cmd if cmd else "z"
    click.echo(f'_FOCUS_ZOXIDE_CMD="{zoxide_cmd}"')
    click.echo(data.decode())
