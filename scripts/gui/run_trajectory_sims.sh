#!/bin/bash
# Run trajectory simulations for all metalcone materials at 10 and 100 keV

# Setup Geant4 environment
source /opt/geant4/bin/geant4.sh 2>/dev/null

EBL_SIM="/home/dreece23/projects/research/ebl-simulation/build/bin/ebl_sim"
MACRO_DIR="/home/dreece23/projects/research/ebl-simulation/scripts/gui/metalcone_animations_final/macros"
OUTPUT_DIR="/home/dreece23/projects/research/ebl-simulation/scripts/gui/metalcone_animations_final/trajectories"

mkdir -p "$OUTPUT_DIR"

echo "============================================================"
echo "Running EBL Trajectory Simulations"
echo "============================================================"
echo

# Run each simulation
for material in Alucone Zincone Tincone; do
    for energy in 10 100; do
        MACRO="traj_${material}_${energy}keV.mac"
        echo ">>> Running: $material at ${energy} keV"
        echo "    Macro: $MACRO"

        # Change to output directory so JSON is saved there
        cd "$OUTPUT_DIR"

        # Run simulation
        "$EBL_SIM" -m "${MACRO_DIR}/${MACRO}" 2>&1 | tail -10

        # Check if output was created
        if [ -f "traj_${material}_${energy}keV.json" ]; then
            echo "    ✓ Output: traj_${material}_${energy}keV.json"
            ls -lh "traj_${material}_${energy}keV.json"
        else
            echo "    ✗ Failed to create trajectory file"
        fi
        echo
    done
done

echo "============================================================"
echo "Trajectory simulations complete!"
echo "Output: $OUTPUT_DIR"
echo "============================================================"
ls -la "$OUTPUT_DIR"/*.json 2>/dev/null || echo "No JSON files found"
