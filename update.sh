#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Detect OS for correct venv paths
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) BIN_DIR="$VENV_DIR/Scripts" ;;
    *)                     BIN_DIR="$VENV_DIR/bin" ;;
esac

echo "sttui Updater"
echo "============="

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

# Pull latest code if in a git repo
if [ -d "$SCRIPT_DIR/.git" ]; then
    echo "Pulling latest changes..."
    git -C "$SCRIPT_DIR" pull
fi

# Ensure venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi

# Upgrade dependencies
echo "Updating dependencies..."
"$BIN_DIR/pip" install --upgrade -r "$SCRIPT_DIR/requirements.txt"

echo "Done. Run ./run.sh to start."
