# Understanding the Simulation Workflow

## The Two Systems Explained

### 1. Pattern Visualization Tab (Mathematical Preview)
**What it does:**
- Uses a mathematical formula (two-Gaussian PSF model)
- Calculates proximity effects instantly using convolution
- NO actual electron simulation
- Just for quick preview and parameter testing

**When it says "Calculating proximity effects..."**
- It's doing mathematical convolution: Pattern ⊗ PSF
- Takes seconds because it's just math
- Uses the PSF parameters you set (α, β, σf, σb)

### 2. Simulation Tab (Real Physics)
**What it does:**
- Runs actual Geant4 Monte Carlo simulation
- Tracks individual electrons through materials
- Records where energy is deposited
- Creates real PSF data from physics

**Should take:**
- Small pattern (1μm): 1-5 minutes
- Large pattern (10μm): 5-30 minutes
- If instant: Something is wrong!

## Why Was Your Simulation Finishing Instantly?

The command order was wrong! The fixed order is now:

```
1. Material settings (/det/...)
2. Physics settings (/process/...)  
3. /run/initialize
4. Beam settings (/gun/...)
5. Pattern settings (/pattern/...)
6. /pattern/generate
7. /pattern/beamMode pattern
8. /run/beamOn -1
```

The old order had `/run/initialize` too early, causing later commands to fail.

## Complete Workflow for Proximity Effect Analysis

### Step 1: Quick Preview (No Simulation)
1. **Pattern Scanning tab:**
   - Configure your pattern
   - Set dose modulation (1.0 = no correction)

2. **Pattern Visualization tab:**
   - Click "Generate Pattern Preview"
   - Select "Effective Dose"
   - See instant mathematical preview
   - Adjust parameters as needed

### Step 2: Run Real Simulation
1. **Simulation tab:**
   - Click "Generate Macro"
   - Click "Run Simulation"
   - WAIT for progress (should see "Processing event X")
   - Should take minutes, not seconds!

2. **Check output:**
   - Look for psf_data.csv in output folder
   - Check simulation_summary.txt for statistics

### Step 3: Use Real Data
1. **Pattern Visualization tab:**
   - Click "Load PSF from Simulation"
   - This replaces theoretical PSF with real data
   - Now preview uses actual physics results!

### Step 4: Compare Corrected vs Uncorrected
1. **Select "Correction Comparison" view**
2. **See 4 panels:**
   - Top: Without correction (uniform dose)
   - Bottom: With correction (if enabled)

## Key Points to Remember

- **Pattern Visualization** = Just math, instant preview
- **Simulation** = Real physics, takes time
- **"Calculating proximity effects"** in visualization = Mathematical convolution, NOT simulation
- **If simulation finishes instantly** = Error, check the log!

## Testing Without Correction

To see uncorrected proximity effects:
1. Set all dose modulations to 1.0
2. Run simulation
3. View "Effective Dose" - you'll see edge/corner brightening
4. This shows why proximity correction is needed!