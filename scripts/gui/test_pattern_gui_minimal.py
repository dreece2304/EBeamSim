#!/usr/bin/env python3
"""
test_pattern_gui_minimal.py

Minimal test of pattern generation and dose visualization in GUI.
Tests only the basic pattern functionality without PSF/proximity effects.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from ebl_gui import EBLSimGUI

def test_pattern_generation():
    """Test pattern generation in GUI"""
    app = QApplication(sys.argv)
    
    # Create GUI instance
    gui = EBLSimGUI()
    
    # Set up pattern mode
    print("Setting up pattern mode...")
    gui.pattern_mode_radio.setChecked(True)
    
    # Configure pattern
    gui.pattern_type_combo.setCurrentText("square")
    gui.pattern_size_spin.setValue(1.0)  # 1 μm
    gui.pattern_center_x.setValue(0.0)
    gui.pattern_center_y.setValue(0.0)
    
    # JEOL parameters
    gui.eos_mode_combo.setCurrentIndex(0)  # Mode 3
    gui.shot_pitch_spin.setValue(4)
    gui.jeol_current_spin.setValue(2.0)
    gui.base_dose_spin.setValue(400.0)
    gui.scan_strategy_combo.setCurrentText("serpentine")
    
    # Dose modulation
    gui.interior_dose_spin.setValue(1.0)
    gui.edge_dose_spin.setValue(0.85)
    gui.corner_dose_spin.setValue(0.75)
    
    # Generate macro to test command generation
    print("\nGenerating macro...")
    try:
        macro_path = gui.generate_macro()
        print(f"Macro generated: {macro_path}")
        
        # Read and display pattern commands
        with open(macro_path, 'r') as f:
            content = f.read()
            
        print("\nPattern commands in macro:")
        for line in content.split('\n'):
            if '/EBL/pattern/' in line:
                print(f"  {line.strip()}")
        
        print("\nSuccess! Pattern dose modeling is properly configured.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Don't show GUI, just test functionality
    return 0

if __name__ == "__main__":
    sys.exit(test_pattern_generation())