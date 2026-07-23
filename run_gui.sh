#!/bin/bash
# GUI Launcher for EBL Simulation
#
# Usage: ./run_gui.sh [--env NAME]
#   --env NAME   activate a specific conda env (default: ebl-sim, then ebeam)

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

ENV_NAME=""
if [ "${1:-}" = "--env" ] && [ -n "${2:-}" ]; then
    ENV_NAME="$2"
fi

echo "Starting EBL Simulation GUI..."

# --- Python environment ---------------------------------------------------
activate_conda() {
    local base
    base="$(conda info --base 2>/dev/null)" || return 1
    # shellcheck disable=SC1091
    source "$base/etc/profile.d/conda.sh" || return 1
    if [ -n "$ENV_NAME" ]; then
        conda activate "$ENV_NAME" && return 0
        echo "Warning: conda env '$ENV_NAME' not found."
        return 1
    fi
    conda activate ebl-sim 2>/dev/null && return 0
    conda activate ebeam 2>/dev/null && return 0
    echo "Note: conda envs 'ebl-sim'/'ebeam' not found, using current environment."
    echo "      Create one with: conda env create -f environment.yml"
    return 0
}

if ! command -v conda >/dev/null 2>&1; then
    # Try well-known install locations before giving up on conda
    for base in "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3"; do
        if [ -x "$base/bin/conda" ]; then
            # shellcheck disable=SC1091
            source "$base/etc/profile.d/conda.sh"
            break
        fi
    done
fi

if command -v conda >/dev/null 2>&1; then
    activate_conda
elif [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/venv/bin/activate"
else
    echo "Note: no conda or venv found - using system python."
fi

if ! python -c "import PySide6" 2>/dev/null; then
    echo "Error: PySide6 not available in this Python environment."
    echo "  Create the GUI environment first:  conda env create -f environment.yml"
    echo "  Then run:                          ./run_gui.sh"
    exit 1
fi

# Fix PySide6 plugin path (needed after Qt updates)
PYSIDE_PATH=$(python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))" 2>/dev/null)
if [ -n "$PYSIDE_PATH" ]; then
    export QT_PLUGIN_PATH="$PYSIDE_PATH/Qt/plugins"
fi

# --- Display (WSL2 / Linux) ----------------------------------------------
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    # WSLg or a Wayland session: let Qt pick the platform itself
    :
else
    # X11 path: default DISPLAY for WSL2 if unset
    export DISPLAY="${DISPLAY:-:0}"
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
    if command -v xset >/dev/null 2>&1 && ! xset q &>/dev/null; then
        echo "Warning: X11 display '$DISPLAY' not reachable."
        echo "  On WSL2 with WSLg (Windows 11) this usually still works - trying anyway."
        echo "  Otherwise start an X server (e.g. VcXsrv) and set DISPLAY."
    fi
fi

echo "Launching EBL GUI..."
exec python scripts/gui/ebl_gui.py
