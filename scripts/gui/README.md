# EBL Simulation GUI

**Main Entry Point**: `ebl_gui.py` - Comprehensive GUI with PSF simulation, pattern exposure, and BEAMER integration

## Quick Start

### Prerequisites
```bash
pip install PySide6 matplotlib numpy pandas scipy
```

### Run the GUI
```bash
# From project root:
./run_gui.sh

# Or directly:
python scripts/gui/ebl_gui.py
```

## Architecture

### Directory Structure

```
scripts/gui/
├── ebl_gui.py              # MAIN GUI - Full-featured EBL simulation interface
│
├── core/                   # Core infrastructure
│   ├── config.py          # Configuration management
│   ├── geant4_detector.py # Geant4 path detection
│   ├── validator.py       # Input validation
│   ├── file_manager.py    # File operations
│   └── constants.py       # Application constants
│
├── models/                 # Data models
│   ├── beam_model.py      # Beam parameters
│   ├── material_model.py  # Resist/substrate materials
│   └── simulation_model.py # Simulation configuration
│
├── services/              # Business logic
│   ├── beamer_converter.py # BEAMER format conversion
│   └── macro_generator.py  # Geant4 macro generation
│
├── utils/                 # Utilities
│   ├── threading_utils.py # Simulation threading
│   ├── plotting_utils.py  # Plot helpers
│   └── data_utils.py      # Data processing
│
├── widgets/               # UI components
│   ├── common/           # Shared widgets (buttons, inputs)
│   ├── plotting/         # Plot widgets
│   ├── modern/           # Material Design 3 components
│   ├── enhanced_beam_widget.py
│   ├── resist_properties_widget.py
│   ├── pattern_heatmap_widget.py      # Active - used in main GUI
│   ├── proximity_correction_widget.py # Active - used in main GUI
│   └── settings_dialog.py
│
└── archive/              # Deprecated/prototype code
    ├── interfaces/       # Orphaned MVC interfaces (reference only)
    ├── widgets/          # Unused widgets (~2,880 lines)
    ├── launchers/        # Old launcher variants
    ├── mockups/          # UI design prototypes
    └── visualization/    # Deprecated visualization code
```

## Standalone Scripts

Beyond the main GUI, several specialized standalone tools are available:

### PSF Analysis & Visualization
- **`psf_viewer.py`** - Interactive PSF data viewer with comparison tools
- **`psf_visualizer.py`** - Advanced PSF visualization with energy analysis
- **`psf_energy_visualizer.py`** - Energy-dependent PSF visualization
- **`psf_presentation_figure.py`** - Generate publication-quality PSF figures

### Animation & Trajectory
- **`trajectory_viewer.py`** - View electron trajectory data
- **`trajectory_animator.py`** - Create trajectory animations
- **`animation_gui.py`** - Animation generation interface
- **`blender_trajectory_export.py`** - Export trajectories for Blender
- **`generate_all_animations.py`** - Batch animation generation

### Embedded Visualization
- **`vis_embedded.py`** - Embedded Geant4 visualization interface

## Features

### Main GUI (`ebl_gui.py`)
- **PSF Simulation**: Point spread function generation and analysis
- **Pattern Exposure**: JEOL pattern generation with proximity correction
- **Material Database**: HSQ, PMMA, AluconeXPS, Sn-MLD, Zincone
- **BEAMER Integration**: Export PSFs in BEAMER format for JEOL systems
- **2D Visualization**: Interactive contour plots and heatmaps
- **Batch Processing**: Queue multiple simulations
- **Configuration Management**: Save/load simulation parameters

### Archived Code (Not in Use)

The `archive/` directory contains:
- **MVC Interfaces** (~1,600 lines): Prototype dashboard interfaces never integrated
- **Unused Widgets** (~2,900 lines): Pattern/proximity widgets superseded by main GUI tabs
- **Old Launchers**: Pre-consolidation GUI variants
- **UI Mockups**: Early design explorations

These files are preserved as reference material and design history.

## Development Notes

### Active Development Focus
- Main GUI: `ebl_gui.py` (5,100+ lines, needs modularization)
- Standalone analysis tools maintain separate scope

### Code Organization
- **Models → Services → Widgets** architecture
- Serena MCP tools preferred for navigation/editing
- Output data goes to `output/` (gitignored)

### Adding New Materials
Create JSON configs in `config/materials/`:
```json
{
  "name": "Material Name",
  "density": "g/cm3",
  "composition": {"Element": fraction}
}
```

## Testing

```bash
# Verify GUI can import (quick check)
python -c "from scripts.gui.ebl_gui import *"

# Launch GUI
./run_gui.sh
```

## Troubleshooting

### Import Errors
Ensure you're running from project root or have `PYTHONPATH` set:
```bash
export PYTHONPATH=/path/to/ebl-simulation:$PYTHONPATH
```

### Missing Geant4
The GUI will auto-detect Geant4. If not found, it will prompt for the path.

### Qt/Matplotlib Issues
If you see Qt backend errors:
```bash
pip install --upgrade PySide6 matplotlib
```

## Contributing

When modifying GUI code:
1. Use Serena symbolic tools (not grep/sed)
2. Follow existing MVC patterns
3. Archive deprecated code (don't delete)
4. Test both import and runtime
5. Update this README if structure changes

---

**Last Updated**: January 15, 2026 (Phase 2 cleanup)
