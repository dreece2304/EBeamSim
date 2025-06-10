#!/usr/bin/env python3
"""
Modern EBL Simulation GUI using Qt
----------------------------------
A professional-looking GUI for electron beam lithography simulations
using PySide6 (Qt6) with modern styling and better performance.

Installation:
pip install PySide6 matplotlib numpy
"""

import sys
import os
import time
import threading
import subprocess
import platform
from pathlib import Path
import csv
import queue
from collections import deque

# Qt imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit,
    QProgressBar, QStatusBar, QMenuBar, QFileDialog, QMessageBox,
    QGroupBox, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal, QSettings
from PySide6.QtGui import QFont, QIcon, QAction, QPalette, QColor

# Matplotlib for Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np

class SimulationWorker(QObject):
    """Worker thread for running simulations"""
    output = Signal(str)  # Signal for output messages
    progress = Signal(int)  # Signal for progress updates
    finished = Signal(bool, str)  # Signal for completion (success, message)

    def __init__(self, executable_path, macro_path, working_dir):
        super().__init__()
        self.executable_path = executable_path
        self.macro_path = macro_path
        self.working_dir = working_dir
        self.process = None
        self.should_stop = False

    def run_simulation(self):
        """Run the simulation in this thread"""
        try:
            args = [self.executable_path, self.macro_path]

            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=0,
                cwd=self.working_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )

            line_count = 0
            max_lines = 5000  # Reasonable limit

            while True:
                if self.should_stop:
                    self.process.terminate()
                    break

                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if line:
                    if line_count < max_lines:
                        self.output.emit(line)
                    elif line_count == max_lines:
                        self.output.emit("... (output truncated)")

                    # Try to extract progress information
                    if "Event #" in line:
                        try:
                            event_num = int(line.split("Event #")[1].split()[0])
                            self.progress.emit(event_num)
                        except:
                            pass

                    line_count += 1

            return_code = self.process.wait()

            if return_code == 0 and not self.should_stop:
                self.finished.emit(True, "Simulation completed successfully")
            else:
                self.finished.emit(False, f"Simulation failed (code: {return_code})")

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

    def stop(self):
        """Stop the simulation"""
        self.should_stop = True
        if self.process:
            self.process.terminate()

class PlotWidget(QWidget):
    """Custom widget for matplotlib plots"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Plot controls
        controls = QHBoxLayout()

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Linear", "Log-Log", "Semi-Log"])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot_type)

        self.load_button = QPushButton("Load Data")
        self.load_button.clicked.connect(self.load_data)

        self.save_button = QPushButton("Save Plot")
        self.save_button.clicked.connect(self.save_plot)

        controls.addWidget(QLabel("Plot Type:"))
        controls.addWidget(self.plot_type_combo)
        controls.addStretch()
        controls.addWidget(self.load_button)
        controls.addWidget(self.save_button)

        layout.addWidget(self.toolbar)
        layout.addLayout(controls)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

        # Store data for replotting
        self.current_data = None

    def plot_data(self, radii, energies, title="PSF Profile"):
        """Plot the data with current settings"""
        self.current_data = (radii, energies, title)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        plot_type = self.plot_type_combo.currentText()

        if plot_type == "Log-Log":
            # Filter positive values
            valid = [(r > 0 and e > 0) for r, e in zip(radii, energies)]
            r_filt = [r for r, v in zip(radii, valid) if v]
            e_filt = [e for e, v in zip(energies, valid) if v]

            if r_filt and e_filt:
                ax.loglog(r_filt, e_filt, 'b-', linewidth=2)
        elif plot_type == "Semi-Log":
            ax.semilogy(radii, energies, 'b-', linewidth=2)
        else:  # Linear
            ax.plot(radii, energies, 'b-', linewidth=2)

        ax.set_xlabel('Radius (nm)')
        ax.set_ylabel('Energy Deposition (eV/nmÂ²)')
        ax.set_title(f'{title} - {plot_type} Scale')
        ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def update_plot_type(self):
        """Update plot when type changes"""
        if self.current_data:
            self.plot_data(*self.current_data)

    def load_data(self):
        """Load data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data", "", "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            try:
                radii, energies = [], []

                with open(file_path, 'r') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header

                    for row in reader:
                        if len(row) >= 2:
                            try:
                                radii.append(float(row[0]))
                                energies.append(float(row[1]))
                            except ValueError:
                                continue

                if radii and energies:
                    self.plot_data(radii, energies, f"PSF - {Path(file_path).stem}")
                else:
                    QMessageBox.warning(self, "Warning", "No valid data found in file")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def save_plot(self):
        """Save current plot"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "",
            "PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg)"
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Plot saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")

class EBLMainWindow(QMainWindow):
    """Main window for EBL simulation GUI"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("EBL", "SimulationGUI")
        self.setup_ui()
        self.setup_defaults()
        self.load_settings()

        # Simulation state
        self.simulation_worker = None
        self.simulation_thread = None
        self.simulation_running = False

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("EBL Simulation Control - Qt Edition")
        self.setMinimumSize(1000, 700)

        # Apply modern dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
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
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #404040;
                border: 1px solid #555555;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs
        self.create_resist_tab()
        self.create_beam_tab()
        self.create_simulation_tab()
        self.create_output_tab()
        self.create_visualization_tab()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)

        # Create menu bar and status bar
        self.create_menu_bar()
        self.create_status_bar()

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        select_exe_action = QAction("Select Executable", self)
        select_exe_action.triggered.connect(self.select_executable)
        file_menu.addAction(select_exe_action)

        save_macro_action = QAction("Save Macro", self)
        save_macro_action.triggered.connect(self.save_macro)
        file_menu.addAction(save_macro_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Simulation menu
        sim_menu = menubar.addMenu("Simulation")

        run_action = QAction("Run Simulation", self)
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)

        stop_action = QAction("Stop Simulation", self)
        stop_action.triggered.connect(self.stop_simulation)
        sim_menu.addAction(stop_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def create_resist_tab(self):
        """Create resist properties tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Material group
        material_group = QGroupBox("Material Properties")
        material_layout = QGridLayout()

        # Material presets
        self.material_presets = {
            "PMMA": ("C:5,H:8,O:2", 1.19),
            "HSQ": ("Si:1,H:1,O:1.5", 1.4),
            "ZEP": ("C:11,H:14,O:1", 1.2),
            "Alucone_XPS": ("Al:1,C:5,H:4,O:2", 1.35),
            "Alucone_Exposed": ("Al:1,C:5,H:4,O:3", 1.40),
            "Custom": ("", 1.0)
        }

        material_layout.addWidget(QLabel("Material:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems(list(self.material_presets.keys()))
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        material_layout.addWidget(self.material_combo, 0, 1)

        material_layout.addWidget(QLabel("Composition:"), 1, 0)
        self.composition_edit = QLineEdit()
        self.composition_edit.setPlaceholderText("Al:1,C:5,H:4,O:2")
        material_layout.addWidget(self.composition_edit, 1, 1, 1, 2)

        material_layout.addWidget(QLabel("Thickness (nm):"), 2, 0)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 10000.0)
        self.thickness_spin.setValue(40.0)
        self.thickness_spin.setDecimals(1)
        material_layout.addWidget(self.thickness_spin, 2, 1)

        material_layout.addWidget(QLabel("Density (g/cmÂ³):"), 3, 0)
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 10.0)
        self.density_spin.setValue(1.35)
        self.density_spin.setDecimals(2)
        material_layout.addWidget(self.density_spin, 3, 1)

        material_group.setLayout(material_layout)

        # Info group
        info_group = QGroupBox("Material Information")
        info_layout = QVBoxLayout()

        info_text = QLabel("""
<b>Current defaults based on XPS analysis:</b><br>
â€¢ Pristine Alucone: Al:1,C:5,H:4,O:2 (1.35 g/cmÂ³)<br>
â€¢ Exposed Alucone: Al:1,C:5,H:4,O:3 (1.40 g/cmÂ³)<br>
â€¢ From TMA + butyne-1,4-diol MLD process
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        info_group.setLayout(info_layout)

        layout.addWidget(material_group)
        layout.addWidget(info_group)
        layout.addStretch()

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Resist Properties")

    def create_beam_tab(self):
        """Create beam parameters tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Beam properties group
        beam_group = QGroupBox("Beam Properties")
        beam_layout = QGridLayout()

        beam_layout.addWidget(QLabel("Energy (keV):"), 0, 0)
        self.energy_spin = QDoubleSpinBox()
        self.energy_spin.setRange(0.1, 1000.0)
        self.energy_spin.setValue(30.0)
        self.energy_spin.setDecimals(1)
        beam_layout.addWidget(self.energy_spin, 0, 1)

        beam_layout.addWidget(QLabel("Beam Size (nm):"), 1, 0)
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.1, 1000.0)
        self.beam_size_spin.setValue(1.0)
        self.beam_size_spin.setDecimals(1)
        beam_layout.addWidget(self.beam_size_spin, 1, 1)

        beam_group.setLayout(beam_layout)

        # Position group
        position_group = QGroupBox("Beam Position (nm)")
        position_layout = QGridLayout()

        position_layout.addWidget(QLabel("X:"), 0, 0)
        self.pos_x_spin = QDoubleSpinBox()
        self.pos_x_spin.setRange(-10000, 10000)
        self.pos_x_spin.setValue(0.0)
        position_layout.addWidget(self.pos_x_spin, 0, 1)

        position_layout.addWidget(QLabel("Y:"), 0, 2)
        self.pos_y_spin = QDoubleSpinBox()
        self.pos_y_spin.setRange(-10000, 10000)
        self.pos_y_spin.setValue(0.0)
        position_layout.addWidget(self.pos_y_spin, 0, 3)

        position_layout.addWidget(QLabel("Z:"), 1, 0)
        self.pos_z_spin = QDoubleSpinBox()
        self.pos_z_spin.setRange(-1000, 1000)
        self.pos_z_spin.setValue(50.0)
        position_layout.addWidget(self.pos_z_spin, 1, 1)

        position_layout.addWidget(QLabel("(Z should be above resist)"), 1, 2, 1, 2)

        position_group.setLayout(position_layout)

        # Direction group
        direction_group = QGroupBox("Beam Direction")
        direction_layout = QGridLayout()

        direction_layout.addWidget(QLabel("X:"), 0, 0)
        self.dir_x_spin = QDoubleSpinBox()
        self.dir_x_spin.setRange(-1, 1)
        self.dir_x_spin.setValue(0.0)
        self.dir_x_spin.setDecimals(3)
        direction_layout.addWidget(self.dir_x_spin, 0, 1)

        direction_layout.addWidget(QLabel("Y:"), 0, 2)
        self.dir_y_spin = QDoubleSpinBox()
        self.dir_y_spin.setRange(-1, 1)
        self.dir_y_spin.setValue(0.0)
        self.dir_y_spin.setDecimals(3)
        direction_layout.addWidget(self.dir_y_spin, 0, 3)

        direction_layout.addWidget(QLabel("Z:"), 1, 0)
        self.dir_z_spin = QDoubleSpinBox()
        self.dir_z_spin.setRange(-1, 1)
        self.dir_z_spin.setValue(-1.0)
        self.dir_z_spin.setDecimals(3)
        direction_layout.addWidget(self.dir_z_spin, 1, 1)

        direction_layout.addWidget(QLabel("(Downward = 0,0,-1)"), 1, 2, 1, 2)

        direction_group.setLayout(direction_layout)

        layout.addWidget(beam_group)
        layout.addWidget(position_group)
        layout.addWidget(direction_group)
        layout.addStretch()

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Beam Parameters")

    def create_simulation_tab(self):
        """Create simulation settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Simulation parameters group
        sim_group = QGroupBox("Simulation Parameters")
        sim_layout = QGridLayout()

        sim_layout.addWidget(QLabel("Number of Events:"), 0, 0)
        self.events_spin = QSpinBox()
        self.events_spin.setRange(1, 100000000)
        self.events_spin.setValue(100000)
        sim_layout.addWidget(self.events_spin, 0, 1)

        warning_label = QLabel("âš ï¸ >1M events may take significant time")
        warning_label.setStyleSheet("color: orange; font-size: 10px;")
        sim_layout.addWidget(warning_label, 0, 2)

        sim_layout.addWidget(QLabel("Random Seed:"), 1, 0)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2147483647)
        self.seed_spin.setValue(-1)
        sim_layout.addWidget(self.seed_spin, 1, 1)

        sim_layout.addWidget(QLabel("Verbose Level:"), 2, 0)
        self.verbose_spin = QSpinBox()
        self.verbose_spin.setRange(0, 5)
        self.verbose_spin.setValue(0)
        sim_layout.addWidget(self.verbose_spin, 2, 1)

        sim_group.setLayout(sim_layout)

        # Physics options group
        physics_group = QGroupBox("Physics Options")
        physics_layout = QVBoxLayout()

        self.fluorescence_check = QCheckBox("Enable Fluorescence")
        self.fluorescence_check.setChecked(True)
        physics_layout.addWidget(self.fluorescence_check)

        self.auger_check = QCheckBox("Enable Auger Processes")
        self.auger_check.setChecked(True)
        physics_layout.addWidget(self.auger_check)

        self.visualization_check = QCheckBox("Enable Visualization")
        self.visualization_check.setChecked(False)
        physics_layout.addWidget(self.visualization_check)

        physics_group.setLayout(physics_layout)

        # Control buttons
        button_layout = QHBoxLayout()

        self.generate_button = QPushButton("Generate Macro")
        self.generate_button.clicked.connect(self.generate_macro)
        button_layout.addWidget(self.generate_button)

        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop Simulation")
        self.stop_button.clicked.connect(self.stop_simulation)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        button_layout.addStretch()

        layout.addWidget(sim_group)
        layout.addWidget(physics_group)
        layout.addLayout(button_layout)
        layout.addStretch()

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Simulation")

    def create_output_tab(self):
        """Create output log tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Output text
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.output_text)

        # Control buttons
        button_layout = QHBoxLayout()

        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_button)

        save_button = QPushButton("Save Log")
        save_button.clicked.connect(self.save_log)
        button_layout.addWidget(save_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Output Log")

    def create_visualization_tab(self):
        """Create visualization tab"""
        self.plot_widget = PlotWidget()
        self.tab_widget.addTab(self.plot_widget, "Visualization")

    def setup_defaults(self):
        """Setup default values"""
        # Set defaults based on XPS data
        self.material_combo.setCurrentText("Alucone_XPS")
        self.on_material_changed()

        # Default executable path
        self.executable_path = str(Path(__file__).resolve().parents[3] / "out" / "build" / "x64-release" / "bin" / "ebl_sim.exe")
        self.working_dir = str(Path(self.executable_path).parent)

    def on_material_changed(self):
        """Handle material selection change"""
        material = self.material_combo.currentText()
        if material in self.material_presets:
            composition, density = self.material_presets[material]
            self.composition_edit.setText(composition)
            self.density_spin.setValue(density)

            # Enable/disable composition editing
            self.composition_edit.setReadOnly(material != "Custom")

    def generate_macro(self):
        """Generate Geant4 macro file"""
        try:
            macro_path = Path(self.working_dir) / "ebl_sim_run.mac"

            with open(macro_path, 'w') as f:
                f.write("# EBL Simulation Macro - Generated by Qt GUI\n")
                f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # Verbose settings
                verbose = min(self.verbose_spin.value(), 1) if self.events_spin.value() > 10000 else self.verbose_spin.value()
                f.write(f"/run/verbose {verbose}\n")
                f.write(f"/event/verbose {max(0, verbose-1)}\n")
                f.write(f"/tracking/verbose {max(0, verbose-2)}\n\n")

                # Random seed
                if self.seed_spin.value() > 0:
                    f.write(f"/random/setSeeds {self.seed_spin.value()} {self.seed_spin.value()+1}\n\n")

                # Initialize
                f.write("/run/initialize\n\n")

                # Resist properties
                f.write("# Resist properties\n")
                f.write(f'/det/setResistComposition "{self.composition_edit.text()}"\n')
                f.write(f"/det/setResistThickness {self.thickness_spin.value()} nm\n")
                f.write(f"/det/setResistDensity {self.density_spin.value()} g/cm3\n")
                f.write("/det/update\n\n")

                # Physics
                f.write("# Physics settings\n")
                f.write(f"/process/em/fluo {1 if self.fluorescence_check.isChecked() else 0}\n")
                f.write(f"/process/em/auger {1 if self.auger_check.isChecked() else 0}\n\n")

                # Beam parameters
                f.write("# Beam parameters\n")
                f.write("/gun/particle e-\n")
                f.write(f"/gun/energy {self.energy_spin.value()} keV\n")
                f.write(f"/gun/position {self.pos_x_spin.value()} {self.pos_y_spin.value()} {self.pos_z_spin.value()} nm\n")

                # Normalize direction
                dx, dy, dz = self.dir_x_spin.value(), self.dir_y_spin.value(), self.dir_z_spin.value()
                length = (dx*dx + dy*dy + dz*dz)**0.5
                if length > 0:
                    dx, dy, dz = dx/length, dy/length, dz/length
                else:
                    dx, dy, dz = 0, 0, -1

                f.write(f"/gun/direction {dx} {dy} {dz}\n\n")

                # Visualization
                if self.visualization_check.isChecked():
                    f.write("# Visualization\n")
                    f.write("/vis/open OGLSQt\n")
                    f.write("/vis/drawVolume\n")
                    f.write("/vis/scene/add/trajectories smooth\n\n")

                # Run
                f.write("# Run simulation\n")
                f.write(f"/run/beamOn {self.events_spin.value()}\n")

            self.log_output(f"Macro generated: {macro_path}")
            self.status_label.setText("Macro generated successfully")
            return str(macro_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate macro: {str(e)}")
            return None

    def run_simulation(self):
        """Start simulation"""
        if self.simulation_running:
            QMessageBox.information(self, "Info", "Simulation is already running")
            return

        # Validate inputs
        if self.events_spin.value() > 1000000:
            reply = QMessageBox.question(
                self, "Warning",
                f"Running {self.events_spin.value():,} events may take a very long time. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Generate macro
        macro_path = self.generate_macro()
        if not macro_path:
            return

        # Check executable
        if not Path(self.executable_path).exists():
            QMessageBox.critical(self, "Error", f"Executable not found: {self.executable_path}")
            return

        # Clear log and setup UI
        self.clear_log()
        self.simulation_running = True
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(self.events_spin.value())
        self.progress_bar.setValue(0)

        # Create worker thread
        self.simulation_thread = QThread()
        self.simulation_worker = SimulationWorker(self.executable_path, macro_path, self.working_dir)
        self.simulation_worker.moveToThread(self.simulation_thread)

        # Connect signals
        self.simulation_worker.output.connect(self.log_output)
        self.simulation_worker.progress.connect(self.update_progress)
        self.simulation_worker.finished.connect(self.simulation_finished)
        self.simulation_thread.started.connect(self.simulation_worker.run_simulation)

        # Start thread
        self.simulation_thread.start()
        self.log_output("Simulation started...")
        self.status_label.setText("Simulation running...")

    def stop_simulation(self):
        """Stop simulation"""
        if self.simulation_worker:
            self.simulation_worker.stop()
            self.log_output("Stopping simulation...")

    def simulation_finished(self, success, message):
        """Handle simulation completion"""
        self.simulation_running = False
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)

        self.log_output(message)
        self.status_label.setText(message)

        if self.simulation_thread:
            self.simulation_thread.quit()
            self.simulation_thread.wait()

        if success:
            QMessageBox.information(self, "Success", "Simulation completed successfully!")

    def update_progress(self, event_num):
        """Update progress bar"""
        self.progress_bar.setValue(event_num)
        progress = (event_num / self.events_spin.value()) * 100
        self.status_label.setText(f"Simulation running... {event_num}/{self.events_spin.value()} ({progress:.1f}%)")

    def log_output(self, message):
        """Add message to output log"""
        self.output_text.append(message)

    def clear_log(self):
        """Clear output log"""
        self.output_text.clear()

    def save_log(self):
        """Save log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "", "Text files (*.txt);;All files (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.output_text.toPlainText())
                QMessageBox.information(self, "Success", f"Log saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")

    def save_macro(self):
        """Save macro to file"""
        macro_path = self.generate_macro()
        if macro_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Macro", "", "Macro files (*.mac);;All files (*.*)"
            )

            if file_path:
                try:
                    with open(macro_path, 'r') as src, open(file_path, 'w') as dst:
                        dst.write(src.read())
                    QMessageBox.information(self, "Success", f"Macro saved to {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save macro: {str(e)}")

    def select_executable(self):
        """Select executable file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select EBL Executable", "", "Executable files (*.exe);;All files (*.*)"
        )

        if file_path:
            self.executable_path = file_path
            self.working_dir = str(Path(file_path).parent)
            self.log_output(f"Selected executable: {file_path}")

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About EBL Simulation GUI",
                          """<h3>EBL Simulation GUI v2.0 (Qt Edition)</h3>
                          <p>A modern, professional GUI for Geant4-based electron beam lithography simulations.</p>
                          <p><b>Key Features:</b></p>
                          <ul>
                          <li>XPS-based material compositions</li>
                          <li>Modern Qt interface with dark theme</li>
                          <li>Real-time simulation monitoring</li>
                          <li>Integrated data visualization</li>
                          <li>Improved performance and stability</li>
                          </ul>
                          <p>Based on experimental data from TMA + butyne-1,4-diol MLD process.</p>
                          """)

    def load_settings(self):
        """Load application settings"""
        # Restore window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Restore executable path
        exe_path = self.settings.value("executable_path")
        if exe_path and Path(exe_path).exists():
            self.executable_path = exe_path
            self.working_dir = str(Path(exe_path).parent)

    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("executable_path", self.executable_path)

    def closeEvent(self, event):
        """Handle window close event"""
        self.save_settings()

        if self.simulation_running:
            reply = QMessageBox.question(
                self, "Quit", "Simulation is running. Stop and quit?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            else:
                self.stop_simulation()

        event.accept()

def main():
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("EBL Simulation GUI")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("EBL Research")

    # Create and show main window
    window = EBLMainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
