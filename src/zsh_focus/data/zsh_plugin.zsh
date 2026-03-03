# shellcheck shell=bash

# _FOCUS_ZOXIDE_CMD is set by `focus init zsh` — don't set it manually.
_FOCUS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zsh-focus"
_FOCUS_COMPILED="${_FOCUS_CONFIG_DIR}/compiled.zsh"
_focus_last_mtime=0

# ── Compiled config reload (runs on each prompt) ─────────────────────────────

_focus_reload_if_needed() {
    [[ ! -f "$_FOCUS_COMPILED" ]] && return
    local mtime
    # macOS: stat -f %m  /  Linux: stat -c %Y
    mtime=$(stat -f %m "$_FOCUS_COMPILED" 2>/dev/null || stat -c %Y "$_FOCUS_COMPILED" 2>/dev/null)
    if [[ "$mtime" != "$_focus_last_mtime" ]]; then
        source "$_FOCUS_COMPILED"
        _focus_last_mtime="$mtime"
    fi
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _focus_reload_if_needed

# Source immediately on first load too
[[ -f "$_FOCUS_COMPILED" ]] && source "$_FOCUS_COMPILED" && \
    _focus_last_mtime=$(stat -f %m "$_FOCUS_COMPILED" 2>/dev/null || stat -c %Y "$_FOCUS_COMPILED" 2>/dev/null)

# ── Save whatever 'cd' is right now, before we overwrite it ──────────────────
# If zoxide used --cmd cd, its function is already defined and gets captured here.
# If zoxide used the default (z/zi), functions[cd] is empty and we fall back to
# builtin cd at the end of our wrapper.
functions[_focus_orig_cd]=${functions[cd]:-}

# ── Resolve destination ───────────────────────────────────────────────────────

# Determines the real absolute path we'd end up in, without changing directory.
# 1. Tries literal path resolution via builtin cd.
# 2. If that fails AND zoxide is in play, asks `zoxide query` for its answer.
# Echoes the resolved path and returns 0 on success, returns 1 on failure.
_focus_resolve_dest() {
    local dest

    # Special case: cd -
    if [[ "${1:-}" == "-" ]]; then
        echo "${OLDPWD:-$HOME}"
        return 0
    fi

    local target="${1:-$HOME}"

    # Try as a literal path first (handles normal absolute/relative paths)
    dest=$(builtin cd -- "$target" 2>/dev/null && pwd)
    if [[ -n "$dest" ]]; then
        echo "$dest"
        return 0
    fi

    # Literal resolution failed — if zoxide is handling cd (--cmd cd) or the
    # caller might be using a fuzzy query, ask zoxide what it would resolve to.
    # _FOCUS_ZOXIDE_CMD is "z" for standard init, or e.g. "cd" for --cmd cd.
    if [[ -n "${_FOCUS_ZOXIDE_CMD:-}" ]]; then
        dest=$(zoxide query -- "$@" 2>/dev/null)
        if [[ -n "$dest" ]]; then
            echo "$dest"
            return 0
        fi
    fi

    return 1
}

# ── Core check ────────────────────────────────────────────────────────────────

# Returns 0 (allow) or 1 (block)
_focus_check_dir() {
    local target_dir="$1"

    # No active mode → transparent
    [[ -z "$ZSH_FOCUS_ACTIVE_MODE" ]] && return 0

    # Resolve to absolute path (:A expands ~ and symlinks)
    target_dir="${target_dir:A}"

    # Global whitelist — prefix match so subdirs are implicitly allowed
    local dir
    for dir in "${ZSH_FOCUS_GLOBAL_WHITELIST[@]}"; do
        [[ "$target_dir" == "$dir" || "$target_dir" == "$dir/"* ]] && return 0
    done

    # Mode whitelist
    for dir in "${ZSH_FOCUS_MODE_WHITELIST[@]}"; do
        [[ "$target_dir" == "$dir" || "$target_dir" == "$dir/"* ]] && return 0
    done

    # Mode blacklist
    for dir in "${ZSH_FOCUS_MODE_BLACKLIST[@]}"; do
        if [[ "$target_dir" == "$dir" || "$target_dir" == "$dir/"* ]]; then
            if [[ "$ZSH_FOCUS_BLOCK_NOTIFICATION" == "true" ]]; then
                print -P "%F{red}blocked by focus mode '${ZSH_FOCUS_ACTIVE_MODE}'%f" >&2
            fi
            return 1
        fi
    done

    # Not on any list — non-strict modes allow it silently
    [[ "$ZSH_FOCUS_STRICT" != "true" ]] && return 0

    # Strict mode — prompt if interactive, honour config setting otherwise
    if [[ -o interactive ]]; then
        local response
        print -n "Are you sure this isn't a distraction? (y/N) " >&2
        read -r response
        [[ "$response" =~ ^[Yy]$ ]] && return 0
        return 1
    else
        [[ "$ZSH_FOCUS_NON_INTERACTIVE" == "allow" ]] && return 0
        return 1
    fi
}

# ── cd wrapper ────────────────────────────────────────────────────────────────

function cd() {
    local dest
    dest=$(_focus_resolve_dest "$@")

    if [[ $? -ne 0 ]]; then
        # Resolution failed entirely — pass through for a proper error message
        if [[ -n "${functions[_focus_orig_cd]}" ]]; then
            _focus_orig_cd "$@"
        else
            builtin cd "$@"
        fi
        return $?
    fi

    _focus_check_dir "$dest" || return 1

    # Delegate to whatever cd was before we wrapped it
    if [[ -n "${functions[_focus_orig_cd]}" ]]; then
        _focus_orig_cd "$@"
    else
        builtin cd "$@"
    fi
}

# zsh-focus: directory-aware focus mode plugin
# eval "$(focus init zsh)" in your .zshrc, AFTER zoxide's init
#
# If zoxide was initialised with --cmd cd, mirror that here:
#   eval "$(zoxide init zsh --cmd cd)"
#   eval "$(focus init zsh --cmd cd)"
