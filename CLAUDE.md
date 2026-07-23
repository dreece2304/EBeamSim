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

# Run GUI tests (headless)
QT_QPA_PLATFORM=offscreen python -m pytest scripts/gui/tests/
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
Single monolithic entry point plus small support packages:

```
scripts/gui/
├── ebl_gui.py      # Main entry point: EBLMainWindow (tabs, menus, inline macro
│                   #   generation via generate_macro, simulation lifecycle)
├── core/           # file_manager, validator, geant4_detector, constants
├── widgets/        # psf_plot_widget (1D PSF + BEAMER conversion), enhanced_2d_plot,
│                   #   settings_dialog, pattern_heatmap_widget, common/status_button
├── utils/          # threading_utils (SimulationWorker - runs ebl_sim, parses progress)
├── tests/          # pytest suite (run offscreen, see below)
└── archive/        # superseded code (do not import from here)
```

**Flow**: GUI → `generate_macro()` writes `gui_generated.mac` → `SimulationWorker` subprocess
runs ebl_sim → stdout parsed for progress → results auto-loaded → BEAMER file.
Detector settings are written BEFORE `/run/initialize` in the generated macro.

```bash
# Run GUI tests (headless)
cd scripts/gui && QT_QPA_PLATFORM=offscreen python -m pytest tests/
```

### Output Data
GUI runs write to `output/` (gitignored) with descriptive names (`<prefix>_psf.csv`,
`<prefix>_beamer.dat`, `<prefix>_summary.txt`, `<prefix>_psf2d.csv`). CLI runs write default
names (`ebl_psf_data.csv`, `beamer_psf.dat`, `simulation_summary.txt`) to the current directory
unless the macro sets `/ebl/output/setDirectory`. The BEAMER file is radius (µm) vs
peak-normalized PSF.

## Key Domain Concepts

### PSF (Point Spread Function)
Energy distribution from a point electron source. Uses logarithmic radial bins (0.5nm - 100μm) to capture both forward scattering (center) and backscattering (tails).

### Materials
Resist compositions defined as element:count strings (e.g., `"Al:1,C:5,H:4,O:2"`; decimal counts allowed, e.g. HSQ `"Si:1,H:1,O:1.5"`). Presets in `ebl_gui.py` (`self.material_presets`, ~line 2866):
- PMMA, HSQ (standard resists)
- Alucone, Sn-MLD, Zincone (metal-organic hybrid resists)

### BEAMER Integration
PSF files exported for BEAMER proximity effect correction. Point source (0nm beam) used because BEAMER applies beam blur separately.

## Geant4 Macro Examples

```bash
# Basic PSF simulation (detector settings BEFORE /run/initialize)
/det/setResistComposition "Sn:1,C:8,H:8,O:4"
/det/setResistThickness 30 nm
/det/setResistDensity 2.0 g/cm3
/run/initialize
/gun/energy 100 keV
/gun/beamSize 0 nm
/run/beamOn 100000
```

## Critical Constraints

1. **Macro Order**: Material settings SHOULD come before `/run/initialize` (built once, correctly). Changing them after initialize requires `/det/update`, which swaps the material, resizes the resist, and re-applies cuts before the next `/run/beamOn`
2. **Point Source for PSF**: Default beam size is 0nm - BEAMER handles beam blur
3. **High-Z Materials**: Sn, Zn resists use finer physics cuts (0.01nm vs 0.05nm)
4. **WSL2 Display**: GUI requires X11 forwarding (`export DISPLAY=:0`)

## Serena MCP Tools (Preferred)

When Serena MCP is available, prefer these over standard file tools:
- `get_symbols_overview` / `find_symbol` - Navigate code by symbols
- `replace_symbol_body` / `replace_content` - Edit code
- `list_memories` / `read_memory` / `write_memory` - Session continuity for multi-session tasks
