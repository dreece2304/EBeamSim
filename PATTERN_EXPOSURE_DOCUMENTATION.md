# EBeamSim Pattern Exposure Documentation

## Project Overview

EBeamSim is a Geant4-based electron beam lithography simulator that accurately models electron-matter interactions in resist materials. This document describes the pattern exposure feature addition that enables simulation of JEOL electron beam lithography systems performing actual pattern writing.

## Original System Capabilities

### Core Features
- **Point Spread Function (PSF) simulation**: Models electron scattering for proximity effect correction
- **Material modeling**: Supports various resist materials (Alucone, PMMA, HSQ, ZEP)
- **Physics processes**: Full Geant4 physics including fluorescence and Auger electrons
- **Output formats**: PSF data for BEAMER software, CSV for analysis

### Architecture
- **C++ Backend**: Geant4 simulation engine with modular design
  - `PrimaryGeneratorAction`: Electron beam generation
  - `DetectorConstruction`: Resist and substrate geometry
  - `SteppingAction`: Energy deposition tracking
  - `DataManager`: Data collection and output
- **Python GUI**: PySide6-based interface for configuration and visualization

## Pattern Exposure Upgrade Motivation

### Why Add Pattern Exposure?
1. **Validate PSF accuracy**: Compare simulated dose distribution with expected patterns
2. **Study proximity effects**: Visualize forward/backscattering in actual patterns
3. **Process optimization**: Determine optimal dose and exposure parameters
4. **JEOL system modeling**: Accurate simulation of real e-beam tool behavior

### JEOL System Parameters
The upgrade models the JEOL JBX-6300FS system with:
- **Operating Modes**: 
  - Mode 3 (4th lens): 500 um field, 1.0 nm machine grid
  - Mode 6 (5th lens): 62.5 um field, 0.125 nm machine grid
- **Beam Currents**: 0.5, 1, 2, 5, 8, 10, 20 nA
- **Shot Pitch**: 1 or even multiples of machine grid
- **Hardware Limit**: 50 MHz maximum clock frequency

## Implementation Details

### New C++ Components

#### 1. PatternGenerator (`src/beam/include/PatternGenerator.hh`)
```cpp
class PatternGenerator {
    // Generates exposure patterns (square, line, custom)
    // Calculates dwell time from dose equation
    // Validates field boundaries
    // Computes electrons per exposure point
};
```

Key features:
- Pattern types: SINGLE_SPOT, SQUARE, LINE, CUSTOM (all fully implemented)
- JEOL mode configuration
- Dwell time calculation: `Clock Freq = (I_beam × 1000 × 100) / (Dose × Grid²)`
- Electrons per point: `N = I_beam × t_dwell / e`

#### 2. Enhanced PrimaryGeneratorAction
```cpp
// Refactored into clean, focused methods:
void GeneratePrimaries(G4Event* anEvent);     // Main dispatcher
void GeneratePatternPrimary(G4Event* anEvent); // Pattern mode
void GeneratePSFPrimary(G4Event* anEvent);     // PSF mode
void ValidateBeamPosition() const;             // Position validation
G4double CalculateBeamSigma() const;           // Beam spread calculation
G4double GetBeamZPosition() const;             // Smart Z positioning
```

#### 3. Enhanced DataManager
```cpp
// Added:
// - 3D dose grid for spatial dose accumulation
// - Energy to dose conversion (keV → uC/cm^2)
// - Pattern-specific output formats
// - Singleton pattern for efficiency
```

#### 4. VerbosityManager (NEW)
```cpp
// Conditional logging system for performance:
// - Multiple verbosity levels (SILENT, ERRORS, WARNINGS, INFO, DEBUG, VERBOSE)
// - Convenient macros: LOG_ERROR, LOG_WARNING, LOG_INFO, LOG_DEBUG, LOG_VERBOSE
// - Significantly reduces I/O overhead in large simulations
```

#### 5. Messenger Classes
- `PatternMessenger`: Controls pattern parameters via macro commands
- `DataMessenger`: Initializes dose accumulation grid

### New Python GUI Components

#### Pattern Exposure Tab
```python
# Features:
# - JEOL mode selection (radio buttons)
# - Pattern parameters (type, size, position)
# - Exposure parameters (beam current, dose, shot pitch)
# - Real-time dwell time calculation
# - Electrons per point display
# - Dose grid resolution settings
# - Parameter validation
# - Automatic macro generation for pattern mode
```

#### BEAMER Converter (NEW - `beamer_converter.py`)
```python
class BEAMERConverter:
    # Consolidated all BEAMER conversion functionality
    # - Automatic parameter extraction (alpha, beta, eta)
    # - Format conversion with validation
    # - Quality diagnostics
```

### Key Algorithms

#### 1. Dose Calculation
```
Dose (uC/cm^2) = (Beam Current (pA) × 100) / (Shot Pitch² × Clock Frequency (MHz))
```

#### 2. Dwell Time
```
Dwell Time = 1 / Clock Frequency
If Clock Freq > 50 MHz: clamp to 50 MHz and recalculate actual dose
```

#### 3. Electrons Per Point
```
Electrons/point = (Beam Current × Dwell Time) / elementary_charge
```

## Complete List of Changes

### C++ Backend Changes

1. **Created PatternGenerator class**:
   - Generates square patterns with configurable spacing ✓
   - LINE pattern implementation (horizontal lines) ✓
   - CUSTOM pattern implementation (cross pattern example) ✓
   - Calculates exposure parameters ✓
   - Validates against JEOL constraints ✓

2. **Refactored PrimaryGeneratorAction**:
   - Split into focused methods (pattern vs PSF generation) ✓
   - Added helper methods to eliminate code duplication ✓
   - Pattern mode with multiple electrons per point ✓
   - Tracks progress through pattern points ✓
   - Maintains beam spread at each exposure location ✓

3. **Enhanced DataManager**:
   - Added 3D dose grid (fDoseGrid) ✓
   - Dose normalization from energy to uC/cm^2 ✓
   - Separate output files for pattern dose ✓
   - Fixed Unicode characters (μC/cm² → uC/cm^2) ✓

4. **Updated SteppingAction**:
   - Accumulates dose in pattern mode ✓
   - Proper mode detection via grid initialization ✓

5. **Added VerbosityManager**:
   - Centralized conditional logging system ✓
   - Significant performance improvement for large simulations ✓

6. **Performance Optimizations**:
   - Cached loop sizes in RunAction ✓
   - Optimized string parsing in parseComposition ✓
   - Single-pass parsing without temporary strings ✓

7. **Fixed All Build Warnings**:
   - Replaced Unicode characters in all C++ files ✓
   - Fixed type conversion warnings ✓

### Python GUI Changes

1. **New Pattern Exposure Tab**:
   - JEOL mode selection ✓
   - Discrete beam current values ✓
   - Shot pitch validation ✓
   - Real-time dwell time display ✓
   - Electrons per point calculation ✓
   - Field boundary checking ✓

2. **GUI Macro Generation**:
   - Detects pattern mode ✓
   - Generates pattern-specific commands ✓
   - Calculates dose grid bounds ✓
   - Automatically calculates total events needed ✓

3. **BEAMER Converter Consolidation**:
   - Single reusable BEAMERConverter class ✓
   - Eliminates code duplication ✓

4. **Fixed Unicode Issues**:
   - Replaced emoji symbols with text equivalents ✓
   - Fixed Greek letters (μ→u, α→alpha, β→beta) ✓
   - Fixed superscripts (²→^2, ³→^3) ✓

### Physics Corrections

1. **Proper Dose Delivery**:
   - Fires correct number of electrons per point ✓
   - Based on beam current and dwell time ✓

2. **Unit Conversions**:
   - Energy (keV) to dose (uC/cm^2) ✓
   - Proper normalization by voxel area ✓

3. **Constraint Validation**:
   - Shot pitch: 1 or even numbers only ✓
   - Pattern must fit within field ✓
   - Clock frequency ≤ 50 MHz ✓

## Usage Example

### GUI Usage
1. Select "Pattern Exposure" tab
2. Choose JEOL mode (Mode 3 or Mode 6)
3. Select pattern type (Square, Line, or Custom)
4. Set beam current from dropdown
5. Enter dose and shot pitch
6. Click "Generate Macro" and "Run Simulation"

### Macro Commands
```bash
# Enable pattern mode
/pattern/enable true
/pattern/type square    # or "line" or "custom"
/pattern/jeolMode mode3
/pattern/shotPitch 4
/pattern/size 1000 nm
/pattern/center 0 0 0 nm
/pattern/beamCurrent 2.0 nA
/pattern/dose 300
/pattern/generate

# Initialize dose grid
/data/initDoseGrid 200 200 20 -1000 1000 -1000 1000 0 30 nm

# Set verbosity level (NEW)
/verbosity/level 3  # INFO level

# Run simulation (events = points × electrons/point)
/run/beamOn 1000000
```

### Output Files
- `pattern_dose_distribution.csv`: 3D dose grid with X,Y,Z,Energy[keV],Dose[uC/cm^2]
- `pattern_dose_2d.csv`: 2D projection integrated through Z

## Code Quality Improvements

### Architecture
- Clean separation between PSF and pattern modes ✓
- No significant code duplication ✓
- Efficient memory usage with conditional allocation ✓
- Performance-optimized for large simulations ✓

### Build Status
- All Unicode warnings fixed ✓
- All compilation warnings resolved ✓
- Cross-platform compatible (Windows code page issues fixed) ✓

## Future Enhancements

1. **Pattern Import**:
   - Load custom patterns from files
   - Support for GDS/OASIS formats

2. **Field Stitching**:
   - Multi-field patterns
   - Stitching error simulation
   - Field alignment algorithms

3. **Proximity Correction**:
   - Dose modulation (0-255 shot ranks)
   - PSF-based correction
   - Iterative optimization

4. **GPU Acceleration**:
   - Dose accumulation on GPU
   - Real-time visualization
   - PSF convolution

## Technical Notes

### Compilation
- Requires Geant4 10.7+ with Qt support
- C++17 standard
- CMake 3.16+

### Key Files Modified/Added
- `src/beam/`: PatternGenerator, refactored PrimaryGeneratorAction, messengers
- `src/common/`: DataManager with dose grid, VerbosityManager (NEW)
- `src/actions/`: SteppingAction, optimized RunAction
- `scripts/gui/ebl_gui.py`: Pattern exposure tab with full macro generation
- `scripts/gui/beamer_converter.py`: Consolidated BEAMER converter (NEW)
- `CMakeLists.txt`: Build configuration updates

### Testing
Use `test_pattern.mac` to verify:
- Pattern generation (square, line, custom) ✓
- Dose accumulation ✓
- Output file formats ✓
- GUI integration ✓

## Physical Accuracy

The implementation accurately models:
- JEOL vector scanning behavior ✓
- Beam dwell time based on dose requirements ✓
- Electron scattering (forward and backscattering) ✓
- 3D dose distribution in resist ✓
- Proximity effects from neighboring exposures ✓
- Discrete electrons per point matching real hardware ✓

The dose calculation matches JEOL specifications and the simulation fires the physically correct number of electrons at each exposure point to achieve the target dose.

## Summary

The pattern exposure feature is now 100% complete with all improvements implemented:
- Full pattern generation (SQUARE, LINE, CUSTOM) ✓
- Clean, refactored code architecture ✓
- Performance optimizations throughout ✓
- Complete GUI integration with macro generation ✓
- All build warnings and Unicode issues fixed ✓
- Comprehensive documentation ✓

The system is production-ready for simulating JEOL electron beam lithography pattern exposures.