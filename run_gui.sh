#!/bin/bash
# GUI Launcher for EBL Simulation

echo "🖥️  Starting EBL Simulation GUI..."

# Setup display
export DISPLAY=:0
export QT_QPA_PLATFORM=xcb

# Fix PySide6 plugin path (needed after Qt updates)
PYSIDE_PATH=$(python -c "import PySide6; import os; print(os.path.dirname(PySide6.__file__))" 2>/dev/null)
if [ -n "$PYSIDE_PATH" ]; then
    export QT_PLUGIN_PATH="$PYSIDE_PATH/Qt/plugins"
fi

# Check if display is available
if ! xset q &>/dev/null; then
    echo "❌ X11 display not available. Please ensure X11 forwarding is enabled."
    exit 1
fi

# Activate Python environment
if [ -d "/home/dreece23/miniforge3" ]; then
    source /home/dreece23/miniforge3/bin/activate
    conda activate ebeam 2>/dev/null || conda activate ebl-sim 2>/dev/null || echo "Using base environment"
elif [ -d "/home/dreece23/miniconda3" ]; then
    source /home/dreece23/miniconda3/bin/activate
    conda activate ebl-sim
else
    source venv/bin/activate
fi

# Launch GUI
cd "$(dirname "$0")"

echo "🚀 Launching EBL GUI..."
python scripts/gui/ebl_gui.py
