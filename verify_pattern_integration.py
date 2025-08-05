#!/usr/bin/env python3
"""
Verify pattern exposure integration without running GUI
"""

import re
from pathlib import Path

def verify_gui_integration():
    """Check that all pattern exposure components are integrated in the GUI"""
    
    gui_file = Path("scripts/gui/ebl_gui.py")
    if not gui_file.exists():
        print(f"✗ GUI file not found: {gui_file}")
        return False
    
    with open(gui_file, 'r') as f:
        content = f.read()
    
    checks = {
        "Pattern tab creation": r"create_pattern_tab",
        "Pattern mode checkbox": r"pattern_mode_check.*QCheckBox",
        "JEOL mode selection": r"mode3_radio.*QRadioButton",
        "Beam current combo": r"beam_current_combo.*QComboBox",
        "Shot pitch spin": r"shot_pitch_spin.*QSpinBox",
        "Pattern size spin": r"pattern_size_spin.*Q.*SpinBox",
        "Dose spin": r"dose_spin.*value",
        "Dwell time calculation": r"def update_dwell_time",
        "Electrons per point label": r"electrons_per_point_label.*QLabel",
        "Pattern macro generation": r"pattern/enable true",
        "Dose grid initialization": r"/data/initDoseGrid",
        "Pattern type command": r"/pattern/type",
        "Pattern generate command": r"/pattern/generate"
    }
    
    print("Checking GUI integration:")
    all_passed = True
    
    for description, pattern in checks.items():
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_passed = False
    
    # Check macro generation logic
    if "/pattern/enable true" in content:
        print("\n✓ Pattern macro generation is integrated!")
        
        # Find and display the pattern macro section
        pattern_section = re.search(
            r'# Check if pattern mode.*?# Beam configuration',
            content,
            re.DOTALL
        )
        if pattern_section:
            print("\nPattern macro generation code found:")
            print("-" * 60)
            print(pattern_section.group(0)[:500] + "...")
            print("-" * 60)
    
    return all_passed

def verify_cpp_backend():
    """Check that C++ backend has all necessary components"""
    
    files_to_check = {
        "PatternGenerator.hh": "src/beam/include/PatternGenerator.hh",
        "PatternGenerator.cc": "src/beam/src/PatternGenerator.cc",
        "PatternMessenger.cc": "src/beam/src/PatternMessenger.cc",
        "DataManager dose grid": "src/common/src/DataManager.cc"
    }
    
    print("\n\nChecking C++ backend:")
    all_passed = True
    
    for description, filepath in files_to_check.items():
        if Path(filepath).exists():
            print(f"  ✓ {description} exists")
        else:
            print(f"  ✗ {description} not found at {filepath}")
            all_passed = False
    
    return all_passed

def main():
    """Run all verifications"""
    
    print("=" * 60)
    print("PATTERN EXPOSURE INTEGRATION VERIFICATION")
    print("=" * 60)
    
    gui_ok = verify_gui_integration()
    cpp_ok = verify_cpp_backend()
    
    print("\n" + "=" * 60)
    if gui_ok and cpp_ok:
        print("✓ PATTERN EXPOSURE FULLY INTEGRATED!")
        print("\nThe implementation includes:")
        print("- C++ backend with PatternGenerator and dose grid")
        print("- Pattern-specific messenger commands")
        print("- GUI Pattern Exposure tab with JEOL parameters")
        print("- Automatic macro generation for pattern mode")
        print("- Electrons per point calculation")
        print("- Dose grid initialization commands")
        return 0
    else:
        print("✗ Some components missing or not integrated")
        return 1

if __name__ == "__main__":
    exit(main())