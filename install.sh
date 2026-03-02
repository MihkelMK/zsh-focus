#!/usr/bin/env bash
set -e

PLUGIN_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/zsh-focus"
BIN_DIR="${HOME}/.local/bin"

echo "Installing zsh-focus..."

# Copy plugin files
mkdir -p "$PLUGIN_DIR"
cp focus.plugin.zsh "$PLUGIN_DIR/"
cp bin/focus "$PLUGIN_DIR/"
cp requirements.txt "$PLUGIN_DIR/"

# Install Python deps
pip install --user -q click toml

# Symlink the CLI
mkdir -p "$BIN_DIR"
ln -sf "$PLUGIN_DIR/focus" "$BIN_DIR/focus"

echo ""
echo "Done! Add these lines to your .zshrc (order matters):"
echo ""
echo "  # 1. zoxide first"
echo "  eval \"\$(zoxide init zsh)\""
echo ""
echo "  # 2. then zsh-focus"
echo "  source \"$PLUGIN_DIR/focus.plugin.zsh\""
echo ""
echo "Make sure $BIN_DIR is in your PATH."
