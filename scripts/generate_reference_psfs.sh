#!/bin/bash
# Generate reference PSF library for GUI comparison
# This script runs 4 simulations to create standard reference PSFs

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Reference PSF Library Generation${NC}"
echo -e "${BLUE}========================================${NC}"

# Find project root and build directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
EXECUTABLE="$BUILD_DIR/bin/ebl_sim"
OUTPUT_DIR="$PROJECT_ROOT/data/reference_psfs"
MACRO_DIR="$PROJECT_ROOT/macros/reference_psfs"

# Check if executable exists
if [ ! -f "$EXECUTABLE" ]; then
    echo -e "${RED}Error: ebl_sim executable not found at $EXECUTABLE${NC}"
    echo -e "${RED}Please build the project first: cd build && make${NC}"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Define simulations
declare -a MATERIALS=("PMMA" "HSQ" "AluconeXPS" "SnMLD")
declare -a MACROS=("ref_pmma_100nm.mac" "ref_hsq_100nm.mac" "ref_alucone_30nm.mac" "ref_snmld_30nm.mac")
declare -a THICKNESSES=("100" "100" "30" "30")

echo -e "\n${GREEN}Running 4 reference PSF simulations...${NC}"
echo -e "${BLUE}This will take approximately 10-20 minutes depending on CPU${NC}\n"

# Run each simulation
for i in "${!MATERIALS[@]}"; do
    MATERIAL="${MATERIALS[$i]}"
    MACRO="${MACROS[$i]}"
    THICKNESS="${THICKNESSES[$i]}"

    echo -e "${GREEN}[${i}/4] Generating ${MATERIAL} ${THICKNESS}nm PSF...${NC}"

    # Create temporary output directory for this simulation
    TEMP_DIR="$OUTPUT_DIR/temp_$MATERIAL"
    mkdir -p "$TEMP_DIR"

    # Run simulation in temp directory
    cd "$TEMP_DIR"

    # Run with proper error handling
    if "$EXECUTABLE" "$MACRO_DIR/$MACRO" > simulation.log 2>&1; then
        echo -e "${GREEN}  ✓ Simulation complete${NC}"

        # Rename output files with standard naming (check output/ subdirectory)
        if [ -f "output/ebl_psf_data.csv" ]; then
            mv output/ebl_psf_data.csv "$OUTPUT_DIR/ref_${MATERIAL}_${THICKNESS}nm_data.csv"
            echo -e "${GREEN}  ✓ Saved CSV data${NC}"
        elif [ -f "ebl_psf_data.csv" ]; then
            mv ebl_psf_data.csv "$OUTPUT_DIR/ref_${MATERIAL}_${THICKNESS}nm_data.csv"
            echo -e "${GREEN}  ✓ Saved CSV data${NC}"
        fi

        if [ -f "output/beamer_psf.dat" ]; then
            mv output/beamer_psf.dat "$OUTPUT_DIR/ref_${MATERIAL}_${THICKNESS}nm_beamer.dat"
            echo -e "${GREEN}  ✓ Saved BEAMER format${NC}"
        elif [ -f "beamer_psf.dat" ]; then
            mv beamer_psf.dat "$OUTPUT_DIR/ref_${MATERIAL}_${THICKNESS}nm_beamer.dat"
            echo -e "${GREEN}  ✓ Saved BEAMER format${NC}"
        fi

        if [ -f "output/simulation_summary.txt" ]; then
            mv output/simulation_summary.txt "$OUTPUT_DIR/ref_${MATERIAL}_${THICKNESS}nm_summary.txt"
        elif [ -f "simulation_summary.txt" ]; then
            mv simulation_summary.txt "$OUTPUT_DIR/ref_${MATERIAL}_${THICKNESS}nm_summary.txt"
        fi

        # Clean up temp directory
        cd "$PROJECT_ROOT"
        rm -rf "$TEMP_DIR"

    else
        echo -e "${RED}  ✗ Simulation failed! Check $TEMP_DIR/simulation.log${NC}"
        cd "$PROJECT_ROOT"
        exit 1
    fi

    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Reference PSF Library Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nGenerated files in: ${BLUE}$OUTPUT_DIR${NC}"
echo -e "\n${GREEN}Files created:${NC}"
ls -lh "$OUTPUT_DIR"/*.dat "$OUTPUT_DIR"/*.csv 2>/dev/null || echo "No files found"

echo -e "\n${BLUE}Next step: Copy BEAMER .dat files to scripts/gui/ for GUI access${NC}"
echo -e "${BLUE}Command: cp $OUTPUT_DIR/*.dat $PROJECT_ROOT/scripts/gui/${NC}"
