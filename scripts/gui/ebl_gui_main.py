#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EBL Simulation GUI - Main Application
"""

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QTextEdit, QLabel, QGroupBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor

import subprocess
import json
from datetime import datetime


class SimulationThread(QThread):
    """Thread for running simulation without blocking GUI"""
    output_received = Signal(str)
    error_received = Signal(str)
    finished = Signal(int)
    
    def __init__(self, exe_path, macro_path):
        super().__init__()
        self.exe_path = exe_path
        self.macro_path = macro_path
        self.process = None
        
    def run(self):
        """Run the simulation"""
        try:
            # Set environment variables
            env = os.environ.copy()
            g4_path = r"C:\Users\dreec\Geant4Projects\program_files"
            
            # Add Geant4 data paths
            env['G4ABLADATA'] = f"{g4_path}\\share\\Geant4\\data\\G4ABLA3.3"
            env['G4LEDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4EMLOW8.6.1"
            env['G4LEVELGAMMADATA'] = f"{g4_path}\\share\\Geant4\\data\\PhotonEvaporation6.1"
            env['G4NEUTRONHPDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4NDL4.7.1"
            env['G4PARTICLEXSDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4PARTICLEXS4.1"
            env['G4PIIDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4PII1.3"
            env['G4RADIOACTIVEDATA'] = f"{g4_path}\\share\\Geant4\\data\\RadioactiveDecay6.1.2"
            env['G4REALSURFACEDATA'] = f"{g4_path}\\share\\Geant4\\data\\RealSurface2.2"
            env['G4SAIDXSDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4SAIDDATA2.0"
            env['G4ENSDFSTATEDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4ENSDFSTATE3.0"
            
            # Add to PATH
            env['PATH'] = f"{g4_path}\\bin;" + env.get('PATH', '')
            
            # Run simulation
            self.process = subprocess.Popen(
                [self.exe_path, self.macro_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Read output
            for line in self.process.stdout:
                self.output_received.emit(line.strip())
                
            # Wait for completion
            return_code = self.process.wait()
            self.finished.emit(return_code)
            
        except Exception as e:
            self.error_received.emit(str(e))
            self.finished.emit(-1)


class EBLSimulationGUI(QMainWindow):
    """Main GUI window for EBL Simulation"""
    
    def __init__(self):
        super().__init__()
        self.simulation_thread = None
        self.project_path = Path(r"C:\Users\dreec\Geant4Projects\EBeamSim")
        self.exe_path = None  # Initialize exe_path
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("EBL Simulation Control Panel")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs - NOTE: Output tab must be created first or at least output_text must exist
        self.create_output_tab()  # Create this first so output_text exists
        self.create_material_tab()
        self.create_beam_tab()
        self.create_simulation_tab()
        
        # Reorder tabs to desired order
        self.tabs.removeTab(0)  # Remove output tab from position 0
        self.tabs.insertTab(3, self.tabs.widget(0), "Output")  # Insert at position 3
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_simulation)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)
        
    def create_material_tab(self):
        """Create material configuration tab"""
        material_widget = QWidget()
        layout = QVBoxLayout(material_widget)
        
        # Material selection
        material_group = QGroupBox("Resist Material")
        material_layout = QVBoxLayout()
        
        self.material_combo = QComboBox()
        self.material_combo.addItems([
            "Alucone (Al:1,C:5,H:4,O:2)",
            "PMMA (C:5,H:8,O:2)",
            "HSQ (Si:1,H:1,O:1.5)",
            "ZEP (C:11,H:14,O:1)",
            "Custom"
        ])
        material_layout.addWidget(QLabel("Material Type:"))
        material_layout.addWidget(self.material_combo)
        
        # Thickness
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Thickness (nm):"))
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 1000)
        self.thickness_spin.setValue(30)
        thickness_layout.addWidget(self.thickness_spin)
        material_layout.addLayout(thickness_layout)
        
        # Density
        density_layout = QHBoxLayout()
        density_layout.addWidget(QLabel("Density (g/cm³):"))
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 10.0)
        self.density_spin.setValue(1.35)
        self.density_spin.setSingleStep(0.01)
        density_layout.addWidget(self.density_spin)
        material_layout.addLayout(density_layout)
        
        material_group.setLayout(material_layout)
        layout.addWidget(material_group)
        layout.addStretch()
        
        self.tabs.addTab(material_widget, "Material")
        
    def create_beam_tab(self):
        """Create beam configuration tab"""
        beam_widget = QWidget()
        layout = QVBoxLayout(beam_widget)
        
        beam_group = QGroupBox("Beam Parameters")
        beam_layout = QVBoxLayout()
        
        # Energy
        energy_layout = QHBoxLayout()
        energy_layout.addWidget(QLabel("Energy (keV):"))
        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(1, 300)
        self.energy_spin.setValue(100)
        energy_layout.addWidget(self.energy_spin)
        beam_layout.addLayout(energy_layout)
        
        # Beam size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Beam Size (nm):"))
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.1, 100)
        self.beam_size_spin.setValue(2.0)
        self.beam_size_spin.setSingleStep(0.1)
        size_layout.addWidget(self.beam_size_spin)
        beam_layout.addLayout(size_layout)
        
        # Position
        position_group = QGroupBox("Beam Position")
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Z (nm):"))
        self.z_position_spin = QSpinBox()
        self.z_position_spin.setRange(1, 1000)
        self.z_position_spin.setValue(100)
        pos_layout.addWidget(self.z_position_spin)
        position_group.setLayout(pos_layout)
        beam_layout.addWidget(position_group)
        
        beam_group.setLayout(beam_layout)
        layout.addWidget(beam_group)
        layout.addStretch()
        
        self.tabs.addTab(beam_widget, "Beam")
        
    def create_simulation_tab(self):
        """Create simulation control tab"""
        sim_widget = QWidget()
        layout = QVBoxLayout(sim_widget)
        
        # Simulation parameters
        sim_group = QGroupBox("Simulation Parameters")
        sim_layout = QVBoxLayout()
        
        # Number of events
        events_layout = QHBoxLayout()
        events_layout.addWidget(QLabel("Number of Events:"))
        self.events_spin = QSpinBox()
        self.events_spin.setRange(10, 1000000)
        self.events_spin.setValue(10000)
        self.events_spin.setSingleStep(1000)
        events_layout.addWidget(self.events_spin)
        sim_layout.addLayout(events_layout)
        
        # Physics options
        self.fluo_check = QCheckBox("Enable Fluorescence")
        self.fluo_check.setChecked(True)
        sim_layout.addWidget(self.fluo_check)
        
        self.auger_check = QCheckBox("Enable Auger Electrons")
        self.auger_check.setChecked(True)
        sim_layout.addWidget(self.auger_check)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # Executable path
        exe_group = QGroupBox("Simulation Executable")
        exe_layout = QHBoxLayout()
        self.exe_path_label = QLabel("Not selected")
        exe_layout.addWidget(self.exe_path_label)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_executable)
        exe_layout.addWidget(browse_button)
        exe_group.setLayout(exe_layout)
        layout.addWidget(exe_group)
        
        # Auto-detect executable
        self.auto_detect_executable()
        
        layout.addStretch()
        self.tabs.addTab(sim_widget, "Simulation")
        
    def create_output_tab(self):
        """Create output/log tab"""
        output_widget = QWidget()
        layout = QVBoxLayout(output_widget)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.output_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.output_text.clear)
        button_layout.addWidget(clear_button)
        
        save_button = QPushButton("Save Log")
        save_button.clicked.connect(self.save_log)
        button_layout.addWidget(save_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.tabs.addTab(output_widget, "Output")
        
    def auto_detect_executable(self):
        """Auto-detect the simulation executable"""
        possible_paths = [
            self.project_path / "out/build/x64-debug/ebl_sim.exe",
            self.project_path / "out/build/x64-release/ebl_sim.exe",
            self.project_path / "build/bin/Debug/ebl_sim.exe",
            self.project_path / "build/bin/Release/ebl_sim.exe",
        ]
        
        for path in possible_paths:
            if path.exists():
                self.exe_path = str(path)
                self.exe_path_label.setText(str(path.name))
                self.log_output(f"Found executable: {path}")
                return
                
        self.log_output("Warning: Could not auto-detect ebl_sim.exe")
        
    def browse_executable(self):
        """Browse for the simulation executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ebl_sim.exe",
            str(self.project_path),
            "Executable (*.exe)"
        )
        
        if file_path:
            self.exe_path = file_path
            self.exe_path_label.setText(Path(file_path).name)
            self.log_output(f"Selected executable: {file_path}")
            
    def generate_macro(self):
        """Generate a macro file from GUI settings"""
        material_map = {
            "Alucone (Al:1,C:5,H:4,O:2)": "Al:1,C:5,H:4,O:2",
            "PMMA (C:5,H:8,O:2)": "C:5,H:8,O:2",
            "HSQ (Si:1,H:1,O:1.5)": "Si:1,H:1,O:1.5",
            "ZEP (C:11,H:14,O:1)": "C:11,H:14,O:1"
        }
        
        material = material_map.get(self.material_combo.currentText(), "Al:1,C:5,H:4,O:2")
        
        macro_content = f"""# EBL Simulation Macro - Generated by GUI
# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

/run/verbose 1
/event/verbose 0
/tracking/verbose 0

# Initialize
/run/initialize

# Material settings
/det/setResistComposition "{material}"
/det/setResistThickness {self.thickness_spin.value()} nm
/det/setResistDensity {self.density_spin.value()} g/cm3
/det/update

# Physics processes
/process/em/fluo {1 if self.fluo_check.isChecked() else 0}
/process/em/auger {1 if self.auger_check.isChecked() else 0}

# Beam configuration
/gun/particle e-
/gun/energy {self.energy_spin.value()} keV
/gun/position 0 0 {self.z_position_spin.value()} nm
/gun/direction 0 0 -1
/gun/beamSize {self.beam_size_spin.value()} nm

# Run simulation
/run/beamOn {self.events_spin.value()}
"""
        
        # Save macro file
        macro_path = self.project_path / "gui_generated.mac"
        with open(macro_path, 'w') as f:
            f.write(macro_content)
            
        return str(macro_path)
        
    def run_simulation(self):
        """Run the simulation"""
        if not self.exe_path:
            QMessageBox.warning(self, "Error", "Please select the simulation executable first!")
            return
            
        # Generate macro
        macro_path = self.generate_macro()
        self.log_output(f"Generated macro: {macro_path}")
        
        # Switch to output tab
        self.tabs.setCurrentIndex(3)
        
        # Update UI
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Running simulation...")
        
        # Create and start simulation thread
        self.simulation_thread = SimulationThread(self.exe_path, macro_path)
        self.simulation_thread.output_received.connect(self.log_output)
        self.simulation_thread.error_received.connect(self.log_error)
        self.simulation_thread.finished.connect(self.simulation_finished)
        self.simulation_thread.start()
        
    def stop_simulation(self):
        """Stop the running simulation"""
        if self.simulation_thread and self.simulation_thread.process:
            self.simulation_thread.process.terminate()
            self.log_output("Simulation stopped by user")
            
    def simulation_finished(self, return_code):
        """Handle simulation completion"""
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        if return_code == 0:
            self.status_label.setText("Simulation completed successfully")
            self.log_output(f"\nSimulation finished successfully!")
            
            # Check for output files
            self.check_output_files()
        else:
            self.status_label.setText("Simulation failed")
            self.log_error(f"Simulation failed with code: {return_code}")
            
    def check_output_files(self):
        """Check for generated output files"""
        exe_dir = Path(self.exe_path).parent
        
        output_files = [
            "ebl_psf_data.csv",
            "beamer_psf.dat",
            "simulation_summary.txt"
        ]
        
        self.log_output("\nChecking for output files:")
        for file in output_files:
            file_path = exe_dir / file
            if file_path.exists():
                self.log_output(f"  [OK] {file} ({file_path.stat().st_size} bytes)")
            else:
                self.log_output(f"  [MISSING] {file} not found")
                
    def log_output(self, message):
        """Add message to output log"""
        self.output_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def log_error(self, message):
        """Add error message to output log"""
        self.output_text.append(f"<span style='color: red;'>[ERROR] {message}</span>")
        
    def save_log(self):
        """Save the output log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log",
            str(self.project_path / f"simulation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Text Files (*.txt)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.output_text.toPlainText())
            self.log_output(f"Log saved to: {file_path}")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = EBLSimulationGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()