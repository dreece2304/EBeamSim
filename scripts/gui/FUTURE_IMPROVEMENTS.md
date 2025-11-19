# Future GUI Improvements - TODO List

**Last Updated:** 2025-11-19
**Status:** Deferred for future implementation

This document tracks planned improvements that were identified during the Phase 1-4 refactoring but deferred for later implementation.

---

## 🎯 **HIGH PRIORITY - Phase 3 Remaining Items**

### **Phase 3.2: Comprehensive Tooltips** ⭐⭐⭐
**Impact:** High | **Effort:** Medium | **Priority:** P1

Add tooltips to ~90 input fields throughout the application.

**What to Add:**
- Acceptable value ranges
- Units (keV, nm, g/cm³, etc.)
- Typical values for EBL
- What the parameter does
- Examples of good/bad values

**Example Implementation:**
```python
self.energy_spin.setToolTip(
    "Electron beam energy in keV\n"
    "Typical range: 50-125 keV\n"
    "Higher energy = deeper penetration"
)

self.beam_size_spin.setToolTip(
    "FWHM beam diameter in nm\n"
    "Typical range: 2-10 nm\n"
    "Smaller = better resolution, harder to achieve"
)

self.events_spin.setToolTip(
    "Number of electrons to simulate\n"
    "Quick test: 10,000\n"
    "Standard PSF: 100,000\n"
    "High quality: 1,000,000+"
)
```

**Files to Modify:**
- `ebl_gui.py` - All input widgets in beam, resist, simulation tabs
- `widgets/enhanced_beam_widget.py`
- `widgets/resist_properties_widget.py`

**Estimated Time:** 3-4 hours

---

### **Phase 3.3: Enhanced Status Messages with ETA** ⭐⭐⭐
**Impact:** High | **Effort:** Low | **Priority:** P1

Show detailed progress with estimated time remaining during simulations.

**Current:**
```
Simulation running...
```

**Target:**
```
Simulation: 45,230/100,000 events (45.2%) - Est. 3m 45s remaining
```

**Implementation:**
1. Track simulation start time
2. Calculate events/second rate
3. Estimate remaining time based on rate
4. Update status bar every second with detailed info

**Code Location:**
- `ebl_gui.py:update_progress()` method (line ~3760)
- Add ETA calculation in SimulationWorker

**Estimated Time:** 2-3 hours

---

### **Phase 3.4: Progress Indicators for Long Operations** ⭐⭐
**Impact:** Medium | **Effort:** Low | **Priority:** P2

Add `QProgressDialog` for operations that block the UI.

**Operations Needing Progress:**
- CSV file loading (large files)
- BEAMER conversion
- PSF comparison calculations
- 2D data visualization generation

**Example Implementation:**
```python
def load_large_csv(self, file_path):
    progress = QProgressDialog("Loading CSV data...", "Cancel", 0, 100, self)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(500)  # Show after 500ms

    # Update progress during loading
    for i, chunk in enumerate(chunks):
        if progress.wasCanceled():
            break
        # Process chunk
        progress.setValue(int((i / total_chunks) * 100))
```

**Files to Modify:**
- `ebl_gui.py` - File loading operations
- `core/file_manager.py` - CSV parsing
- BEAMER conversion methods

**Estimated Time:** 4-5 hours

---

### **Phase 3.5: Optimized Defaults & Preset System** ⭐⭐⭐
**Impact:** High | **Effort:** Medium | **Priority:** P1

Better default values and a preset dropdown for common scenarios.

**Current Issues:**
- Some defaults not realistic for typical use
- Users must manually configure for common cases

**Preset System Design:**
```python
PRESETS = {
    "Quick Test": {
        "events": 10000,
        "energy": 100.0,
        "beam_size": 5.0,
        "resist_thickness": 30.0,
        "description": "Fast test run for debugging"
    },
    "Standard PSF": {
        "events": 100000,
        "energy": 100.0,
        "beam_size": 5.0,
        "resist_thickness": 30.0,
        "description": "Standard PSF simulation"
    },
    "High Quality PSF": {
        "events": 1000000,
        "energy": 100.0,
        "beam_size": 2.0,
        "resist_thickness": 30.0,
        "description": "High-quality PSF for production"
    },
    "Low Energy Study": {
        "events": 100000,
        "energy": 30.0,
        "beam_size": 5.0,
        "resist_thickness": 15.0,
        "description": "Low-energy resist characterization"
    }
}
```

**UI Addition:**
- Dropdown at top of Simulation tab: "Preset: [Quick Test ▼]"
- Apply button loads all parameters
- Save Custom Preset button

**Files to Modify:**
- `ebl_gui.py` - Add preset dropdown and logic
- `core/constants.py` - Add PRESETS dictionary

**Estimated Time:** 5-6 hours

---

### **Phase 3.6: Persistent Settings & Recent Files** ⭐⭐
**Impact:** Medium | **Effort:** Medium | **Priority:** P2

Remember user preferences across sessions.

**Settings to Persist:**
1. **Window geometry** - Size and position
2. **Window state** - Splitter positions, current tab
3. **Recent files** - Last 10 simulation outputs/configs
4. **Last used parameters** - Restore last simulation settings
5. **Last directory** - For file dialogs

**Implementation:**

Already partially done in `load_settings()` and `save_settings()`. Need to expand:

```python
def save_settings(self):
    # Already saves: geometry, executable_path, geant4_path

    # Add:
    self.settings.setValue("windowState", self.saveState())
    self.settings.setValue("currentTab", self.tab_widget.currentIndex())

    # Recent files (as list)
    self.settings.setValue("recentFiles", self.recent_files[:10])

    # Last used parameters
    params = {
        "energy": self.energy_spin.value(),
        "beam_size": self.beam_size_spin.value(),
        # ... etc
    }
    self.settings.setValue("lastParameters", params)

def load_settings(self):
    # Restore all settings
    if self.settings.contains("windowState"):
        self.restoreState(self.settings.value("windowState"))

    # Recent files menu
    recent = self.settings.value("recentFiles", [])
    self.populate_recent_files_menu(recent)
```

**Recent Files Menu:**
- Add to File menu
- Show last 10 files with full paths
- Click to open
- Clear Recent Files option

**Files to Modify:**
- `ebl_gui.py` - Expand save_settings(), load_settings()
- Add recent files menu to create_menu_bar()

**Estimated Time:** 4-5 hours

---

## 💡 **MEDIUM PRIORITY - Nice to Have**

### **Confirmation Dialogs for Destructive Actions** ⭐
**Impact:** Low-Medium | **Effort:** Low | **Priority:** P3

Add confirmation before:
- Clearing output log
- Overwriting existing files
- Resetting parameters to defaults

**Example:**
```python
def clear_log(self):
    reply = QMessageBox.question(
        self, "Confirm Clear",
        "Clear all output? This cannot be undone.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No  # Default to No
    )
    if reply == QMessageBox.Yes:
        self.output_text.clear()
```

**Estimated Time:** 1-2 hours

---

### **Visual State Indicators (Color-Coded Buttons)** ⭐
**Impact:** Medium | **Effort:** Low | **Priority:** P3

Use colors to show button states more clearly.

**Color Scheme:**
- **Idle:** Blue (#007acc)
- **Working:** Orange/Yellow (#ff9800)
- **Success:** Green (#4caf50)
- **Error:** Red (#f44336)

**Implementation:**
Currently using `StatusButton` widget. Enhance with state colors:

```python
class StatusButton(QPushButton):
    def set_state(self, state: str):
        colors = {
            'idle': '#007acc',
            'working': '#ff9800',
            'success': '#4caf50',
            'error': '#f44336'
        }
        self.setStyleSheet(f"background-color: {colors.get(state, '#007acc')}")
```

**Files to Modify:**
- `widgets/common/status_button.py` (if exists) or `ebl_gui.py`

**Estimated Time:** 2-3 hours

---

### **Drag-and-Drop File Loading** ⭐
**Impact:** Low-Medium | **Effort:** Medium | **Priority:** P3

Drag CSV/data files onto window to load them.

**Implementation:**
```python
def __init__(self):
    # ... existing code ...
    self.setAcceptDrops(True)

def dragEnterEvent(self, event):
    if event.mimeData().hasUrls():
        event.acceptProposedAction()

def dropEvent(self, event):
    for url in event.mimeData().urls():
        file_path = url.toLocalFile()
        if file_path.endswith('.csv'):
            self.load_csv_file(file_path)
        elif file_path.endswith('.json'):
            self.load_configuration_file(file_path)
```

**Estimated Time:** 2-3 hours

---

### **Export Configuration to Python Script** ⭐
**Impact:** Low | **Effort:** Medium | **Priority:** P3

Generate a Python script that reproduces current settings.

**Use Cases:**
- Batch processing
- Documentation
- Reproducibility
- Sharing configurations

**Example Output:**
```python
#!/usr/bin/env python3
# EBL Simulation Configuration
# Generated: 2025-11-19 10:30:00

from ebl_sim import Simulation

sim = Simulation()
sim.set_beam_energy(100.0)  # keV
sim.set_beam_size(5.0)  # nm
sim.set_resist("AluconeXPS", thickness=30.0, density=1.35)
sim.set_events(100000)
sim.run()
```

**Estimated Time:** 4-5 hours

---

## 🌙 **LOW PRIORITY - Future Enhancements**

### **Dark/Light Theme Toggle**
**Impact:** Low | **Effort:** Medium | **Priority:** P4

Currently hardcoded dark theme. Add theme selector.

**Options:**
- Dark theme (current)
- Light theme
- Auto (follow system)

**Implementation:**
- Create QSS files for each theme
- Add Settings option
- Apply theme dynamically

**Estimated Time:** 6-8 hours

---

### **Simulation History Log**
**Impact:** Low | **Effort:** High | **Priority:** P4

Track all simulations run with parameters and results.

**Features:**
- New "History" tab
- Table of past runs with: date, parameters, result files, status
- Re-run with same parameters button
- Compare results button
- Export history to CSV

**Storage:**
- SQLite database or JSON file
- Store in user config directory

**Estimated Time:** 10-12 hours

---

## 📊 **Summary**

### **Recommended Next Steps (in order):**
1. **Phase 3.2: Tooltips** - Highest user impact for effort
2. **Phase 3.5: Presets** - Makes common tasks much easier
3. **Phase 3.3: Enhanced Status with ETA** - Better user feedback
4. **Phase 3.6: Persistent Settings** - Quality of life improvement
5. **Phase 3.4: Progress Indicators** - Polish for long operations

### **Total Estimated Time:**
- **High Priority Items:** 18-23 hours
- **Medium Priority Items:** 7-10 hours
- **Low Priority Items:** 16-20 hours
- **Grand Total:** 41-53 hours

---

## 📝 **Notes**

- All estimates assume familiarity with the codebase
- Testing time not included in estimates
- Some items may be quicker due to existing infrastructure
- Can be done incrementally, one item at a time
- Each item should be a separate git commit

**Implementation Strategy:**
Work on these in priority order, testing thoroughly after each addition. Commit individually so features can be rolled back if needed.

---

**Created:** 2025-11-19
**Author:** Claude Code
**Status:** Ready for implementation when needed
