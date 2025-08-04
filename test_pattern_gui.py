#!/usr/bin/env python3
"""
Test script to verify pattern exposure GUI macro generation
"""

import sys
import os
from pathlib import Path

# Add the GUI scripts directory to path
gui_path = Path(__file__).parent / "scripts" / "gui"
sys.path.insert(0, str(gui_path))

# Import the necessary classes
from PySide6.QtWidgets import QApplication
from ebl_gui import EBLGui

def test_pattern_macro_generation():
    """Test that pattern mode macro generation works correctly"""
    app = QApplication([])
    
    # Create GUI instance
    gui = EBLGui()
    
    # Enable pattern mode
    if hasattr(gui, 'pattern_mode_check'):
        gui.pattern_mode_check.setChecked(True)
        print("✓ Pattern mode checkbox found and enabled")
    else:
        print("✗ Pattern mode checkbox not found!")
        return False
    
    # Set pattern parameters
    gui.pattern_type_combo.setCurrentText("Square")
    gui.pattern_size_spin.setValue(1000)  # 1 µm square
    gui.shot_pitch_spin.setValue(4)  # 4 nm pitch
    gui.dose_spin.setValue(300)  # 300 µC/cm²
    gui.beam_current_combo.setCurrentText("2 nA")
    
    # Set working directory to temp
    gui.working_dir = "/tmp/ebl_test"
    Path(gui.working_dir).mkdir(exist_ok=True)
    
    # Generate macro
    macro_path = gui.generate_macro()
    
    if macro_path and Path(macro_path).exists():
        print(f"✓ Macro generated at: {macro_path}")
        
        # Read and check macro content
        with open(macro_path, 'r') as f:
            content = f.read()
            
        # Check for pattern-specific commands
        checks = [
            ("/pattern/enable true", "Pattern mode enabled"),
            ("/pattern/type square", "Pattern type set"),
            ("/pattern/jeolMode", "JEOL mode configured"),
            ("/pattern/shotPitch 4", "Shot pitch set"),
            ("/pattern/beamCurrent 2", "Beam current set"),
            ("/pattern/dose 300", "Dose set"),
            ("/pattern/generate", "Pattern generation command"),
            ("/data/initDoseGrid", "Dose grid initialized")
        ]
        
        print("\nChecking macro content:")
        all_passed = True
        for check_str, description in checks:
            if check_str in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - NOT FOUND")
                all_passed = False
        
        # Print macro content for debugging
        if not all_passed:
            print("\nGenerated macro content:")
            print("-" * 60)
            print(content)
            print("-" * 60)
        
        return all_passed
    else:
        print("✗ Failed to generate macro")
        return False

if __name__ == "__main__":
    success = test_pattern_macro_generation()
    sys.exit(0 if success else 1)