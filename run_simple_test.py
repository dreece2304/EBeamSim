#!/usr/bin/env python3
"""
run_simple_test.py - Direct test of pattern simulation
"""

import subprocess
import os
import time
from pathlib import Path

def run_simulation():
    """Run a simple pattern simulation test"""
    
    # Find the executable
    exe_name = "ebl_sim.exe" if os.name == 'nt' else "ebl_sim"
    exe_paths = [
        Path("cmake-build-release/bin") / exe_name,
        Path("cmake-build-release") / exe_name,
        Path("build/bin") / exe_name,
        Path("build") / exe_name,
    ]
    
    exe_path = None
    for path in exe_paths:
        if path.exists():
            exe_path = path
            break
    
    if not exe_path:
        print("ERROR: Cannot find ebl_sim executable!")
        print("Searched in:", exe_paths)
        return
    
    print(f"Found executable: {exe_path}")
    
    # Run the simulation
    macro_path = "simple_pattern_test.mac"
    if not Path(macro_path).exists():
        print(f"ERROR: {macro_path} not found!")
        return
    
    print(f"\nRunning: {exe_path} {macro_path}")
    print("=" * 60)
    print("This should show event progress...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Run with real-time output
        process = subprocess.Popen(
            [str(exe_path), macro_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output as it comes
        event_count = 0
        for line in process.stdout:
            print(line.rstrip())
            
            # Count events
            if "Event" in line and "started" in line:
                event_count += 1
                if event_count % 10 == 0:
                    print(f">>> Processed {event_count} events...")
        
        process.wait()
        
    except Exception as e:
        print(f"ERROR running simulation: {e}")
        return
    
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Simulation finished in {elapsed:.1f} seconds")
    print(f"Events processed: {event_count}")
    
    # Check for output
    output_files = list(Path(".").glob("test_pattern*.csv"))
    if output_files:
        print(f"\nOutput files created:")
        for f in output_files:
            print(f"  {f} ({f.stat().st_size} bytes)")
    else:
        print("\nWARNING: No output files found!")
    
    # Check for PSF data
    if Path("output/test_pattern.csv").exists():
        print("\nChecking PSF data...")
        with open("output/test_pattern.csv", 'r') as f:
            lines = f.readlines()
            print(f"  PSF file has {len(lines)} lines")
            if len(lines) > 5:
                print("  First few lines:")
                for line in lines[:5]:
                    print(f"    {line.rstrip()}")

if __name__ == "__main__":
    run_simulation()