# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Electron Beam Lithography (EBL) simulation using Geant4 (C++) for Monte Carlo physics and PySide6 (Python) for GUI. Generates point spread functions (PSF) for BEAMER proximity effect correction software used in semiconductor lithography.

## Build & Run Commands

### C++ Simulation (Geant4)
```bash
# Build (from project root)
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j8

# Run with macro (batch mode)
./build/bin/ebl_sim macros/runs/run.mac

# Run with event count override
./build/bin/ebl_sim -m macros/runs/run.mac -n 50000

# Interactive mode (Qt visualization)
./build/bin/ebl_sim -u

# Pipe mode (stdin commands with visualization)
./build/bin/ebl_sim -p

# Multi-threading control
./build/bin/ebl_sim -t 4 macros/runs/run.mac  # Use 4 threads
./build/bin/ebl_sim -t 0 macros/runs/run.mac  # Sequential mode
```

### Python GUI
```bash
# Launch GUI (uses conda env: ebeam or ebl-sim)
./run_gui.sh

# Direct launch
python scripts/gui/ebl_gui.py

# Run GUI tests
python -m pytest scripts/gui/tests/
```

### CMake Options
- `-DBUILD_TESTING=ON` - Build unit tests
- `-DBUILD_ANALYSIS=ON` - Build analysis tools
- `-DGeant4_DIR=/path/to/geant4` - Specify Geant4 installation

## Architecture

### C++ Core (`src/`)
The simulation follows Geant4's modular architecture:

```
src/
├── common/     # EBLConstants.hh - all simulation parameters as constexpr
├── geometry/   # DetectorConstruction - resist/substrate/world geometry
├── physics/    # PhysicsList - EM physics with Livermore models
├── beam/       # PrimaryGeneratorAction, PatternGenerator (JEOL patterns)
└── actions/    # RunAction (PSF accumulation), SteppingAction (energy scoring)
```

**Data Flow**: Beam → SteppingAction (records energy deposits) → RunAction (accumulates into PSF bins) → Output files

**Key Messenger Commands** (used in .mac files):
- `/det/setResistComposition`, `/det/setResistThickness`, `/det/setResistDensity`, `/det/update`
- `/gun/energy`, `/gun/beamSize`, `/gun/position`
- `/run/beamOn`

### Python GUI (`scripts/gui/`)
MVC architecture with single entry point:

```
scripts/gui/
├── ebl_gui.py      # Main entry point (large monolithic file)
├── core/           # Config, validation, Geant4 environment detection
├── models/         # MaterialModel, BeamModel, SimulationModel (dataclasses)
├── services/       # BeamerConverterService, MacroGenerator, SimulationController
├── widgets/        # UI components (PySide6)
└── utils/          # threading_utils (SimulationWorker), plotting_utils
```

**Service Layer**: GUI → Services → Macro generation → subprocess (ebl_sim) → Parse output

### Output Data
All simulation outputs go to `output/` (gitignored):
- `psf_data.csv` - Radial energy distribution (radius, energy, normalized)
- `psf_beamer.txt` - BEAMER software format
- `simulation_summary.txt` - Run parameters and statistics

## Key Domain Concepts

### PSF (Point Spread Function)
Energy distribution from a point electron source. Uses logarithmic radial bins (0.5nm - 100μm) to capture both forward scattering (center) and backscattering (tails).

### Materials
Resist compositions defined as element:count strings (e.g., `"Al:1,C:5,H:4,O:2"`). Presets in `MaterialModel.PRESETS`:
- PMMA, HSQ (standard resists)
- Alucone, Sn-MLD, Zincone (metal-organic hybrid resists)

### BEAMER Integration
PSF files exported for BEAMER proximity effect correction. Point source (0nm beam) used because BEAMER applies beam blur separately.

## Geant4 Macro Examples

```bash
# Basic PSF simulation
/run/initialize
/det/setResistComposition "Sn:1,C:8,H:8,O:4"
/det/setResistThickness 30 nm
/det/setResistDensity 2.0 g/cm3
/det/update
/gun/energy 100 keV
/run/beamOn 100000
```

## Critical Constraints

1. **Macro Order**: Material settings MUST come before `/run/initialize` or use `/det/update` to rebuild geometry
2. **Point Source for PSF**: Default beam size is 0nm - BEAMER handles beam blur
3. **High-Z Materials**: Sn, Zn resists use finer physics cuts (0.01nm vs 0.05nm)
4. **WSL2 Display**: GUI requires X11 forwarding (`export DISPLAY=:0`)

## Serena MCP Tools (Preferred)

When Serena MCP is available, prefer these over standard file tools:
- `get_symbols_overview` / `find_symbol` - Navigate code by symbols
- `replace_symbol_body` / `replace_content` - Edit code
- `list_memories` / `read_memory` / `write_memory` - Session continuity for multi-session tasks
