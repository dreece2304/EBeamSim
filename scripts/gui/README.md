# EBL Simulation GUI

**Main Entry Point**: `ebl_gui.py` — PSF simulation, results visualization, and BEAMER export.
For the user-facing workflow guide, see the repository root [README](../../README.md).

## Quick Start

```bash
# From project root (activates the ebl-sim conda env, handles WSL2 display):
./run_gui.sh

# Or directly, in an env with PySide6/matplotlib/numpy/pandas/scipy:
python scripts/gui/ebl_gui.py
```

Environment setup: `conda env create -f environment.yml` (repo root)
or `pip install -r scripts/gui/requirements.txt`.

## Architecture

Everything user-facing lives in `ebl_gui.py` (one large file, ~5,100 lines):
`EBLMainWindow` (tabs, menus, inline macro generation, simulation lifecycle) plus the inline
`PlotWidget` (1D PSF + BEAMER conversion) and `Enhanced2DPlotWidget` (2D maps).

```
scripts/gui/
├── ebl_gui.py              # MAIN GUI (single source of truth for the UI)
├── core/                   # Support: file_manager, validator, geant4_detector, constants
├── utils/                  # threading_utils (SimulationWorker), plotting/data helpers
├── widgets/                # settings_dialog, pattern_heatmap_widget, common/status_button
├── tests/                  # pytest suite (headless-safe)
└── archive/                # Superseded code kept for reference - never import from here
```

Simulation flow: `generate_macro()` writes `gui_generated.mac` (detector settings before
`/run/initialize`, `/ebl/output/*` filenames) → `SimulationWorker` runs `ebl_sim` as a
subprocess and parses stdout for progress → results auto-load → BEAMER file
(`radius [µm]`, peak-normalized) in the repo's `output/` directory.

## Standalone Scripts

Separate tools, not part of the main GUI:

- **PSF analysis**: `psf_viewer.py`, `psf_visualizer.py`, `psf_energy_visualizer.py`,
  `psf_presentation_figure.py`, `psf_convolution.py`, `process_psf.py`
- **Trajectories/animation**: `trajectory_viewer.py`, `trajectory_animator.py`,
  `animation_gui.py`, `blender_trajectory_export.py`, `generate_all_animations.py`,
  `run_trajectory_sims.sh`
- **Embedded Geant4 vis**: `vis_embedded.py`
- **Pattern dose**: `visualize_pattern_dose.py`

## Testing

```bash
cd scripts/gui
QT_QPA_PLATFORM=offscreen python -m pytest tests/
```

Covers: SimulationWorker progress parsing (PSF + pattern mode), stop/finished behavior
(regression for the stuck-Run-button bug), main-window construction, composition parsing.

## Troubleshooting

- **Import errors**: run from the project root, or `export PYTHONPATH=/path/to/ebl-simulation`.
- **Missing Geant4**: auto-detected; set the path in Settings if not found.
- **Qt backend errors**: `pip install --upgrade PySide6 matplotlib`.

## Contributing

1. New UI work goes in `ebl_gui.py` (or a new widget module under `widgets/`).
2. Archive deprecated code under `archive/` (don't delete), and never import from `archive/`.
3. Keep tests green: `QT_QPA_PLATFORM=offscreen python -m pytest tests/`.
4. Update this README if the structure changes.

---

**Last Updated**: July 23, 2026 (physics-fix + cleanup pass)
