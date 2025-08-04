#!/usr/bin/env python3
"""
debug_pattern_simulation.py

Debug why pattern simulation finishes instantly
"""

import os
from pathlib import Path

def check_macro_file():
    """Check the generated macro file"""
    macro_path = Path("gui_generated.mac")
    
    if not macro_path.exists():
        print("ERROR: Macro file not found!")
        return
    
    print("Checking macro file content:")
    print("=" * 60)
    
    with open(macro_path, 'r') as f:
        content = f.read()
        print(content)
    
    print("=" * 60)
    print("\nChecking for critical commands:")
    
    # Check for pattern commands
    if "/pattern/generate" in content:
        print("✓ Pattern generation command found")
    else:
        print("✗ Pattern generation command MISSING!")
    
    if "/pattern/beamMode pattern" in content:
        print("✓ Pattern mode activation found")
    else:
        print("✗ Pattern mode activation MISSING!")
    
    if "/run/beamOn -1" in content:
        print("✓ Automatic event calculation found")
    elif "/run/beamOn" in content:
        print("⚠ Manual event number used (should be -1 for pattern mode)")
    else:
        print("✗ No beamOn command found!")
    
    if "/run/initialize" in content:
        print("✓ Initialize command found")
    else:
        print("✗ Initialize command MISSING!")
    
    # Check command order
    lines = content.split('\n')
    init_line = -1
    pattern_line = -1
    beamon_line = -1
    
    for i, line in enumerate(lines):
        if "/run/initialize" in line:
            init_line = i
        if "/pattern/generate" in line:
            pattern_line = i
        if "/run/beamOn" in line:
            beamon_line = i
    
    print(f"\nCommand order:")
    print(f"  /run/initialize at line {init_line}")
    print(f"  /pattern/generate at line {pattern_line}")
    print(f"  /run/beamOn at line {beamon_line}")
    
    if init_line > 0 and pattern_line > init_line and beamon_line > pattern_line:
        print("✓ Command order is correct")
    else:
        print("✗ Command order is WRONG!")
        print("  Should be: initialize → pattern generate → beamOn")

def check_output_files():
    """Check for output files"""
    output_dir = Path("output")
    
    print("\n\nChecking output directory:")
    print("=" * 60)
    
    if not output_dir.exists():
        print("Output directory doesn't exist yet")
        return
    
    files = list(output_dir.glob("*"))
    if files:
        print(f"Found {len(files)} files:")
        for f in files:
            size = f.stat().st_size
            print(f"  {f.name} ({size} bytes)")
    else:
        print("No output files found!")

def check_log_file():
    """Check for error in log files"""
    log_files = list(Path(".").glob("*.log")) + list(Path(".").glob("*_log.txt"))
    
    if log_files:
        print("\n\nChecking log files:")
        print("=" * 60)
        
        for log_file in log_files:
            print(f"\nLog file: {log_file}")
            with open(log_file, 'r') as f:
                content = f.read()
                
            # Look for errors
            if "ERROR" in content or "Exception" in content or "WWWW" in content:
                print("Found errors in log:")
                for line in content.split('\n'):
                    if any(x in line for x in ["ERROR", "Exception", "WWWW", "Command not found"]):
                        print(f"  {line}")

def main():
    print("Pattern Simulation Debug")
    print("=" * 60)
    
    check_macro_file()
    check_output_files()
    check_log_file()
    
    print("\n\nCommon Issues:")
    print("1. If simulation finishes instantly:")
    print("   - Check if executable path is correct")
    print("   - Look for 'Command not found' errors")
    print("   - Verify pattern was generated before beamOn")
    print("\n2. If no output files:")
    print("   - Check working directory is correct")
    print("   - Verify output commands are recognized")
    print("\n3. If pattern mode not working:")
    print("   - Ensure /run/initialize comes BEFORE pattern setup")
    print("   - Check that /run/beamOn -1 is used (not a number)")

if __name__ == "__main__":
    main()