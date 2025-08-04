#!/usr/bin/env python3
"""
test_dose_modeling.py

Test pattern dose modeling calculations without running full GUI.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def calculate_pattern_shots(pattern_size_um, shot_pitch, eos_mode=3):
    """Calculate shot positions for a square pattern"""
    # Convert to nm
    pattern_size = pattern_size_um * 1000
    
    # Machine grid
    machine_grid = 1.0 if eos_mode == 3 else 0.125  # nm
    exposure_grid = machine_grid * shot_pitch  # nm
    
    # Calculate number of shots
    n_shots_1d = int(pattern_size / exposure_grid)
    
    # Generate shot positions
    shots = []
    for i in range(n_shots_1d):
        for j in range(n_shots_1d):
            x = i * exposure_grid - pattern_size/2
            y = j * exposure_grid - pattern_size/2
            
            # Determine if edge or corner
            is_edge_x = (i == 0 or i == n_shots_1d - 1)
            is_edge_y = (j == 0 or j == n_shots_1d - 1)
            
            if is_edge_x and is_edge_y:
                rank = 2  # Corner
            elif is_edge_x or is_edge_y:
                rank = 1  # Edge
            else:
                rank = 0  # Interior
            
            shots.append({'x': x/1000, 'y': y/1000, 'rank': rank})  # Convert to μm
    
    return shots, exposure_grid

def visualize_dose_map(shots, dose_modulation, pattern_size_um):
    """Visualize the dose assignments"""
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Separate shots by rank
    interior = [(s['x'], s['y']) for s in shots if s['rank'] == 0]
    edge = [(s['x'], s['y']) for s in shots if s['rank'] == 1]
    corner = [(s['x'], s['y']) for s in shots if s['rank'] == 2]
    
    # Plot shots with color-coded doses
    if interior:
        ix, iy = zip(*interior)
        ax.scatter(ix, iy, c='blue', s=5, alpha=0.6, 
                  label=f'Interior ({dose_modulation[0]:.0%})')
    if edge:
        ex, ey = zip(*edge)
        ax.scatter(ex, ey, c='orange', s=10, alpha=0.8,
                  label=f'Edge ({dose_modulation[1]:.0%})')
    if corner:
        cx, cy = zip(*corner)
        ax.scatter(cx, cy, c='red', s=20, alpha=1.0,
                  label=f'Corner ({dose_modulation[2]:.0%})')
    
    # Draw pattern boundary
    half_size = pattern_size_um / 2
    rect = Rectangle((-half_size, -half_size), pattern_size_um, pattern_size_um,
                    fill=False, edgecolor='black', linewidth=2, linestyle='--')
    ax.add_patch(rect)
    
    ax.set_xlim(-pattern_size_um * 0.6, pattern_size_um * 0.6)
    ax.set_ylim(-pattern_size_um * 0.6, pattern_size_um * 0.6)
    ax.set_xlabel('X (μm)')
    ax.set_ylabel('Y (μm)')
    ax.set_title(f'Pattern Dose Map - {pattern_size_um}μm Square')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    plt.tight_layout()
    plt.savefig('test_dose_map.png', dpi=150)
    plt.show()
    
    # Print statistics
    n_interior = len(interior)
    n_edge = len(edge)
    n_corner = len(corner)
    n_total = n_interior + n_edge + n_corner
    
    print(f"\nShot Statistics:")
    print(f"Total shots: {n_total}")
    print(f"Interior: {n_interior} ({n_interior/n_total*100:.1f}%)")
    print(f"Edge: {n_edge} ({n_edge/n_total*100:.1f}%)")
    print(f"Corner: {n_corner} ({n_corner/n_total*100:.1f}%)")
    
    # Calculate average dose
    avg_dose = (n_interior * dose_modulation[0] + 
                n_edge * dose_modulation[1] + 
                n_corner * dose_modulation[2]) / n_total
    print(f"\nAverage dose factor: {avg_dose:.3f}")

def test_dose_calculation(base_dose, beam_current, shot_pitch, eos_mode=3):
    """Test JEOL dose calculation"""
    # Machine parameters
    machine_grid = 1.0 if eos_mode == 3 else 0.125  # nm
    exposure_grid = machine_grid * shot_pitch  # nm
    
    # JEOL frequency
    frequency = 50e6  # 50 MHz
    
    # Calculate actual dose per shot
    # Dose (μC/cm²) = (Current_nA × 100) / (Frequency_MHz × GridStep_nm²)
    dose_per_shot = (beam_current * 100) / (50 * exposure_grid**2)
    
    # Number of shots needed for base dose
    shots_needed = base_dose / dose_per_shot
    
    print(f"\nDose Calculation:")
    print(f"Machine grid: {machine_grid} nm")
    print(f"Exposure grid: {exposure_grid} nm")
    print(f"Dose per shot: {dose_per_shot:.3f} μC/cm²")
    print(f"Shots for {base_dose} μC/cm²: {shots_needed:.1f}")
    print(f"Dwell time per shot: {1/frequency*1e9:.1f} ns")

def main():
    """Run dose modeling tests"""
    print("=" * 60)
    print("Pattern Dose Modeling Test")
    print("=" * 60)
    
    # Test parameters
    pattern_size = 1.0  # μm
    shot_pitch = 4
    eos_mode = 3
    base_dose = 400  # μC/cm²
    beam_current = 2.0  # nA
    
    # Dose modulation factors
    dose_modulation = {
        0: 1.0,   # Interior
        1: 0.85,  # Edge
        2: 0.75   # Corner
    }
    
    print(f"\nPattern Parameters:")
    print(f"Size: {pattern_size} μm")
    print(f"Shot pitch: {shot_pitch}")
    print(f"EOS mode: {eos_mode}")
    print(f"Base dose: {base_dose} μC/cm²")
    print(f"Beam current: {beam_current} nA")
    
    # Calculate shots
    shots, exposure_grid = calculate_pattern_shots(pattern_size, shot_pitch, eos_mode)
    print(f"\nExposure grid: {exposure_grid} nm")
    print(f"Total shots: {len(shots)}")
    
    # Test dose calculation
    test_dose_calculation(base_dose, beam_current, shot_pitch, eos_mode)
    
    # Visualize dose map
    visualize_dose_map(shots, dose_modulation, pattern_size)
    
    print("\n" + "=" * 60)
    print("Test complete. Check test_dose_map.png for visualization.")

if __name__ == "__main__":
    main()