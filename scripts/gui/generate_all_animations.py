#!/usr/bin/env python3
"""
Generate All Trajectory Animations for PhD Defense

Creates both quick matplotlib preview animations and exports data for Blender rendering.
"""

import sys
from pathlib import Path
import json

# Set matplotlib backend before any imports
import matplotlib
matplotlib.use('Agg')

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from trajectory_animator import ElectronAnimator


def generate_animations():
    """Generate animations for all metalcone materials at 10 and 100 keV."""

    traj_dir = Path(__file__).parent / "metalcone_animations_final" / "trajectories"
    output_dir = Path(__file__).parent / "metalcone_animations_final" / "animations"
    output_dir.mkdir(exist_ok=True)

    # Material parameters (EG-based chemistry)
    materials = {
        "Alucone": {"density": 1.5, "metal_z": 13, "desc": "Al-based MLD (TMA + EG)"},
        "Zincone": {"density": 2.0, "metal_z": 30, "desc": "Zn-based MLD (DEZ + EG)"},
        "Tincone": {"density": 2.5, "metal_z": 50, "desc": "Sn-based MLD (TDMASn + EG)"},
    }

    energies = [10, 100]  # keV

    print("=" * 70)
    print("Generating Trajectory Animations for PhD Defense")
    print("=" * 70)
    print()

    created = []

    for material, props in materials.items():
        for energy in energies:
            json_file = traj_dir / f"traj_{material}_{energy}keV.json"

            if not json_file.exists():
                print(f"  SKIP: {json_file.name} not found")
                continue

            print(f"\n>>> {material} at {energy} keV")
            print(f"    Loading: {json_file.name}")

            # Create animator
            animator = ElectronAnimator(
                resist_thickness=100,
                resist_material=material,
                beam_energy=energy,
                substrate_thickness=500,
                show_secondaries=False
            )

            # Load trajectory data
            if animator.load_geant4_trajectories(str(json_file)):
                # Generate dual-view animation
                output_gif = output_dir / f"anim_{material}_{energy}keV_dual.gif"

                print(f"    Creating animation...")
                animator.create_dual_view_animation(
                    output_file=str(output_gif),
                    fps=30,
                    duration=6.0,
                    loop=False
                )

                created.append(output_gif)
                print(f"    Saved: {output_gif.name}")
            else:
                print(f"    ERROR: Failed to load trajectory data")

    print()
    print("=" * 70)
    print(f"Generated {len(created)} animations")
    print("=" * 70)

    for f in created:
        print(f"  {f.name}")

    return created


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate trajectory animations")
    parser.add_argument("--preview", action="store_true", help="Generate quick preview GIFs")
    args = parser.parse_args()

    generate_animations()


if __name__ == "__main__":
    main()
