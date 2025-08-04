#!/usr/bin/env python3
"""Quick test of the cleanup script"""

import subprocess
import sys

# Run cleanup in dry-run mode
result = subprocess.run([sys.executable, "cleanup_project.py"], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

print(f"\nReturn code: {result.returncode}")