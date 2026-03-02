# zsh-focus: directory-aware focus mode plugin
# Source this file in your .zshrc AFTER zoxide's init

_FOCUS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zsh-focus"
_FOCUS_COMPILED="${_FOCUS_CONFIG_DIR}/compiled.zsh"
_focus_last_mtime=0

# ── Compiled config reload (runs on each prompt) ─────────────────────────────

_focus_reload_if_needed() {
    [[ ! -f "$_FOCUS_COMPILED" ]] && return
    local mtime
    # macOS: stat -f %m / Linux: stat -c %Y
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

# ── Core check ────────────────────────────────────────────────────────────────

# Returns 0 (allow) or 1 (block)
_focus_check_dir() {
    local target_dir="$1"

    # No active mode → transparent
    [[ -z "$ZSH_FOCUS_ACTIVE_MODE" ]] && return 0

    # Resolve to absolute path (zsh :A expands symlinks + ~)
    target_dir="${target_dir:A}"

    # Check global whitelist (prefix match → subdirs are implicitly allowed)
    local dir
    for dir in "${ZSH_FOCUS_GLOBAL_WHITELIST[@]}"; do
        [[ "$target_dir" == "$dir" || "$target_dir" == "$dir/"* ]] && return 0
    done

    # Check mode whitelist
    for dir in "${ZSH_FOCUS_MODE_WHITELIST[@]}"; do
        [[ "$target_dir" == "$dir" || "$target_dir" == "$dir/"* ]] && return 0
    done

    # Check mode blacklist
    for dir in "${ZSH_FOCUS_MODE_BLACKLIST[@]}"; do
        if [[ "$target_dir" == "$dir" || "$target_dir" == "$dir/"* ]]; then
            if [[ "$ZSH_FOCUS_BLOCK_NOTIFICATION" == "true" ]]; then
                print -P "%F{red}blocked by focus mode '${ZSH_FOCUS_ACTIVE_MODE}'%f" >&2
            fi
            return 1
        fi
    done

    # Not on any list — prompt if interactive, honour setting otherwise
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

    if [[ "${1:-}" == "-" ]]; then
        dest="${OLDPWD:-$HOME}"
    else
        local target="${1:-$HOME}"
        # Resolve without actually changing dir
        dest=$(builtin cd -- "$target" 2>/dev/null && pwd)
        if [[ $? -ne 0 ]]; then
            # Let builtin produce the proper error message
            builtin cd "$@"
            return $?
        fi
    fi

    _focus_check_dir "$dest" || return 1
    builtin cd "$@"
}

# ── zoxide wrappers ───────────────────────────────────────────────────────────
# NOTE: source this plugin AFTER zoxide's eval "$(zoxide init zsh)" so that
# __zoxide_z and __zoxide_zi are already defined.

function z() {
    # Preview where zoxide would send us before committing
    local dest
    dest=$(zoxide query -- "$@" 2>/dev/null)
    if [[ $? -ne 0 || -z "$dest" ]]; then
        # Fall back to zoxide's own error handling
        __zoxide_z "$@"
        return $?
    fi

    _focus_check_dir "$dest" || return 1
    __zoxide_z "$@"
}

# zi is interactive (fzf picker); intercept after the user selects by wrapping
# the underlying cd that __zoxide_zi eventually calls — which our cd() above
# already covers. So zi works automatically with no extra wrapping needed.
