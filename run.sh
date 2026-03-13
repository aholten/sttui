#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Detect OS for correct venv paths
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) BIN_DIR="$VENV_DIR/Scripts" ;;
    *)                     BIN_DIR="$VENV_DIR/bin" ;;
esac

if [ ! -d "$VENV_DIR" ]; then
    echo "No virtual environment detected."
    read -rp "Run install.sh to set up? [Y/n] " confirm
    if [[ "$confirm" == [nN] ]]; then
        echo "Aborted. Run ./install.sh manually to set up."
        exit 1
    fi
    bash "$SCRIPT_DIR/install.sh"
fi

exec "$BIN_DIR/python" "$SCRIPT_DIR/speech_to_text.py" "$@"
