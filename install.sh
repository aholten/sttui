#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "sttui Installer"
echo "==============="
echo ""

# Detect python command
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python not found. Install Python 3.10+ and ensure 'python3' or 'python' is in your PATH."
    exit 1
fi

echo "Using Python: $($PYTHON --version) ($(command -v $PYTHON))"

# Detect OS for correct venv paths
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) BIN_DIR="$VENV_DIR/Scripts" ;;
    *)                     BIN_DIR="$VENV_DIR/bin" ;;
esac

# Create venv and install dependencies
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists. Updating dependencies..."
    "$BIN_DIR/pip" install --upgrade -r "$SCRIPT_DIR/requirements.txt"
else
    echo "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
    echo "Installing dependencies..."
    "$BIN_DIR/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

echo ""
echo "Installation complete!"
echo ""

# Detect shell rc file
RC_FILE=""
SHELL_NAME=""
if [ -n "$ZSH_VERSION" ] || [ "$(basename "$SHELL" 2>/dev/null)" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ] || [ "$(basename "$SHELL" 2>/dev/null)" = "bash" ]; then
    # On MINGW/Git Bash, .bashrc is typical
    RC_FILE="$HOME/.bashrc"
    SHELL_NAME="bash"
fi

ALIAS_LINE="alias sttui='\"$SCRIPT_DIR/run.sh\"'"

echo "To launch from anywhere, add the sttui alias to your shell:"
echo ""
if [ -n "$RC_FILE" ]; then
    echo "  echo '$ALIAS_LINE' >> $RC_FILE && source $RC_FILE"
else
    echo "  # Add this line to your shell's rc file (~/.bashrc, ~/.zshrc, etc.):"
    echo "  $ALIAS_LINE"
fi
echo ""
echo "Then just run:  sttui"
echo "You can use with options:   sttui --cli --model small"
echo ""
read -rp "Start sttui now? [y/N] " launch
if [[ "$launch" == [yY] ]]; then
    exec bash "$SCRIPT_DIR/run.sh"
fi
