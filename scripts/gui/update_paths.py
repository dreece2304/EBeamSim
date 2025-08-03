#!/usr/bin/env python3
"""
Script to update paths in ebl_gui.py for new machine
Run this script in the same directory as ebl_gui.py
"""

import re
from pathlib import Path

def update_ebl_gui_paths():
    """Update paths in ebl_gui.py"""

    gui_file = Path("ebl_gui.py")

    if not gui_file.exists():
        print("Error: ebl_gui.py not found in current directory")
        return

    print("Updating ebl_gui.py paths...")

    # Read the file
    with open(gui_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Backup the original
    backup_file = gui_file.with_suffix('.py.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Backup created: {backup_file}")

    # Update the executable path and working directory in setup_defaults
    old_pattern = r'self\.executable_path = r"C:\\Users\\dreec\\Geant4Projects\\EBeamSim\\out\\build\\x64-release\\bin\\ebl_sim\.exe"\s*\n\s*self\.working_dir = r"C:\\Users\\dreec\\Geant4Projects\\EBeamSim\\out\\build\\x64-release\\bin"'

    new_code = '''# Navigate up from scripts/gui/ to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        
        # Updated build directory path for cmake-build-release
        build_dir = project_root / "cmake-build-release" / "bin"
        
        self.executable_path = str(build_dir / "ebl_sim.exe")
        self.working_dir = str(build_dir)'''

    content = re.sub(old_pattern, new_code, content)

    # Update the possible_paths list
    old_paths_pattern = r'possible_paths = \[\s*project_root / "out" / "build" / "x64-release" / "bin" / "ebl_sim\.exe",\s*project_root / "out" / "build" / "x64-debug" / "bin" / "ebl_sim\.exe",\s*project_root / "build" / "bin" / "Release" / "ebl_sim\.exe",\s*project_root / "build" / "bin" / "Debug" / "ebl_sim\.exe",\s*\]'

    new_paths_code = '''possible_paths = [
                project_root / "cmake-build-release" / "bin" / "ebl_sim.exe",
                project_root / "cmake-build-debug" / "bin" / "ebl_sim.exe",
                project_root / "build" / "bin" / "ebl_sim.exe",
                project_root / "out" / "build" / "x64-release" / "bin" / "ebl_sim.exe",
            ]'''

    content = re.sub(old_paths_pattern, new_paths_code, content, flags=re.MULTILINE | re.DOTALL)

    # Write the updated file
    with open(gui_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ ebl_gui.py updated successfully!")
    print("\nChanges made:")
    print("1. Updated executable path to use cmake-build-release directory")
    print("2. Updated fallback paths list")
    print("3. Geant4 path already correct")

    print(f"\n🔧 Manual verification recommended:")
    print(f"   Check that your executable exists at:")
    print(f"   {Path().resolve().parent.parent.parent / 'cmake-build-release' / 'bin' / 'ebl_sim.exe'}")

if __name__ == "__main__":
    update_ebl_gui_paths()