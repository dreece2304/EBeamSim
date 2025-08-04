# Proximity Effect Visualization Guide

This guide explains the enhanced pattern visualization features that show proximity effects in e-beam lithography.

## Overview

The Pattern Visualization tab now includes advanced proximity effect simulation to help you:
- Visualize dose distribution beyond pattern boundaries
- Calculate effective dose including forward and backscatter
- Optimize dose modulation parameters
- Determine appropriate array spacing

## New Visualization Modes

### 1. **Effective Dose Map**
Shows the actual dose distribution including proximity effects:
- Calculates dose using two-Gaussian PSF model
- Shows dose in surrounding resist areas
- Includes threshold contour for resist development
- Adjustable view margin to see dose tails

### 2. **Dose Profile**
Cross-sectional dose plots through pattern center:
- X and Y profiles showing dose distribution
- Pattern boundaries marked
- Dose threshold line
- Useful for understanding edge effects

### 3. **Enhanced Dose Map**
Improved dose visualization:
- Shows surrounding area beyond pattern
- Uses actual exposure grid resolution
- Zero dose background clearly visible
- Pattern boundary overlay

## Proximity Effect Parameters

### Point Spread Function (PSF) Model
The system uses a two-Gaussian model:
```
PSF(r) = α/(2πσf²) * exp(-r²/2σf²) + β/(2πσb²) * exp(-r²/2σb²)
```

### Adjustable Parameters:

**Forward Scatter:**
- **α (alpha)**: Forward scatter ratio (typically ~1.0)
- **σf (sigma_f)**: Forward scatter range in nm (typically 10-50 nm)

**Backscatter:**
- **β (beta)**: Backscatter ratio (typically 2-5)
- **σb (sigma_b)**: Backscatter range in μm (typically 1-10 μm)

**Dose Threshold:**
- Development threshold (typically 1.0 = 100% of base dose)

### View Margin:
- How far beyond pattern to calculate/display dose
- Default: 5 μm (captures most backscatter)

## Using for Proximity Correction

### 1. **Single Pattern Analysis**
1. Create a single square pattern
2. Switch to "Effective Dose" view
3. Adjust PSF parameters to match your resist/substrate
4. Observe dose at pattern edges vs center
5. Adjust edge/corner modulation until uniform effective dose

### 2. **Array Spacing Optimization**
1. Create array pattern (e.g., 3×3)
2. View "Effective Dose" with large margin
3. Check dose between patterns
4. Increase array pitch until inter-pattern dose < threshold
5. This gives minimum spacing without bridging

### 3. **Dose Matrix Testing**
1. Create array with different base doses
2. Use varying modulation factors
3. Compare effective dose maps
4. Find optimal dose for isolated vs dense features

## Typical PSF Parameters

**HSQ on Silicon (100 keV):**
- α = 1.0, σf = 20 nm
- β = 3.0, σb = 5 μm

**PMMA on Silicon (100 keV):**
- α = 1.0, σf = 30 nm
- β = 4.0, σb = 8 μm

**High-Z Substrate (Gold):**
- α = 1.0, σf = 20 nm
- β = 8.0, σb = 3 μm

## Workflow Example

### Finding Optimal Dose Modulation:
1. Set pattern: 1 μm square, shot pitch 4
2. Set base dose: 400 μC/cm²
3. Initial modulation: Interior 100%, Edge 90%, Corner 80%
4. Generate preview → "Effective Dose"
5. Check dose uniformity across pattern
6. Adjust edge/corner modulation
7. Iterate until effective dose is uniform

### Determining Array Spacing:
1. Create 3×3 array of 500 nm squares
2. Start with 2 μm pitch
3. View "Effective Dose" with 10 μm margin
4. Check dose between patterns
5. If > threshold, increase pitch
6. Find minimum pitch where inter-pattern dose < threshold

## Tips

- Start with literature PSF values for your resist/substrate
- Forward scatter mainly affects fine features (<100 nm)
- Backscatter determines minimum pattern spacing
- Use "Dose Profile" to quantify edge effects
- Export effective dose maps for documentation

## Integration with Simulation

The visualization parameters help you:
1. Set appropriate dose modulation in Pattern Scanning tab
2. Choose correct base dose for your resist
3. Determine if pattern fracturing is needed
4. Predict proximity effects before fabrication

These visualization tools complement the Monte Carlo simulation by providing fast, interactive proximity effect preview before running full simulations.