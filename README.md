# zsh-focus

A zsh plugin that makes your shell aware of focus modes. When a mode is active, navigating into blacklisted directories is blocked, and unlisted directories prompt for confirmation.

## Installation

```bash
git clone https://github.com/you/zsh-focus
cd zsh-focus
./install.sh
```

Or manually:

```bash
pip install --user click toml
```

Then add to your `.zshrc` — **order matters**:

```zsh
# zoxide must come first
eval "$(zoxide init zsh)"

# then zsh-focus
source /path/to/zsh-focus/focus.plugin.zsh
```

And ensure `focus` is on your PATH:

```zsh
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

```
focus new <mode>            Create a new mode
focus on <mode>             Activate a mode
focus off                   Deactivate (transparent shell)
focus status                Show active mode and all lists
focus list                  List all modes

focus allow [path] [-m mode]   Whitelist a directory
                               No -m → global (applies to all modes)
                               -m mode → that mode's whitelist

focus deny [path] -m <mode>    Blacklist a directory (always per-mode)

focus remove [path] [-m mode]  Remove a whitelist/blacklist entry
```

All `path` arguments default to `$PWD` when omitted.

## Example workflow

```zsh
# Create a deep work mode
focus new deep-work

# Blacklist distracting directories
focus deny ~/social    -m deep-work
focus deny ~/games     -m deep-work
focus deny ~/youtube   -m deep-work

# Whitelist your work tree (all modes)
focus allow ~/work

# Whitelist something specific to this mode only
focus allow ~/work/projects -m deep-work

# Activate
focus on deep-work

# Now in another shell session — it's already active
cd ~/social   # ❌  blocked by focus mode 'deep-work'
z games       # ❌  blocked by focus mode 'deep-work'
cd ~/notes    # ❓  "Are you sure this isn't a distraction? (y/N)"
cd ~/work     # ✅  globally whitelisted, passes through
```

## Config file

Located at `~/.config/zsh-focus/config.toml`. You can edit it directly; changes take effect at the next shell prompt.

```toml
[global]
whitelist = ["~/work", "~/dotfiles"]

[settings]
block_notification = true          # show red message on block
non_interactive_behavior = "block" # "block" or "allow" for scripts/subshells

[modes.deep-work]
whitelist = ["~/work/projects"]
blacklist = ["~/social", "~/games"]

[modes.writing]
whitelist = ["~/writing"]
blacklist = ["~/work"]  # even work is a distraction
```

## How it works

- The plugin wraps `cd` and `z` as shell functions that intercept navigation before it happens.
- `zi` (zoxide interactive) is also intercepted — it eventually calls `cd`, which our wrapper catches.
- `focus` (the Python CLI) reads/writes the TOML config and compiles a `compiled.zsh` cache of plain shell variable assignments.
- A `precmd` hook checks the mtime of `compiled.zsh` on every prompt and re-sources it if changed. This means `focus on <mode>` takes effect at the very next prompt — no shell restart needed.
- The hot path (every `cd`) only reads shell variables, so there's no Python startup overhead.

## Path matching

Both exact paths and parent paths match. If `~/work` is whitelisted, then `~/work/projects/foo` is also allowed. Same logic applies to blacklists.
