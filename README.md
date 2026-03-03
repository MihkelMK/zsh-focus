# zsh-focus

A zsh plugin and Python CLI to block or restrict cd navigation. Keep yourshellf focused.

When a mode is active, navigating into blacklisted directories is blocked.\
Modes can optionally prompt on unlisted directories too (strict mode).

## Installation

1. Clone the repo

   ```bash
   git clone git@github.com:MihkelMK/zsh-focus.git
   ```

2. Install with pipx/pipxu

   ```bash
   pipx install zsh-focus
   ```

   Or using uv tool:

   ```bash
   uv tool install zsh-focus
   ```

3. Add to your `.zshrc` - **order matters with zoxide**:

   ```zsh
   # zoxide must come first
   eval "$(zoxide init zsh)"

   # then zsh-focus - mirror the same --cmd flag if you use one
   eval "$(zsh-focus init zsh)"
   ```

   If you use zoxide's `--cmd cd`:

   ```zsh
   eval "$(zoxide init zsh --cmd cd)"
   eval "$(zsh-focus init zsh --cmd cd)"
   ```

## Usage

```
zsh-focus on <mode>             Activate a mode
zsh-focus off                   Deactivate (transparent shell)
zsh-focus status                Show active mode and lists
zsh-focus list (ls)             List all modes

zsh-focus new <mode>            Create a new mode
zsh-focus set <mode>            Update mode settings
  --strict / --no-strict        Prompt on unlisted dirs, or allow silently

zsh-focus path (a)llow  [path] [-m mode]   Whitelist a directory
zsh-focus path (b)an    [path] -m <mode>   Blacklist a directory
zsh-focus path (c)lear  [path] [-m mode]   Remove a whitelist/blacklist entry
zsh-focus path (w)hy    [path]             Show why a directory is allowed or blocked
```

- `allow` and `clear` apply to _always-whitelist_ (all modes) without `-m`.
- `ban` requires `-m`. Blacklists are per-mode only.
- `why` defaults to the current directory.

### Strict vs lenient modes

Modes have two behaviours for directories that aren't on any list:

- **Lenient** (default): Just **ban** the things you know are _distracting_.\
  Unlisted dirs pass through silently.
- **Strict**: Every _allowed_ directory must be explicitly **whitelisted**.\
  Unlisted dirs prompt `Are you sure this isn't a distraction? (y/N)`.

```zsh
zsh-focus new deep-work --strict    # whitelist-required
zsh-focus new no-rabbit-holes       # blacklist-only (default)

zsh-focus set deep-work --no-strict # switch an existing mode
```

### Path matching

Both exact paths and parent paths match.\
Whitelisting `~/work` implicitly allows `~/work/projects/foo`. The same prefix logic applies to blacklists.

When a path matches entries on both lists, the **most specific rule wins**.\
Whichever matching entry has the deeper path takes priority, regardless of which list it's on.\
On a tie, the blacklist wins.

```
~/work            → whitelisted (always)
~/work/side-gigs  → banned      ← wins, more specific
```

```
~/private         → banned
~/private/safe    → whitelisted ← wins, more specific
```

This means you can carve exceptions in either direction without restructuring your lists.

### Inspecting decisions

`zsh-focus status` marks whichever list entry matches your current directory with `◀ here`, coloured green (allowed) or red (blocked).

`zsh-focus path why [path]` explains the decision. Which rules matched, which one won, and the verdict:

```
$ zsh-focus path why ~/work/side-gigs

Path:  /home/user/work/side-gigs
Mode:  deep-work  strict
Rules:
  /home/user/work/side-gigs  [mode blacklist]   ← winner
  /home/user/work             [always whitelist] (overridden)
Result: ✗ blocked
```

### Example workflows

#### Lenient mode - ban known distractions

Good for light focus. Create a mode, blacklist distracting directories, done.

```zsh
zsh-focus new no-rabbit-holes

# Ban the usual suspects
zsh-focus path ban ~/social     -m no-rabbit-holes
zsh-focus path ban ~/games      -m no-rabbit-holes
zsh-focus path ban ~/.config    -m no-rabbit-holes  # stop fiddling with configs

zsh-focus on no-rabbit-holes

cd ~/.config   # ❌  blocked by focus mode 'no-rabbit-holes'
cd ~/work      # ✅  not on any list, passes through silently
```

#### Strict mode - whitelist only what you need

It's time to lock in. Everything is suspect unless explicitly allowed.

```zsh
zsh-focus new deep-work --strict

# Allow work directories (for all modes)
zsh-focus path allow ~/work

# ban something specific only in this mode
zsh-focus path ban ~/work/side-gigs -m deep-work

# deepest nested rule wins
zsh-focus path allow ~/work/side-gigs/important -m deep-work

# Ban distractions
zsh-focus path ban ~/social  -m deep-work
zsh-focus path ban ~/games   -m deep-work

zsh-focus on deep-work

cd ~/social                     # ❌  blocked by focus mode 'deep-work'
cd ~/games                      # ❌  blocked by focus mode 'deep-work'
cd ~/notes                      # ❓  "Are you sure this isn't a distraction? (y/N)"
cd ~/work                       # ✅  always whitelisted, passes through
cd ~/work/side-gigs             # ❌  blocked by focus mode 'deep-work'
cd ~/work/side-gigs/important   # ✅  whitelisted for this mode
```

### Config file

Located at `~/.config/zsh-focus/config.toml`.\
You can edit it directly. Changes take effect at the next shell prompt.

```toml
[always]
whitelist = ["~/work", "~/dotfiles"]  # allowed in every mode

[settings]
block_notification = true           # show red message on block
non_interactive_behavior = "block"  # "block" or "allow" for scripts/subshells

[modes.deep-work]
strict = true
whitelist = ["~/work/projects"]
blacklist = ["~/social", "~/games"]

[modes.no-rabbit-holes]
strict = false
blacklist = ["~/social", "~/games", "~/.config"]
```

## How it works

- The plugin wraps `cd` at source time, capturing zoxide's wrapper if present.
- `zoxide`'s fuzzy queries (`z proj`, `zi`) are intercepted and resolved to the destination via `zoxide query`.
- `focus` (the Python CLI) reads/writes `config.toml` and compiles a `compiled.zsh` cache of plain shell variable assignments.
- A `precmd` hook checks the mtime of `compiled.zsh` on every prompt and re-sources it if changed.\
  `zsh-focus on <mode>` takes effect immediately. No shell restart needed.
- The hot path (every `cd`) only reads shell variables. No Python overhead.
