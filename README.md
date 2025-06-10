# EBL Simulation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Geant4](https://img.shields.io/badge/Geant4-11.3-blue.svg)](https://geant4.web.cern.ch/)
[![C++](https://img.shields.io/badge/C++-17-green.svg)](https://isocpp.org/)

A high-precision Geant4-based simulation for Electron Beam Lithography (EBL) point spread functions, featuring advanced material modeling for next-generation resists including Alucone-based materials.

## Features

- **Accurate PSF Calculation**: Logarithmic binning from 50 pm to 100 μm
- **Advanced Material Support**: Including Alucone resists based on XPS characterization
- **Modular Architecture**: Clean separation of geometry, physics, and analysis
- **Modern GUI**: PySide6-based interface with real-time monitoring
- **BEAMER Integration**: Direct export to BEAMER PSF format
- **Comprehensive Physics**: Full EM physics with fluorescence and Auger processes

## Table of Contents

- [Installation](#installation)
- [Building](#building)
- [Usage](#usage)
- [GUI](#gui)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Citation](#citation)
- [License](#license)

## Installation

### Prerequisites

- **Geant4 11.3+** with Qt and OpenGL visualization
- **CMake 3.16+**
- **C++17 compatible compiler**
  - Visual Studio 2019+ (Windows)
  - GCC 7+ (Linux)
  - Clang 9+ (macOS)
- **Python 3.8+** (for GUI)

### Clone Repository

```bash
git clone https://github.com/yourusername/ebl-simulation.git
cd ebl-simulation
```

### Install Python Dependencies (for GUI)

```bash
pip install -r scripts/gui/requirements.txt
```

## Building

### Linux/macOS

```bash
mkdir build
cd build
cmake ..
make -j$(nproc)
```

### Windows (Visual Studio)

```bash
mkdir build
cd build
cmake .. -G "Visual Studio 17 2022" -A x64
cmake --build . --config Release
```

Or open the folder directly in Visual Studio 2022.

### CMake Options

- `-DBUILD_TESTING=ON`: Build unit tests
- `-DBUILD_ANALYSIS=ON`: Build analysis tools
- `-DGeant4_DIR=/path/to/geant4`: Specify Geant4 installation

## Usage

### Command Line

```bash
# Run with macro
./build/bin/ebl_sim macros/runs/run.mac

# Interactive mode
./build/bin/ebl_sim -u

# Quick test
./build/bin/ebl_sim macros/runs/test.mac
```

### Example Macro

```bash
# Set resist properties
/det/setResistComposition "Al:1,C:5,H:4,O:2"
/det/setResistThickness 30 nm
/det/setResistDensity 1.35 g/cm3
/det/update

# Configure beam
/gun/particle e-
/gun/energy 100 keV
/gun/position 0 0 100 nm
/gun/beamSize 2 nm

# Run simulation
/run/beamOn 100000
```

## GUI

Launch the modern GUI for easier simulation control:

```bash
cd scripts/gui
python ebl_gui_main.py
```

### GUI Features

- Material preset management
- Real-time simulation monitoring
- Interactive PSF visualization
- Batch processing support
- Configuration save/load

![GUI Screenshot](docs/images/gui_screenshot.png)

## Project Structure

```
ebl-simulation/
├── apps/                  # Applications
│   └── ebl_sim/          # Main simulation executable
├── src/                   # Source code (modular)
│   ├── common/           # Shared utilities
│   ├── geometry/         # Detector construction
│   ├── physics/          # Physics lists
│   ├── beam/             # Primary generation
│   └── actions/          # User actions
├── macros/               # Geant4 macro files
├── scripts/              # Python scripts
│   └── gui/              # GUI application
├── config/               # Configuration files
├── tests/                # Unit tests
└── docs/                 # Documentation
```

## Output Files

- `ebl_psf_data.csv`: Radial PSF data with energy deposition
- `beamer_psf.dat`: BEAMER-compatible PSF format
- `simulation_summary.txt`: Run statistics and parameters

## Materials

### Predefined Materials

- **PMMA**: C:5,H:8,O:2 (1.19 g/cm³)
- **HSQ**: Si:1,H:1,O:1.5 (1.4 g/cm³)
- **Alucone (XPS)**: Al:1,C:5,H:4,O:2 (1.35 g/cm³)
- **Alucone (Exposed)**: Al:1,C:5,H:4,O:3 (1.40 g/cm³)

## Performance

Typical simulation times on modern hardware:
- 10k events: ~1 minute
- 100k events: ~10 minutes  
- 1M events: ~2 hours

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Citation

If you use this software in your research, please cite:

```bibtex
@software{ebl_simulation,
  title = {EBL Simulation: High-Precision Electron Beam Lithography Modeling},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/yourusername/ebl-simulation}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Geant4 Collaboration for the simulation toolkit
- XPS characterization data for Alucone materials
- BEAMER software compatibility testing

## Contact

- **Email**: your.email@institution.edu
- **Issues**: [GitHub Issues](https://github.com/yourusername/ebl-simulation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ebl-simulation/discussions)