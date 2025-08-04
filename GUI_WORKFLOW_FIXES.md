# GUI Workflow Fixes Needed

## Current Problems:

### 1. Pattern Preview Crash
The "Generate Pattern Preview" button is crashing, likely because:
- Missing imports or undefined methods
- The `calculate_fields` method might not exist
- Widget references might be incorrect after all the edits

### 2. Redundant Workflow
Currently you have to:
1. Set up pattern parameters
2. Run simulation (which generates the pattern internally)
3. Go to another tab
4. Press "Generate Pattern Preview" to recreate the same pattern
5. This is redundant and confusing!

### 3. No Data Flow
The simulation doesn't save pattern data, so:
- Pattern shots are generated in C++ but thrown away
- GUI has to recalculate everything
- No way to verify what pattern was actually simulated

## Proposed Fixes:

### Fix 1: Remove "Generate Pattern Preview" Button
Instead, automatically show pattern when:
- User changes pattern parameters in Pattern Scanning tab
- Simulation completes (load the actual simulated pattern)

### Fix 2: Save Pattern Data from Simulation
Add to C++ RunAction:
```cpp
void RunAction::SavePatternData() {
    // Save shot positions, ranks, fields
    // Output: pattern_data.csv with x,y,rank,field
}
```

### Fix 3: Simplify Pattern Visualization Tab
Current "Pattern Visualization" tab is trying to do too much:
- Pattern preview (geometry)
- PSF parameters  
- Proximity effect calculation
- Dose visualization

Should be split into:
- **Pattern Preview** (in Pattern Scanning tab - show immediately)
- **Proximity Analysis** (separate tab for PSF + correction)

### Fix 4: Auto-Load Results
When simulation finishes:
1. Automatically load PSF data
2. Automatically load pattern data
3. Switch to results tab
4. Show what was actually simulated

## Immediate Band-Aid Fix:

To stop the crash, check if these widgets exist in Pattern Scanning tab:
- `self.eos_mode_combo`
- `self.pattern_type_combo`
- `self.pattern_size_spin`
- `self.pattern_center_x`
- `self.pattern_center_y`
- `self.array_nx_spin`
- `self.array_ny_spin`
- `self.array_pitch_x_spin`
- `self.array_pitch_y_spin`

And ensure `calculate_fields` method exists.

## Better Solution:

Merge pattern preview into Pattern Scanning tab:
1. Remove separate Pattern Visualization tab
2. Add small preview panel to Pattern Scanning tab
3. Update preview automatically when parameters change
4. No button needed!

This would make the workflow much more intuitive.