# GUI Reorganization Plan

## Current Tab Structure Analysis

### Current Tabs (7 tabs):
1. **Resist Properties** - Material composition, thickness, density
2. **Beam Parameters** - Energy, position, direction, size
3. **Pattern Scanning** - Pattern type, JEOL parameters, dose modulation
4. **Simulation** - Run controls, physics settings, events
5. **Output Log** - Console output from simulation
6. **1D PSF Visualization** - Plot PSF curves
7. **2D Visualization** - Depth-radius plots
8. **Pattern Visualization** - Pattern preview with proximity effects (hidden 8th tab)

### Problems with Current Organization:
- Pattern-related controls split between tabs 3 and 8
- PSF generation mixed with pattern simulation
- Visualization split across 3 different tabs
- Unclear workflow progression
- Too many tabs for simple tasks

## Proposed Reorganization

### New Tab Structure (6 main tabs + 1 output):

#### 1. **Sample & Beam Setup**
Combine current "Resist Properties" and "Beam Parameters"
- **Sample Section:**
  - Resist composition
  - Resist thickness
  - Resist density
  - Substrate material
- **Beam Section:**
  - Beam energy
  - Beam size
  - Position (usually default)
  - Direction (usually default)

#### 2. **PSF Generation** 
Single spot simulation for creating PSF model
- **Mode:** Single Spot
- **Events:** Number of electrons to simulate
- **Run Button:** Generate PSF
- **Quick View:** Show resulting PSF curve
- **Output:** psf_data.csv for use in patterns

#### 3. **Pattern Design**
All pattern-related controls in one place
- **Pattern Type:** square, array, etc.
- **Pattern Parameters:** size, center
- **JEOL Settings:** EOS mode, shot pitch, current, dose
- **Array Settings:** (shown only for array type)
- **Pattern Preview:** Simple geometric view

#### 4. **Proximity Analysis**
Dose modulation and correction
- **Load PSF:** From file or use theoretical
- **PSF Parameters:** α, β, σf, σb display
- **Dose Modulation:**
  - Interior: 1.0 (reference)
  - Edge: 0.85 (typical)
  - Corner: 0.75 (typical)
  - Presets: No correction, Light, Medium, Heavy
- **Preview:** Show effective dose with current settings
- **Compare:** Side-by-side corrected vs uncorrected

#### 5. **Run Simulation**
Simplified simulation controls
- **Simulation Mode:**
  - ○ PSF Generation (single spot)
  - ○ Pattern Simulation
- **Physics Settings:** Fluorescence, Auger
- **Advanced:** Verbosity, random seed (collapsible)
- **Big Run Button**
- **Progress Bar**
- **Status Messages**

#### 6. **Results & Visualization**
Combined visualization tab
- **View Mode Selector:**
  - 1D PSF Plot
  - 2D Depth Profile
  - Pattern Dose Map
  - Proximity Comparison
- **Load Data:** Auto-load latest or browse
- **Export:** Save plots, data

#### 7. **Output Log** (keep as is)
- Console output
- Error messages
- Clear button

## Workflow Improvements

### Clear 3-Step Process:

#### Step 1: Setup & Generate PSF
1. Go to "Sample & Beam Setup" → Configure materials
2. Go to "PSF Generation" → Run single spot simulation
3. See PSF curve immediately

#### Step 2: Design Pattern with Correction
1. Go to "Pattern Design" → Set up pattern
2. Go to "Proximity Analysis" → Load PSF, adjust doses
3. Preview the corrected pattern

#### Step 3: Run and Analyze
1. Go to "Run Simulation" → Select Pattern mode → Run
2. Go to "Results" → View all outputs in one place

### Key Improvements:
- **Logical flow:** Setup → PSF → Pattern → Correction → Run → Results
- **Related controls together:** All pattern stuff in one tab
- **Clear separation:** PSF generation vs Pattern simulation
- **One-stop visualization:** All plots in one tab with mode selector
- **Workflow guidance:** Tab order matches typical workflow

### Visual Cues to Add:
- Number badges on tabs (1, 2, 3...) to show workflow order
- "Next Step →" buttons that switch to appropriate tab
- Status indicators showing what's been completed
- Disable tabs that aren't ready yet (e.g., can't do Proximity Analysis without PSF)

This reorganization maintains all functionality while making the workflow much clearer!