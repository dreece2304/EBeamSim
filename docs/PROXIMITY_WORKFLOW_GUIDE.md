# Complete Proximity Effect Analysis Workflow

This guide walks you through the complete process of analyzing proximity effects for your e-beam patterns.

## Overview: Two Complementary Approaches

1. **Quick Preview (GUI Visualization)** - Theoretical calculation using PSF model
2. **Full Simulation (Monte Carlo)** - Actual electron scattering physics

Both give you proximity effect data - use the GUI for quick optimization, then verify with simulation.

## Step-by-Step Workflow

### Phase 1: Quick Pattern Preview (5 seconds)

1. **Open EBL GUI** → Go to **"Pattern Scanning"** tab
2. **Configure Your Test Pattern**:
   ```
   Pattern Mode: ON
   Pattern Type: square
   Pattern Size: 1.0 μm
   Center: (0, 0)
   
   JEOL Parameters:
   - EOS Mode: Mode 3
   - Shot Pitch: 4
   - Beam Current: 2.0 nA
   - Base Dose: 400 μC/cm²
   
   Dose Modulation (start uniform):
   - Interior: 1.0
   - Edge: 1.0
   - Corner: 1.0
   ```

3. **Switch to "Pattern Visualization"** tab
4. **Click "Generate Pattern Preview"**
5. **Select "Effective Dose"** from dropdown
6. **Adjust View Margin** to 10-20 μm

**What You See**: Theoretical dose distribution showing your square and surrounding dose from scatter

### Phase 2: Run Full Simulation (5 minutes)

1. **Stay in "Pattern Scanning"** tab with same settings
2. **Go to "Simulation"** tab
3. **Click "Generate Macro"** → **"Run Simulation"**
4. The GUI automatically calculates the correct number of events
5. Wait for simulation to complete

**Output Files Created**:
- `psf_data.csv` - Actual PSF from Monte Carlo
- `simulation_summary.txt` - Statistics
- `psf_beamer.txt` - BEAMER-compatible PSF

### Phase 3: Compare and Analyze

1. **In "1D PSF Visualization"** tab:
   - Click "Load PSF Data" → Select your `psf_data.csv`
   - This shows the ACTUAL proximity function from simulation
   - Compare with your theoretical preview

2. **What to Look For**:
   - **Peak at center**: Direct exposure dose
   - **Shoulder 10-100nm**: Forward scatter
   - **Long tail 1-10μm**: Backscatter
   - **Total integrated dose**: Should ≈ your base dose

3. **Extract PSF Parameters**:
   From the 1D PSF plot, estimate:
   - α (forward/backscatter ratio at ~50nm)
   - β (backscatter strength at ~5μm)
   - σf (forward scatter range where dose drops to ~37%)
   - σb (backscatter range where dose drops to ~37%)

### Phase 4: Optimize Dose Modulation

1. **Return to "Pattern Visualization"**
2. **Update PSF parameters** with values from simulation
3. **Switch display to "Dose Profile"**
4. **Observe**:
   - Edge dose is higher than center (needs reduction)
   - Corner dose is highest (needs most reduction)

5. **Adjust in "Pattern Scanning"**:
   ```
   Interior: 1.0 (reference)
   Edge: 0.85-0.9 (reduce by 10-15%)
   Corner: 0.7-0.8 (reduce by 20-30%)
   ```

6. **Regenerate preview** to see if dose is now uniform

### Phase 5: Test Array Spacing

1. **Change Pattern Type** to `array`
2. **Set Array Parameters**:
   ```
   Pattern Size: 0.5 μm (individual squares)
   Array Size: 3×3
   Pitch X/Y: Start with 2.0 μm
   ```

3. **View "Effective Dose"** with 15 μm margin
4. **Check dose between patterns**:
   - If > threshold → increase pitch
   - If << threshold → can decrease pitch

5. **Find optimal spacing** where inter-pattern dose ≈ 0.1-0.2

## Complete Example Workflow

### Testing 1μm Square on HSQ/Silicon:

1. **Preview** (30 seconds):
   - Set up 1μm square pattern
   - View effective dose
   - See backscatter extends ~10μm

2. **Simulate** (5 minutes):
   - Run with auto-calculated shots
   - Get actual PSF data

3. **Analyze PSF** (2 minutes):
   - Load psf_data.csv
   - Measure: α≈1, β≈3, σf≈20nm, σb≈5μm

4. **Optimize** (2 minutes):
   - Update GUI PSF parameters
   - Check dose profiles
   - Set edge=0.9, corner=0.8

5. **Verify** (5 minutes):
   - Run new simulation with modulation
   - Check dose uniformity improved

## Tips for Success

1. **Start Simple**: Single square, uniform dose
2. **Use Both Tools**: 
   - GUI for quick "what if" scenarios
   - Simulation for accurate physics
3. **Save PSF Data**: Build library for different resists/substrates
4. **Document Settings**: Screenshot your optimized parameters

## Quick Reference - File Locations

After simulation, find your data in:
```
cmake-build-release/bin/output/
├── psf_data.csv          # Plot this for actual PSF
├── psf_beamer.txt        # Use in BEAMER
├── simulation_summary.txt # Check statistics
└── psf_E[energy]keV_beam[size]nm_resist[thickness]nm_[material]_run[###].csv
```

## Troubleshooting

**Dose too high at edges?**
- Reduce edge/corner modulation
- Check if σb is correct for your substrate

**Can't see backscatter?**
- Increase view margin to 20-30 μm
- Increase β parameter
- Check if substrate has high-Z materials

**PSF doesn't match theory?**
- Run more events (100k+ for smooth PSF)
- Check resist parameters are correct
- Verify beam energy matches your system

This workflow gives you both quick theoretical preview AND accurate Monte Carlo verification!