# PowerShell script to create the modular GUI structure
# Usage: .\create_gui_structure.ps1 -GuiPath "C:\Users\dreec\Geant4Projects\EBeamSim\scripts\gui"

param(
    [Parameter(Mandatory=$true)]
    [string]$GuiPath
)

Write-Host "Creating modular GUI structure at: $GuiPath" -ForegroundColor Green

# Create directory structure
$directories = @(
    "core",
    "widgets", 
    "utils",
    "resources",
    "resources/icons",
    "dialogs"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path "$GuiPath\$dir" | Out-Null
}

Write-Host "Directory structure created!" -ForegroundColor Green

# Create ebl_gui_main.py
$mainContent = @'
#!/usr/bin/env python3
"""
EBL Simulation GUI - Main Entry Point
"""

import sys
import os
from pathlib import Path

# Add the gui directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QIcon

from widgets.material_widget import MaterialWidget
from widgets.beam_widget import BeamWidget
from widgets.simulation_widget import SimulationWidget
from widgets.output_widget import OutputWidget
from widgets.plot_widget import PlotWidget
from core.config import Config
from core.simulation_runner import SimulationRunner

class EBLMainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.simulation_runner = SimulationRunner(self.config)
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("EBL Simulation Control")
        self.setMinimumSize(1200, 800)
        
        # Apply stylesheet
        self.load_stylesheet()
        
        # Create central tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create widgets
        self.material_widget = MaterialWidget(self.config)
        self.beam_widget = BeamWidget(self.config)
        self.simulation_widget = SimulationWidget(self.config, self.simulation_runner)
        self.output_widget = OutputWidget()
        self.plot_widget = PlotWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.material_widget, "Material Properties")
        self.tab_widget.addTab(self.beam_widget, "Beam Parameters")
        self.tab_widget.addTab(self.simulation_widget, "Simulation")
        self.tab_widget.addTab(self.output_widget, "Output Log")
        self.tab_widget.addTab(self.plot_widget, "Visualization")
        
        # Connect signals
        self.simulation_runner.output_signal.connect(self.output_widget.append_output)
        self.simulation_runner.finished_signal.connect(self.on_simulation_finished)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        save_config_action = file_menu.addAction("Save Configuration")
        save_config_action.triggered.connect(self.save_configuration)
        
        load_config_action = file_menu.addAction("Load Configuration")
        load_config_action.triggered.connect(self.load_configuration)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        batch_run_action = tools_menu.addAction("Batch Runner")
        batch_run_action.triggered.connect(self.open_batch_runner)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
    def load_stylesheet(self):
        """Load and apply stylesheet"""
        style_file = Path(__file__).parent / "resources" / "styles.qss"
        if style_file.exists():
            with open(style_file, 'r') as f:
                self.setStyleSheet(f.read())
        else:
            # Default dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #3c3c3c;
                }
                QPushButton {
                    background-color: #007acc;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #005a9e;
                }
            """)
    
    def on_simulation_finished(self, success, message):
        """Handle simulation completion"""
        self.statusBar().showMessage(message)
        if success:
            # Automatically load and plot results
            output_files = self.find_output_files()
            if output_files:
                self.plot_widget.load_data(output_files[0])
    
    def find_output_files(self):
        """Find simulation output files"""
        output_dir = Path(self.config.output_directory)
        return list(output_dir.glob("*.csv"))
    
    def save_configuration(self):
        """Save current configuration to file"""
        self.config.save_to_file()
    
    def load_configuration(self):
        """Load configuration from file"""
        self.config.load_from_file()
        # Update all widgets
        self.material_widget.update_from_config()
        self.beam_widget.update_from_config()
        self.simulation_widget.update_from_config()
    
    def open_batch_runner(self):
        """Open batch runner dialog"""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Info", "Batch runner not implemented yet")
    
    def show_about(self):
        """Show about dialog"""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(self, "About EBL Simulation",
                          "EBL Simulation GUI v2.0\n\n"
                          "A modular interface for Geant4-based\n"
                          "electron beam lithography simulations.")
    
    def load_settings(self):
        """Load application settings"""
        settings = QSettings("EBL", "SimulationGUI")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def save_settings(self):
        """Save application settings"""
        settings = QSettings("EBL", "SimulationGUI")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_settings()
        event.accept()

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("EBL Simulation")
    app.setOrganizationName("EBL Research")
    
    window = EBLMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'@
Set-Content -Path "$GuiPath\ebl_gui_main.py" -Value $mainContent -Encoding UTF8

# Create core/__init__.py
$coreInitContent = @'
"""
Core modules for EBL GUI
"""

from .config import Config
from .simulation_runner import SimulationRunner
from .data_manager import DataManager

__all__ = [
    'Config',
    'SimulationRunner',
    'DataManager'
]
'@
Set-Content -Path "$GuiPath\core\__init__.py" -Value $coreInitContent -Encoding UTF8

# Create core/config.py
$configContent = @'
"""
Configuration management for EBL simulation
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class MaterialConfig:
    """Material configuration"""
    name: str = "Alucone_XPS"
    composition: str = "Al:1,C:5,H:4,O:2"
    density: float = 1.35  # g/cm³
    thickness: float = 30.0  # nm

@dataclass
class BeamConfig:
    """Beam configuration"""
    energy: float = 100.0  # keV
    spot_size: float = 2.0  # nm
    position_x: float = 0.0  # nm
    position_y: float = 0.0  # nm
    position_z: float = 100.0  # nm
    direction_x: float = 0.0
    direction_y: float = 0.0
    direction_z: float = -1.0

@dataclass
class SimulationConfig:
    """Simulation configuration"""
    num_events: int = 100000
    verbose_level: int = 1
    enable_fluorescence: bool = True
    enable_auger: bool = True
    random_seed: int = -1

class Config:
    """Main configuration class"""
    
    # Material presets
    MATERIAL_PRESETS = {
        "PMMA": {"composition": "C:5,H:8,O:2", "density": 1.19},
        "HSQ": {"composition": "Si:1,H:1,O:1.5", "density": 1.4},
        "ZEP": {"composition": "C:11,H:14,O:1", "density": 1.2},
        "Alucone_XPS": {"composition": "Al:1,C:5,H:4,O:2", "density": 1.35},
        "Alucone_Exposed": {"composition": "Al:1,C:5,H:4,O:3", "density": 1.40},
        "Custom": {"composition": "", "density": 1.0}
    }
    
    def __init__(self):
        self.material = MaterialConfig()
        self.beam = BeamConfig()
        self.simulation = SimulationConfig()
        
        # Paths
        self.executable_path = self._find_executable()
        self.output_directory = "data/output"
        self.macro_directory = "macros"
        
        # Load default configuration if exists
        self.config_file = Path.home() / ".ebl_sim" / "config.json"
        if self.config_file.exists():
            self.load_from_file(self.config_file)
    
    def _find_executable(self) -> str:
        """Try to find the EBL simulation executable"""
        possible_paths = [
            Path("../../build/bin/ebl_sim.exe"),
            Path("../../out/build/x64-Release/bin/ebl_sim.exe"),
            Path("C:/Users/dreec/Geant4Projects/EBeamSim/build/bin/ebl_sim.exe"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path.absolute())
        
        return "ebl_sim.exe"  # Default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "material": asdict(self.material),
            "beam": asdict(self.beam),
            "simulation": asdict(self.simulation),
            "paths": {
                "executable": self.executable_path,
                "output": self.output_directory,
                "macros": self.macro_directory
            }
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load configuration from dictionary"""
        if "material" in data:
            self.material = MaterialConfig(**data["material"])
        if "beam" in data:
            self.beam = BeamConfig(**data["beam"])
        if "simulation" in data:
            self.simulation = SimulationConfig(**data["simulation"])
        if "paths" in data:
            self.executable_path = data["paths"].get("executable", self.executable_path)
            self.output_directory = data["paths"].get("output", self.output_directory)
            self.macro_directory = data["paths"].get("macros", self.macro_directory)
    
    def save_to_file(self, filepath: Path = None):
        """Save configuration to JSON file"""
        if filepath is None:
            filepath = self.config_file
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load_from_file(self, filepath: Path = None):
        """Load configuration from JSON file"""
        if filepath is None:
            filepath = self.config_file
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.from_dict(data)
    
    def generate_macro(self) -> str:
        """Generate Geant4 macro from configuration"""
        macro = f"""# EBL Simulation Macro - Generated by GUI
# Material: {self.material.name}

/run/verbose {self.simulation.verbose_level}
/event/verbose {max(0, self.simulation.verbose_level - 1)}
/tracking/verbose {max(0, self.simulation.verbose_level - 2)}

/run/initialize

# Material properties
/det/setResistComposition "{self.material.composition}"
/det/setResistThickness {self.material.thickness} nm
/det/setResistDensity {self.material.density} g/cm3
/det/update

# Physics settings
/process/em/fluo {1 if self.simulation.enable_fluorescence else 0}
/process/em/auger {1 if self.simulation.enable_auger else 0}

# Beam parameters
/gun/particle e-
/gun/energy {self.beam.energy} keV
/gun/position {self.beam.position_x} {self.beam.position_y} {self.beam.position_z} nm
/gun/direction {self.beam.direction_x} {self.beam.direction_y} {self.beam.direction_z}
/gun/beamSize {self.beam.spot_size} nm

# Run simulation
/run/beamOn {self.simulation.num_events}
"""
        return macro
'@
Set-Content -Path "$GuiPath\core\config.py" -Value $configContent -Encoding UTF8

# Create core/simulation_runner.py
$runnerContent = @'
"""
Simulation runner for EBL
"""

import subprocess
import threading
import time
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from typing import Dict, Any

class SimulationRunner(QObject):
    """Handles running the Geant4 simulation"""
    
    # Signals
    output_signal = Signal(str, str)  # message, type
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal(bool, str)  # success, message
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.process = None
        self.thread = None
        self.stop_requested = False
        self.start_time = None
        self.current_event = 0
        
    def start_simulation(self):
        """Start the simulation in a separate thread"""
        if self.thread and self.thread.is_alive():
            return
        
        self.stop_requested = False
        self.thread = threading.Thread(target=self._run_simulation)
        self.thread.start()
        
    def stop_simulation(self):
        """Stop the running simulation"""
        self.stop_requested = True
        if self.process:
            self.process.terminate()
            
    def _run_simulation(self):
        """Run the simulation (called in thread)"""
        try:
            # Create temporary macro file
            macro_path = Path(self.config.macro_directory) / "temp_gui_run.mac"
            macro_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(macro_path, 'w') as f:
                f.write(self.config.generate_macro())
            
            # Build command
            cmd = [self.config.executable_path, str(macro_path)]
            
            # Create output directory
            output_dir = Path(self.config.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Start process
            self.start_time = time.time()
            self.current_event = 0
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=0,
                cwd=str(output_dir)
            )
            
            # Read output
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_requested:
                    break
                    
                line = line.strip()
                if line:
                    # Parse progress
                    if "Event" in line and "#" in line:
                        try:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == "Event" and i+1 < len(parts):
                                    event_str = parts[i+1].replace("#", "")
                                    self.current_event = int(event_str)
                                    self.progress_signal.emit(
                                        self.current_event,
                                        self.config.simulation.num_events
                                    )
                        except:
                            pass
                    
                    # Determine message type
                    msg_type = "info"
                    if "ERROR" in line or "Error" in line:
                        msg_type = "error"
                    elif "WARNING" in line or "Warning" in line:
                        msg_type = "warning"
                    
                    self.output_signal.emit(line, msg_type)
            
            # Wait for process to complete
            return_code = self.process.wait()
            
            if return_code == 0 and not self.stop_requested:
                self.finished_signal.emit(True, "Simulation completed successfully!")
            else:
                self.finished_signal.emit(False, f"Simulation stopped (code: {return_code})")
                
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")
        finally:
            self.process = None
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get current simulation statistics"""
        if not self.start_time:
            return {}
            
        elapsed = time.time() - self.start_time
        rate = self.current_event / elapsed if elapsed > 0 else 0
        
        remaining_events = self.config.simulation.num_events - self.current_event
        remaining_time = remaining_events / rate if rate > 0 else 0
        
        return {
            "events": self.current_event,
            "elapsed_time": elapsed,
            "rate": rate,
            "remaining_time": remaining_time
        }
'@
Set-Content -Path "$GuiPath\core\simulation_runner.py" -Value $runnerContent -Encoding UTF8

# Create core/data_manager.py
$dataManagerContent = @'
"""
Data management for EBL simulation
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

class DataManager:
    """Manages simulation data loading and processing"""
    
    def __init__(self):
        self.current_data = None
        self.metadata = {}
        
    def load_psf_data(self, filepath: str) -> pd.DataFrame:
        """Load PSF data from file"""
        path = Path(filepath)
        
        if path.suffix == '.csv':
            df = pd.read_csv(filepath)
        elif path.suffix == '.dat':
            # Try to read BEAMER format
            df = pd.read_csv(filepath, sep=r'\s+', comment='#', header=None)
            df.columns = ['radius', 'psf'] if len(df.columns) == 2 else df.columns
        else:
            # Try to guess format
            df = pd.read_csv(filepath, sep=None, engine='python')
            
        self.current_data = df
        self._extract_metadata(filepath)
        return df
        
    def _extract_metadata(self, filepath: str):
        """Extract metadata from file"""
        self.metadata = {
            'filename': Path(filepath).name,
            'path': str(filepath),
            'rows': len(self.current_data) if self.current_data is not None else 0
        }
        
    def normalize_psf(self, radius: np.ndarray, psf: np.ndarray) -> np.ndarray:
        """Normalize PSF to unit area"""
        from scipy.integrate import simpson
        area = simpson(psf * 2 * np.pi * radius, radius)
        return psf / area if area > 0 else psf
        
    def calculate_moments(self, radius: np.ndarray, psf: np.ndarray) -> dict:
        """Calculate PSF moments"""
        from scipy.integrate import simpson
        
        # Normalize first
        psf_norm = self.normalize_psf(radius, psf)
        
        # Calculate moments
        r2_psf = radius**2 * psf_norm * 2 * np.pi * radius
        sigma = np.sqrt(simpson(r2_psf, radius))
        
        return {
            'sigma': sigma,
            'fwhm': 2.355 * sigma  # Gaussian approximation
        }
        
    def find_containment_radii(self, radius: np.ndarray, psf: np.ndarray, 
                               fractions: List[float] = [0.5, 0.9, 0.99]) -> dict:
        """Find radii containing specified fractions of deposited energy"""
        from scipy.integrate import cumtrapz
        
        # Calculate cumulative distribution
        cumulative = cumtrapz(psf * 2 * np.pi * radius, radius, initial=0)
        if cumulative[-1] > 0:
            cumulative = cumulative / cumulative[-1]
            
        results = {}
        for frac in fractions:
            idx = np.argmax(cumulative >= frac)
            if idx > 0:
                results[f'R{int(frac*100)}'] = radius[idx]
                
        return results
        
    def export_processed_data(self, filepath: str, data: pd.DataFrame):
        """Export processed data"""
        path = Path(filepath)
        
        if path.suffix == '.csv':
            data.to_csv(filepath, index=False)
        elif path.suffix == '.xlsx':
            data.to_excel(filepath, index=False)
        else:
            # Default to CSV
            data.to_csv(filepath, index=False)
'@
Set-Content -Path "$GuiPath\core\data_manager.py" -Value $dataManagerContent -Encoding UTF8

# Create widgets/__init__.py
$widgetsInitContent = @'
"""
Widget modules for EBL GUI
"""

from .material_widget import MaterialWidget
from .beam_widget import BeamWidget
from .simulation_widget import SimulationWidget
from .output_widget import OutputWidget
from .plot_widget import PlotWidget

__all__ = [
    'MaterialWidget',
    'BeamWidget',
    'SimulationWidget',
    'OutputWidget',
    'PlotWidget'
]
'@
Set-Content -Path "$GuiPath\widgets\__init__.py" -Value $widgetsInitContent -Encoding UTF8

Write-Host "`nCreating widget files..." -ForegroundColor Green

# I'll continue with the widget files in the next part due to length...
# For now, let's create placeholder files

$widgetFiles = @(
    "material_widget.py",
    "beam_widget.py", 
    "simulation_widget.py",
    "output_widget.py",
    "plot_widget.py"
)

foreach ($file in $widgetFiles) {
    $placeholder = @"
"""
Widget implementation
See separate file for full content
"""
"@
    Set-Content -Path "$GuiPath\widgets\$file" -Value $placeholder -Encoding UTF8
}

# Create utils/__init__.py
$utilsInitContent = @'
"""
Utility modules for EBL GUI
"""
'@
Set-Content -Path "$GuiPath\utils\__init__.py" -Value $utilsInitContent -Encoding UTF8

# Create resources/styles.qss
$stylesContent = @'
/* EBL Simulation GUI Stylesheet */

/* Main Window */
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #555555;
    background-color: #3c3c3c;
}

QTabBar::tab {
    background-color: #555555;
    color: #ffffff;
    padding: 8px 16px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #007acc;
}

QTabBar::tab:hover {
    background-color: #666666;
}

/* Group Boxes */
QGroupBox {
    font-weight: bold;
    border: 2px solid #555555;
    border-radius: 5px;
    margin-top: 1ex;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

/* Buttons */
QPushButton {
    background-color: #007acc;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #005a9e;
}

QPushButton:pressed {
    background-color: #004578;
}

QPushButton:disabled {
    background-color: #555555;
    color: #888888;
}

/* Input Fields */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 5px;
    color: #ffffff;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #007acc;
}

/* Text Areas */
QTextEdit, QPlainTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #555555;
    color: #d4d4d4;
    font-family: 'Consolas', 'Monaco', monospace;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #555555;
    border-radius: 3px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #007acc;
    border-radius: 2px;
}

/* Labels */
QLabel {
    color: #ffffff;
}

/* Status Bar */
QStatusBar {
    background-color: #007acc;
    color: white;
}

/* Scroll Bars */
QScrollBar:vertical {
    background-color: #2b2b2b;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #666666;
}
'@
Set-Content -Path "$GuiPath\resources\styles.qss" -Value $stylesContent -Encoding UTF8

Write-Host "`nGUI structure created successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Download the complete widget files (I'll provide these next)"
Write-Host "2. Place them in the appropriate directories"
Write-Host "3. Install required Python packages: pip install PySide6 matplotlib pandas numpy scipy"
Write-Host "4. Run the GUI: python ebl_gui_main.py"