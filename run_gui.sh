#!/bin/bash
# GUI Launcher for EBL Simulation

echo "🖥️  Starting EBL Simulation GUI..."

# Setup display
export DISPLAY=:0
export QT_QPA_PLATFORM=xcb

# Check if display is available
if ! xset q &>/dev/null; then
    echo "❌ X11 display not available. Please ensure X11 forwarding is enabled."
    exit 1
fi

# Activate Python environment
if [ -d "/home/dreece23/miniconda3" ]; then
    source /home/dreece23/miniconda3/bin/activate
    conda activate ebl-sim
else
    source venv/bin/activate
fi

# Launch GUI
cd "$(dirname "$0")"

# Check which GUI to launch
if [ -f "python/ebl_sim/gui/launcher.py" ]; then
    echo "🚀 Launching Professional GUI..."
    python python/ebl_sim/gui/launcher.py
elif [ -f "scripts/gui/ebl_gui.py" ]; then
    echo "🚀 Launching Legacy GUI..."
    python scripts/gui/ebl_gui.py
else
    echo "❌ No GUI found. Please check the installation."
    exit 1
fi
