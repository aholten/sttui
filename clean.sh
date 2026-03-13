#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "sttui Clean"
echo "==========="
echo ""
echo "This will remove:"
echo "  - Virtual environment ($VENV_DIR)"
echo "  - Python cache (__pycache__)"
echo "  - Transcription log (transcription_log.txt)"
echo ""
read -rp "Continue? [y/N] " confirm

if [[ "$confirm" != [yY] ]]; then
    echo "Aborted."
    exit 0
fi

if [ -d "$VENV_DIR" ]; then
    echo "Removing virtual environment..."
    rm -rf "$VENV_DIR"
fi

if [ -d "$SCRIPT_DIR/__pycache__" ]; then
    echo "Removing Python cache..."
    rm -rf "$SCRIPT_DIR/__pycache__"
fi

if [ -f "$SCRIPT_DIR/transcription_log.txt" ]; then
    echo "Removing transcription log..."
    rm -f "$SCRIPT_DIR/transcription_log.txt"
fi

echo "Done. Project files remain intact — re-run ./run.sh to reinstall."
