#!/usr/bin/env python3
"""
ebl_gui_simple.py - Simplified EBL Simulation GUI

Three clear tabs:
1. PSF Generation - Single spot simulation to create PSF model
2. Pattern Simulation - Simulate actual patterns
3. Proximity Analysis - Apply PSF to patterns and visualize effects
"""

import sys
import os
import subprocess
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QTextEdit, QGroupBox, QGridLayout, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class SimulationWorker(QThread):
    """Worker thread for running simulations"""
    output = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, exe_path, macro_path, working_dir):
        super().__init__()
        self.exe_path = exe_path
        self.macro_path = macro_path
        self.working_dir = working_dir
        self.process = None
        
    def run(self):
        """Run the simulation"""
        try:
            self.process = subprocess.Popen(
                [self.exe_path, self.macro_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=self.working_dir
            )
            
            event_count = 0
            for line in self.process.stdout:
                self.output.emit(line.rstrip())
                
                # Track progress
                if "Processing event" in line:
                    event_count += 1
                    if event_count % 100 == 0:
                        self.progress.emit(event_count)
                elif "Events simulated:" in line:
                    # Extract final count
                    parts = line.split(":")
                    if len(parts) > 1:
                        try:
                            total = int(parts[1].strip())
                            self.progress.emit(total)
                        except:
                            pass
            
            self.process.wait()
            success = self.process.returncode == 0
            self.finished.emit(success, "Simulation completed" if success else "Simulation failed")
            
        except Exception as e:
            self.finished.emit(False, str(e))

class SimpleEBLGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EBL Simulation - Simple Interface")
        self.setGeometry(100, 100, 1200, 800)
        
        # Find executable
        self.exe_path = self.find_executable()
        if not self.exe_path:
            QMessageBox.critical(self, "Error", "Cannot find ebl_sim executable!")
            sys.exit(1)
        
        # Working directory
        self.working_dir = str(Path.cwd())
        
        # Initialize UI
        self.init_ui()
        
    def find_executable(self):
        """Find the simulation executable"""
        exe_name = "ebl_sim.exe" if os.name == 'nt' else "ebl_sim"
        search_paths = [
            Path("cmake-build-release/bin") / exe_name,
            Path("cmake-build-release") / exe_name,
            Path("build/bin") / exe_name,
            Path("build") / exe_name,
        ]
        
        for path in search_paths:
            if path.exists():
                return str(path.absolute())
        return None
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: PSF Generation
        self.psf_tab = self.create_psf_tab()
        self.tabs.addTab(self.psf_tab, "1. PSF Generation")
        
        # Tab 2: Pattern Simulation
        self.pattern_tab = self.create_pattern_tab()
        self.tabs.addTab(self.pattern_tab, "2. Pattern Simulation")
        
        # Tab 3: Proximity Analysis
        self.proximity_tab = self.create_proximity_tab()
        self.tabs.addTab(self.proximity_tab, "3. Proximity Analysis")
        
        layout.addWidget(self.tabs)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
    
    def create_psf_tab(self):
        """Create PSF generation tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Generate Point Spread Function from single spot simulation.\n"
            "This creates the PSF model needed for proximity effect analysis."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Parameters
        params_group = QGroupBox("Simulation Parameters")
        params_layout = QGridLayout()
        
        # Beam energy
        params_layout.addWidget(QLabel("Beam Energy (keV):"), 0, 0)
        self.psf_energy = QSpinBox()
        self.psf_energy.setRange(1, 300)
        self.psf_energy.setValue(100)
        params_layout.addWidget(self.psf_energy, 0, 1)
        
        # Resist thickness
        params_layout.addWidget(QLabel("Resist Thickness (nm):"), 1, 0)
        self.psf_thickness = QSpinBox()
        self.psf_thickness.setRange(10, 1000)
        self.psf_thickness.setValue(30)
        params_layout.addWidget(self.psf_thickness, 1, 1)
        
        # Number of events
        params_layout.addWidget(QLabel("Number of Events:"), 2, 0)
        self.psf_events = QSpinBox()
        self.psf_events.setRange(1000, 1000000)
        self.psf_events.setValue(100000)
        self.psf_events.setSingleStep(10000)
        params_layout.addWidget(self.psf_events, 2, 1)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Run button
        self.psf_run_btn = QPushButton("Generate PSF")
        self.psf_run_btn.clicked.connect(self.run_psf_simulation)
        layout.addWidget(self.psf_run_btn)
        
        # Progress
        self.psf_progress = QProgressBar()
        layout.addWidget(self.psf_progress)
        
        # Output
        self.psf_output = QTextEdit()
        self.psf_output.setMaximumHeight(200)
        layout.addWidget(self.psf_output)
        
        # PSF preview
        self.psf_figure = Figure(figsize=(8, 4))
        self.psf_canvas = FigureCanvas(self.psf_figure)
        layout.addWidget(self.psf_canvas)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_pattern_tab(self):
        """Create pattern simulation tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Simulate e-beam patterns with or without proximity correction.\n"
            "Compare the effects of dose modulation on pattern fidelity."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Pattern parameters
        pattern_group = QGroupBox("Pattern Parameters")
        pattern_layout = QGridLayout()
        
        # Pattern type
        pattern_layout.addWidget(QLabel("Pattern Type:"), 0, 0)
        self.pattern_type = QComboBox()
        self.pattern_type.addItems(["square", "array"])
        pattern_layout.addWidget(self.pattern_type, 0, 1)
        
        # Pattern size
        pattern_layout.addWidget(QLabel("Pattern Size (μm):"), 1, 0)
        self.pattern_size = QDoubleSpinBox()
        self.pattern_size.setRange(0.1, 10.0)
        self.pattern_size.setValue(1.0)
        self.pattern_size.setSingleStep(0.1)
        pattern_layout.addWidget(self.pattern_size, 1, 1)
        
        # Shot pitch
        pattern_layout.addWidget(QLabel("Shot Pitch:"), 2, 0)
        self.shot_pitch = QSpinBox()
        self.shot_pitch.setRange(1, 20)
        self.shot_pitch.setValue(4)
        self.shot_pitch.setSingleStep(2)
        pattern_layout.addWidget(self.shot_pitch, 2, 1)
        
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)
        
        # Dose modulation
        dose_group = QGroupBox("Dose Modulation (1.0 = no correction)")
        dose_layout = QGridLayout()
        
        dose_layout.addWidget(QLabel("Interior:"), 0, 0)
        self.dose_interior = QDoubleSpinBox()
        self.dose_interior.setRange(0.1, 2.0)
        self.dose_interior.setValue(1.0)
        self.dose_interior.setSingleStep(0.05)
        dose_layout.addWidget(self.dose_interior, 0, 1)
        
        dose_layout.addWidget(QLabel("Edge:"), 1, 0)
        self.dose_edge = QDoubleSpinBox()
        self.dose_edge.setRange(0.1, 2.0)
        self.dose_edge.setValue(1.0)
        self.dose_edge.setSingleStep(0.05)
        dose_layout.addWidget(self.dose_edge, 1, 1)
        
        dose_layout.addWidget(QLabel("Corner:"), 2, 0)
        self.dose_corner = QDoubleSpinBox()
        self.dose_corner.setRange(0.1, 2.0)
        self.dose_corner.setValue(1.0)
        self.dose_corner.setSingleStep(0.05)
        dose_layout.addWidget(self.dose_corner, 2, 1)
        
        # Quick presets
        dose_layout.addWidget(QLabel("Presets:"), 3, 0)
        preset_layout = QHBoxLayout()
        
        no_correction_btn = QPushButton("No Correction")
        no_correction_btn.clicked.connect(lambda: self.set_dose_preset(1.0, 1.0, 1.0))
        preset_layout.addWidget(no_correction_btn)
        
        typical_correction_btn = QPushButton("Typical Correction")
        typical_correction_btn.clicked.connect(lambda: self.set_dose_preset(1.0, 0.85, 0.75))
        preset_layout.addWidget(typical_correction_btn)
        
        dose_layout.addLayout(preset_layout, 3, 1)
        
        dose_group.setLayout(dose_layout)
        layout.addWidget(dose_group)
        
        # Run button
        self.pattern_run_btn = QPushButton("Run Pattern Simulation")
        self.pattern_run_btn.clicked.connect(self.run_pattern_simulation)
        layout.addWidget(self.pattern_run_btn)
        
        # Progress
        self.pattern_progress = QProgressBar()
        layout.addWidget(self.pattern_progress)
        
        # Output
        self.pattern_output = QTextEdit()
        self.pattern_output.setMaximumHeight(200)
        layout.addWidget(self.pattern_output)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_proximity_tab(self):
        """Create proximity analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Apply PSF to patterns to visualize proximity effects.\n"
            "Load PSF from simulation or use theoretical parameters."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # PSF source
        psf_source_group = QGroupBox("PSF Source")
        psf_source_layout = QVBoxLayout()
        
        source_layout = QHBoxLayout()
        self.load_psf_btn = QPushButton("Load PSF from Simulation")
        self.load_psf_btn.clicked.connect(self.load_psf_data)
        source_layout.addWidget(self.load_psf_btn)
        
        self.use_theoretical_btn = QPushButton("Use Theoretical PSF")
        self.use_theoretical_btn.clicked.connect(self.use_theoretical_psf)
        source_layout.addWidget(self.use_theoretical_btn)
        
        psf_source_layout.addLayout(source_layout)
        
        # PSF parameters display
        self.psf_params_label = QLabel("PSF Parameters: Not loaded")
        psf_source_layout.addWidget(self.psf_params_label)
        
        psf_source_group.setLayout(psf_source_layout)
        layout.addWidget(psf_source_group)
        
        # Pattern selection
        pattern_select_group = QGroupBox("Pattern to Analyze")
        pattern_select_layout = QHBoxLayout()
        
        self.load_pattern_btn = QPushButton("Load Pattern Data")
        self.load_pattern_btn.clicked.connect(self.load_pattern_data)
        pattern_select_layout.addWidget(self.load_pattern_btn)
        
        self.pattern_info_label = QLabel("No pattern loaded")
        pattern_select_layout.addWidget(self.pattern_info_label)
        
        pattern_select_group.setLayout(pattern_select_layout)
        layout.addWidget(pattern_select_group)
        
        # Analysis controls
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QHBoxLayout()
        
        self.calculate_btn = QPushButton("Calculate Proximity Effects")
        self.calculate_btn.clicked.connect(self.calculate_proximity)
        analysis_layout.addWidget(self.calculate_btn)
        
        self.compare_check = QCheckBox("Show Comparison")
        self.compare_check.setChecked(True)
        analysis_layout.addWidget(self.compare_check)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        # Visualization
        self.proximity_figure = Figure(figsize=(10, 6))
        self.proximity_canvas = FigureCanvas(self.proximity_figure)
        layout.addWidget(self.proximity_canvas)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def run_psf_simulation(self):
        """Run PSF generation simulation"""
        self.psf_output.clear()
        self.psf_progress.setValue(0)
        
        # Generate macro
        macro_content = f"""# PSF Generation
/det/setResistComposition "Si:1,O:1,H:1"
/det/setResistThickness {self.psf_thickness.value()} nm
/det/setResistDensity 1.4 g/cm3
/det/update

/process/em/fluo 1
/process/em/auger 1

/run/initialize

/gun/particle e-
/gun/energy {self.psf_energy.value()} keV
/gun/beamSize 2 nm
/gun/position 0 0 100 nm

/ebl/output/setPSFFile psf_single_spot.csv

/run/verbose 1
/run/beamOn {self.psf_events.value()}
"""
        
        macro_path = Path(self.working_dir) / "psf_generation.mac"
        with open(macro_path, 'w') as f:
            f.write(macro_content)
        
        # Run simulation
        self.psf_run_btn.setEnabled(False)
        self.status_label.setText("Running PSF simulation...")
        
        self.psf_worker = SimulationWorker(self.exe_path, str(macro_path), self.working_dir)
        self.psf_worker.output.connect(lambda msg: self.psf_output.append(msg))
        self.psf_worker.progress.connect(lambda n: self.psf_progress.setValue(n * 100 // self.psf_events.value()))
        self.psf_worker.finished.connect(self.psf_simulation_finished)
        self.psf_worker.start()
    
    def psf_simulation_finished(self, success, message):
        """Handle PSF simulation completion"""
        self.psf_run_btn.setEnabled(True)
        self.status_label.setText(message)
        
        if success:
            # Try to load and display PSF
            psf_file = Path(self.working_dir) / "output" / "psf_single_spot.csv"
            if psf_file.exists():
                self.display_psf(psf_file)
                QMessageBox.information(self, "Success", "PSF generated successfully!")
            else:
                QMessageBox.warning(self, "Warning", "Simulation completed but PSF file not found.")
    
    def display_psf(self, psf_file):
        """Display PSF data"""
        try:
            df = pd.read_csv(psf_file, comment='#')
            
            self.psf_figure.clear()
            ax = self.psf_figure.add_subplot(111)
            
            # Plot PSF
            r = df.iloc[:, 0].values  # radius in nm
            energy = df.iloc[:, 2].values  # energy density
            
            # Normalize
            if np.max(energy) > 0:
                energy = energy / np.max(energy)
            
            ax.semilogy(r, energy, 'b-', linewidth=2, label='PSF')
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Normalized Energy Density')
            ax.set_title('Point Spread Function')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, min(1000, np.max(r)))
            ax.legend()
            
            self.psf_canvas.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display PSF: {str(e)}")
    
    def run_pattern_simulation(self):
        """Run pattern simulation"""
        self.pattern_output.clear()
        self.pattern_progress.setValue(0)
        
        # Generate macro
        macro_content = f"""# Pattern Simulation
/det/setResistComposition "Si:1,O:1,H:1"
/det/setResistThickness 30 nm
/det/setResistDensity 1.4 g/cm3
/det/update

/process/em/fluo 1
/process/em/auger 1

/run/initialize

/gun/particle e-
/gun/energy 100 keV
/gun/beamSize 2 nm

# Pattern parameters
/pattern/jeol/eosMode 3
/pattern/jeol/shotPitch {self.shot_pitch.value()}
/pattern/jeol/beamCurrent 2.0
/pattern/jeol/baseDose 400

# Dose modulation
/pattern/jeol/shotRank 0
/pattern/jeol/modulation {self.dose_interior.value()}
/pattern/jeol/shotRank 1
/pattern/jeol/modulation {self.dose_edge.value()}
/pattern/jeol/shotRank 2
/pattern/jeol/modulation {self.dose_corner.value()}

# Pattern
/pattern/type {self.pattern_type.currentText()}
/pattern/size {self.pattern_size.value()} um
/pattern/center 0 0 0 um

/pattern/generate
/pattern/beamMode pattern

/ebl/output/setPSFFile pattern_simulation.csv

/run/verbose 1
/run/beamOn -1
"""
        
        macro_path = Path(self.working_dir) / "pattern_simulation.mac"
        with open(macro_path, 'w') as f:
            f.write(macro_content)
        
        # Run simulation
        self.pattern_run_btn.setEnabled(False)
        self.status_label.setText("Running pattern simulation...")
        
        self.pattern_worker = SimulationWorker(self.exe_path, str(macro_path), self.working_dir)
        self.pattern_worker.output.connect(lambda msg: self.pattern_output.append(msg))
        self.pattern_worker.progress.connect(lambda n: self.pattern_progress.setValue(min(100, n)))
        self.pattern_worker.finished.connect(self.pattern_simulation_finished)
        self.pattern_worker.start()
    
    def pattern_simulation_finished(self, success, message):
        """Handle pattern simulation completion"""
        self.pattern_run_btn.setEnabled(True)
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", 
                "Pattern simulation completed!\n"
                "You can now analyze it in the Proximity Analysis tab.")
    
    def set_dose_preset(self, interior, edge, corner):
        """Set dose modulation preset"""
        self.dose_interior.setValue(interior)
        self.dose_edge.setValue(edge)
        self.dose_corner.setValue(corner)
    
    def load_psf_data(self):
        """Load PSF data from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data", 
            str(Path(self.working_dir) / "output"),
            "CSV files (*.csv)"
        )
        
        if file_path:
            # Extract PSF parameters from data
            try:
                df = pd.read_csv(file_path, comment='#')
                # Simple parameter extraction (would need proper fitting in real implementation)
                self.psf_params_label.setText(f"PSF loaded from: {Path(file_path).name}")
                self.psf_data = df
                QMessageBox.information(self, "Success", "PSF data loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load PSF: {str(e)}")
    
    def use_theoretical_psf(self):
        """Use theoretical PSF parameters"""
        self.psf_params_label.setText("Using theoretical PSF: α=0.3, β=0.7, σf=20nm, σb=5μm")
        self.psf_data = None  # Will use theoretical model
        QMessageBox.information(self, "Info", "Using theoretical PSF parameters")
    
    def load_pattern_data(self):
        """Load pattern data"""
        # In a real implementation, this would load pattern shot data
        self.pattern_info_label.setText(f"Pattern: {self.pattern_size.value()}μm square")
        QMessageBox.information(self, "Info", "Using pattern from simulation tab")
    
    def calculate_proximity(self):
        """Calculate and display proximity effects"""
        self.proximity_figure.clear()
        
        if self.compare_check.isChecked():
            # Create 2x2 comparison
            axes = []
            for i in range(4):
                ax = self.proximity_figure.add_subplot(2, 2, i+1)
                axes.append(ax)
            
            # Create sample data for demonstration
            x = np.linspace(-1, 1, 100)
            y = np.linspace(-1, 1, 100)
            X, Y = np.meshgrid(x, y)
            
            # Pattern (square)
            pattern = ((np.abs(X) <= 0.5) & (np.abs(Y) <= 0.5)).astype(float)
            
            # Simple proximity effect simulation
            from scipy.ndimage import gaussian_filter
            
            # No correction
            axes[0].imshow(pattern, extent=[-1, 1, -1, 1], cmap='hot')
            axes[0].set_title('Pattern (No Correction)')
            
            # Effective dose without correction
            effective_no_corr = gaussian_filter(pattern, sigma=5)
            axes[1].imshow(effective_no_corr, extent=[-1, 1, -1, 1], cmap='hot')
            axes[1].set_title('Effective Dose (No Correction)')
            
            # With correction
            edge_mask = ((np.abs(X) == 0.5) | (np.abs(Y) == 0.5)) & pattern.astype(bool)
            corner_mask = ((np.abs(X) == 0.5) & (np.abs(Y) == 0.5)) & pattern.astype(bool)
            corrected = pattern.copy()
            corrected[edge_mask] *= 0.85
            corrected[corner_mask] *= 0.75
            
            axes[2].imshow(corrected, extent=[-1, 1, -1, 1], cmap='hot')
            axes[2].set_title('Pattern (With Correction)')
            
            # Effective dose with correction
            effective_corr = gaussian_filter(corrected, sigma=5)
            axes[3].imshow(effective_corr, extent=[-1, 1, -1, 1], cmap='hot')
            axes[3].set_title('Effective Dose (With Correction)')
            
            for ax in axes:
                ax.set_xlabel('X (μm)')
                ax.set_ylabel('Y (μm)')
        
        else:
            # Single view
            ax = self.proximity_figure.add_subplot(111)
            # Add single visualization here
            ax.text(0.5, 0.5, 'Proximity effect visualization', 
                   ha='center', va='center', transform=ax.transAxes)
        
        self.proximity_figure.tight_layout()
        self.proximity_canvas.draw()
        
        self.status_label.setText("Proximity analysis completed")

def main():
    app = QApplication(sys.argv)
    gui = SimpleEBLGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()