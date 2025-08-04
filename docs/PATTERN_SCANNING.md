# JEOL-like Pattern Scanning for EBeamSim

This document describes the new pattern scanning functionality added to EBeamSim, which simulates JEOL JBX-6300FS e-beam lithography system behavior.

## Overview

The pattern scanning feature allows you to:
- Create square patterns with vector scanning (beam moves only to exposed areas)
- Configure JEOL-specific parameters (EOS modes, shot pitch, field size)
- Handle field stitching for patterns larger than a single field
- Apply dose modulation for proximity effect correction
- Use the Python GUI to configure all parameters

## Key Parameters

### Machine Grid
- **Mode 3 (4th Lens)**: 1.0 nm
- **Mode 6 (5th Lens)**: 0.125 nm

### Field Size
- **Mode 3**: 500 μm
- **Mode 6**: 62.5 μm

### Shot Pitch
- Must be 1 or even multiples of 2 (2, 4, 6, 8...)
- Exposure grid = Machine grid × Shot pitch

### Dose Calculation
```
Dose [μC/cm²] = (Current[pA] × 100) / (Frequency[MHz] × GridStep[nm]²)
```

## Using Pattern Scanning

### Via Command Line Macro

```bash
# Example macro commands
/pattern/jeol/eosMode 3           # Set to 4th lens mode
/pattern/jeol/shotPitch 4         # 4nm exposure grid
/pattern/jeol/beamCurrent 2.0     # 2 nA
/pattern/jeol/baseDose 400.0      # 400 μC/cm²

# Configure dose modulation
/pattern/jeol/shotRank 0
/pattern/jeol/modulation 1.0      # Interior: 100% dose
/pattern/jeol/shotRank 1
/pattern/jeol/modulation 0.9      # Edge: 90% dose
/pattern/jeol/shotRank 2
/pattern/jeol/modulation 0.8      # Corner: 80% dose

# Define pattern
/pattern/type square
/pattern/size 1 um
/pattern/center 0 0 0
/pattern/generate
/pattern/beamMode pattern

# Run simulation (events = number of shots)
/run/beamOn 65536
```

### Via Python GUI

1. Open the "Pattern Scanning" tab
2. Select "Pattern Mode" radio button
3. Configure:
   - Pattern type (square, array, etc.)
   - Pattern size and position
   - EOS mode and shot pitch
   - Beam current and base dose
   - Dose modulation factors
4. The GUI automatically calculates the required number of shots
5. Click "Run Simulation"

## Pattern Types

### Square Pattern
- Single square with specified size
- Automatic edge/corner detection for dose modulation
- Three scanning strategies: raster, serpentine, spiral

### Array Pattern
- Multiple squares in a grid
- Configurable array size (Nx × Ny)
- Adjustable pitch between patterns

## Field Stitching

When patterns exceed the field size:
- Automatic field assignment
- Field boundary detection
- Progress reporting shows field transitions
- Typical stitching error: ~20 nm

## Proximity Effect Correction

The system supports 256 shot ranks (0-255) for dose modulation:
- Rank 0: Interior shots (typically 100% dose)
- Rank 1: Edge shots (typically 90% dose)
- Rank 2: Corner shots (typically 80% dose)

## Example Applications

### 1. Single Square for Proximity Testing
```
Pattern: 1 μm square
Shot pitch: 4 nm
Dose modulation: Interior 100%, Edge 90%, Corner 80%
```

### 2. Array for Dense Pattern Analysis
```
Pattern: 3×3 array of 500 nm squares
Array pitch: 2 μm
Purpose: Study inter-pattern proximity effects
```

### 3. Large Pattern with Field Stitching
```
Pattern: 600 μm square (exceeds 500 μm field)
Shot pitch: 20 nm (coarser for speed)
Result: Pattern split across 4 fields
```

## Implementation Details

### New Classes
- `JEOLParameters.hh`: System constants and helper functions
- `PatternGenerator`: Base class for pattern generation
- `SquarePatternGenerator`: Square pattern implementation
- `PatternMessenger`: UI command interface

### Modified Classes
- `PrimaryGeneratorAction`: Added pattern scanning mode
- GUI: Added "Pattern Scanning" tab with full parameter control

## Tips for BEAMER Integration

1. Start with the dose values from this simulation
2. Use the modulation factors as initial proximity correction
3. Export PSF data for BEAMER's proximity effect correction
4. Adjust based on actual resist response

## Performance Considerations

- Pattern generation is done once at initialization
- Shot positions are pre-calculated for efficiency
- Progress reporting every 1000 shots
- Field transitions logged for debugging

## Future Enhancements

Potential additions:
- More pattern types (circles, polygons)
- Custom dose modulation maps
- Import/export of pattern files
- Advanced field stitching strategies