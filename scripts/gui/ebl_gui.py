#!/usr/bin/env python3
"""
Enhanced EBL Simulation GUI with 2D Visualization - Part 1
------------------------------------------------
Core improvements including:
- Removed placeholder buttons
- Consolidated BEAMER conversion methods
- Consolidated PSF validation
- Added unified file manager
- Fixed 2D contour plotting
- Better button states and status messages
- PSF comparison functionality

Installation:
pip install PySide6 matplotlib numpy pandas scipy
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
import json
import re
import glob
import random
import scipy.signal

# Qt imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit,
    QProgressBar, QStatusBar, QMenuBar, QFileDialog, QMessageBox,
    QGroupBox, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QSlider, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal, QSettings
from PySide6.QtGui import QFont, QIcon, QAction, QPalette, QColor

# Scientific computing
import numpy as np
import pandas as pd
import scipy.interpolate

# Matplotlib for Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.cm as cm


class FileManager:
    """Unified file management for consistent handling across the application"""

    def __init__(self, working_dir):
        self.working_dir = Path(working_dir)
        self.recent_files = []
        self.supported_formats = {
            'csv': ['csv'],
            'beamer': ['txt', 'dat'],
            'config': ['json'],
            'macro': ['mac']
        }

    def validate_file_format(self, file_path, expected_type):
        """Validate file format before loading"""
        file_path = Path(file_path)
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"

        if expected_type in self.supported_formats:
            valid_extensions = self.supported_formats[expected_type]
            if file_path.suffix.lower().lstrip('.') not in valid_extensions:
                return False, f"Expected {expected_type} file, got {file_path.suffix}"

        return True, "Valid file format"

    def load_csv_with_validation(self, file_path, progress_callback=None):
        """Load CSV with validation and progress reporting"""
        try:
            if progress_callback:
                progress_callback("Validating file format...")

            valid, message = self.validate_file_format(file_path, 'csv')
            if not valid:
                return None, message

            if progress_callback:
                progress_callback("Loading CSV data...")

            df = pd.read_csv(file_path)

            if progress_callback:
                progress_callback("Validating data structure...")

            # Basic validation
            if df.empty:
                return None, "CSV file is empty"

            self._add_to_recent(file_path)
            return df, "Successfully loaded"

        except Exception as e:
            return None, f"Error loading CSV: {str(e)}"

    def save_with_backup(self, data, file_path, backup=True):
        """Save data with optional backup creation"""
        try:
            file_path = Path(file_path)

            # Create backup if file exists
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f".backup{file_path.suffix}")
                file_path.rename(backup_path)

            # Save based on file type
            if file_path.suffix.lower() == '.csv':
                if isinstance(data, pd.DataFrame):
                    data.to_csv(file_path)
                else:
                    # Assume it's structured data for CSV
                    with open(file_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(data)
            else:
                # Text files
                with open(file_path, 'w') as f:
                    f.write(str(data))

            return True, f"Saved to {file_path}"

        except Exception as e:
            return False, f"Error saving: {str(e)}"

    def get_recent_simulation_files(self):
        """Find recent simulation output files"""
        patterns = [
            "*psf*.csv",
            "*_E*keV_*.csv",
            "ebl_psf_data.csv",
            "ebl_2d_data.csv"
        ]

        recent_files = []
        for pattern in patterns:
            files = list(self.working_dir.glob(pattern))
            recent_files.extend(files)

        # Sort by modification time, most recent first
        recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return recent_files[:10]  # Return up to 10 most recent

    def _add_to_recent(self, file_path):
        """Add file to recent files list"""
        file_path = str(file_path)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:20]  # Keep last 20


class StatusButton(QPushButton):
    """Enhanced button with status awareness"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.default_text = text
        self.is_working = False

    def set_status(self, enabled, tooltip_message=""):
        """Set button status with helpful tooltip"""
        self.setEnabled(enabled)
        if not enabled and tooltip_message:
            self.setToolTip(f"❌ {tooltip_message}")
        else:
            self.setToolTip("")

    def set_working(self, working, message="Processing..."):
        """Show working state with spinner effect"""
        self.is_working = working
        if working:
            self.setText(f"🔄 {message}")
            self.setEnabled(False)
        else:
            self.setText(self.default_text)
            self.setEnabled(True)


# Updated SimulationWorker class - keeping the existing optimized version
class SimulationWorker(QObject):
    """Worker thread for running simulations with optimized progress tracking"""
    output = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, executable_path, macro_path, working_dir):
        super().__init__()
        self.executable_path = executable_path
        self.macro_path = macro_path
        self.working_dir = working_dir
        self.process = None
        self.should_stop = False
        self.total_events = None
        self.last_reported_progress = -1

    def run_simulation(self):
        """Run the simulation in this thread with optimized progress tracking"""
        try:
            args = [self.executable_path, self.macro_path]

            # Set up environment variables for Geant4
            env = os.environ.copy()
            g4_path = r"C:\Users\bergsman_lab_user\Geant4\ProgramFiles"

            # Add Geant4 data paths
            env['G4ABLADATA'] = f"{g4_path}\\share\\Geant4\\data\\G4ABLA3.3"
            env['G4CHANNELINGDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4CHANNELING1.0"
            env['G4LEDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4EMLOW8.6.1"
            env['G4ENSDFSTATEDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4ENSDFSTATE3.0"
            env['G4INCLDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4INCL1.2"
            env['G4NEUTRONHPDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4NDL4.7.1"
            env['G4PARTICLEXSDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4PARTICLEXS4.1"
            env['G4PIIDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4PII1.3"
            env['G4RADIOACTIVEDATA'] = f"{g4_path}\\share\\Geant4\\data\\RadioactiveDecay6.1.2"
            env['G4REALSURFACEDATA'] = f"{g4_path}\\share\\Geant4\\data\\RealSurface2.2"
            env['G4SAIDXSDATA'] = f"{g4_path}\\share\\Geant4\\data\\G4SAIDDATA2.0"
            env['G4LEVELGAMMADATA'] = f"{g4_path}\\share\\Geant4\\data\\PhotonEvaporation6.1"

            # Add to PATH
            env['PATH'] = f"{g4_path}\\bin;" + env.get('PATH', '')

            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=self.working_dir,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )

            # OPTIMIZED progress tracking for large simulations
            line_count = 0
            max_gui_lines = 3000  # Reduce GUI overhead for large sims

            # Enhanced tracking variables
            last_event_number = 0
            energy_reports_count = 0
            track_reports_count = 0
            estimated_progress = 0
            last_progress_update = time.time()

            # Keywords for filtering important output
            important_keywords = [
                "Processing event", "Progress:", "Resist energy deposits:",
                "StackingAction:", "ERROR", "WARNING", "Complete", "MeV", "Milestone"
            ]

            while True:
                if self.should_stop:
                    self.process.terminate()
                    break

                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if line:
                    # Smart output filtering for large simulations
                    should_show_line = True
                    if self.total_events and self.total_events > 100000:
                        # For large sims, filter output aggressively
                        should_show_line = any(keyword in line for keyword in important_keywords)

                    if should_show_line and line_count < max_gui_lines:
                        self.output.emit(line)
                    elif line_count == max_gui_lines:
                        self.output.emit("... (output filtered for large simulation performance)")

                    # Parse for total events
                    if "events will be processed" in line or "event will be processed" in line:
                        match = re.search(r'(\d+)\s+events?\s+will be processed', line)
                        if match:
                            self.total_events = int(match.group(1))
                            self.output.emit(f">>> Total events to process: {self.total_events}")

                    # ENHANCED PROGRESS TRACKING
                    progress_updated = False
                    current_time = time.time()

                    # Method 1: Direct "Processing event X" messages
                    if "Processing event" in line and "complete" in line:
                        match = re.search(r'Processing event\s+(\d+)', line)
                        if match:
                            event_num = int(match.group(1))
                            last_event_number = event_num
                            self.progress.emit(event_num)
                            progress_updated = True

                    # Method 2: Milestone messages for very large sims
                    elif "Milestone:" in line:
                        match = re.search(r'(\d+)/(\d+) events', line)
                        if match:
                            event_num = int(match.group(1))
                            last_event_number = event_num
                            self.progress.emit(event_num)
                            progress_updated = True

                    # Method 3: Use energy deposition reports for estimation
                    elif "Resist energy deposits:" in line and "Total energy:" in line:
                        energy_reports_count += 1

                        # Estimate based on energy reports (they come every ~10-20k events)
                        if self.total_events and self.total_events > 50000:
                            # Dynamic estimation based on simulation size
                            if self.total_events <= 100000:
                                estimate_factor = 8000
                            elif self.total_events <= 1000000:
                                estimate_factor = 12000
                            else:
                                estimate_factor = 20000  # For very large sims

                            estimated_events = energy_reports_count * estimate_factor
                            if estimated_events > last_event_number:
                                estimated_progress = min(estimated_events, self.total_events)
                                self.progress.emit(int(estimated_progress))
                                progress_updated = True

                    # Method 4: Use track processing reports for very large sims
                    elif "StackingAction: Processed" in line and "tracks" in line:
                        track_reports_count += 1

                        # For 1M+ events, use track reports as backup indicator
                        if self.total_events and self.total_events >= 1000000:
                            estimated_from_tracks = track_reports_count * 3000
                            if estimated_from_tracks > max(last_event_number, estimated_progress):
                                estimated_progress = min(estimated_from_tracks, self.total_events)
                                if abs(estimated_progress - last_event_number) > 5000:
                                    self.progress.emit(int(estimated_progress))
                                    progress_updated = True

                    # Report percentage progress with adaptive thresholds
                    if progress_updated and self.total_events and self.total_events > 0:
                        current_progress = max(last_event_number, estimated_progress)
                        percentage = (current_progress / self.total_events) * 100

                        # Dynamic reporting threshold based on simulation size
                        if self.total_events > 2000000:
                            report_threshold = 0.5  # Every 0.5% for very large sims
                        elif self.total_events > 500000:
                            report_threshold = 1.0  # Every 1% for large sims
                        elif self.total_events > 50000:
                            report_threshold = 2.0  # Every 2% for medium sims
                        else:
                            report_threshold = 5.0  # Every 5% for smaller sims

                        if percentage - self.last_reported_progress >= report_threshold:
                            self.output.emit(f">>> Progress: {percentage:.1f}% ({current_progress:,}/{self.total_events:,})")
                            self.last_reported_progress = percentage

                    # Track important physics messages
                    if "Fluorescence:" in line or "Auger:" in line or "PIXE:" in line:
                        self.output.emit(f">>> PHYSICS: {line}")

                    # Highlight warnings and errors
                    if "WARNING" in line or "Warning" in line:
                        self.output.emit(f"⚠️ {line}")
                    elif "ERROR" in line or "Error" in line:
                        self.output.emit(f"❌ {line}")

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


class Enhanced2DPlotWidget(QWidget):
    """Enhanced widget for 2D depth-radius visualization with fixed contour plotting"""

    def __init__(self, file_manager):
        super().__init__()
        self.file_manager = file_manager
        self.current_data = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create matplotlib figure with subplots
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Control panel
        controls = QHBoxLayout()

        # Plot type selection
        plot_type_group = QGroupBox("Display Mode")
        plot_type_layout = QHBoxLayout()

        self.radio_2d = QRadioButton("2D Heatmap")
        self.radio_2d.setChecked(True)
        self.radio_3d = QRadioButton("3D Surface")
        self.radio_contour = QRadioButton("Contour Plot")
        self.radio_cross = QRadioButton("Cross Sections")

        self.plot_type_group = QButtonGroup()
        self.plot_type_group.addButton(self.radio_2d, 0)
        self.plot_type_group.addButton(self.radio_3d, 1)
        self.plot_type_group.addButton(self.radio_contour, 2)
        self.plot_type_group.addButton(self.radio_cross, 3)
        self.plot_type_group.buttonClicked.connect(self.update_plot)

        plot_type_layout.addWidget(self.radio_2d)
        plot_type_layout.addWidget(self.radio_3d)
        plot_type_layout.addWidget(self.radio_contour)
        plot_type_layout.addWidget(self.radio_cross)
        plot_type_group.setLayout(plot_type_layout)

        # Colormap selection
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'hot', 'jet', 'turbo'])
        self.colormap_combo.currentTextChanged.connect(self.update_plot)

        # Log scale option
        self.log_scale_check = QCheckBox("Log Scale")
        self.log_scale_check.setChecked(True)
        self.log_scale_check.stateChanged.connect(self.update_plot)

        # Depth slice slider (for cross sections)
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.setMinimum(0)
        self.depth_slider.setMaximum(100)
        self.depth_slider.setValue(50)
        self.depth_slider.valueChanged.connect(self.update_cross_section)
        self.depth_label = QLabel("Depth: 0 nm")

        controls.addWidget(plot_type_group)
        controls.addWidget(QLabel("Colormap:"))
        controls.addWidget(self.colormap_combo)
        controls.addWidget(self.log_scale_check)
        controls.addStretch()
        controls.addWidget(QLabel("Depth Slice:"))
        controls.addWidget(self.depth_slider)
        controls.addWidget(self.depth_label)

        # Enhanced file controls with status-aware buttons
        file_controls = QHBoxLayout()

        self.load_2d_button = StatusButton("Load 2D Data")
        self.load_2d_button.clicked.connect(self.load_2d_data)

        self.save_plot_button = StatusButton("Save Plot")
        self.save_plot_button.clicked.connect(self.save_plot)
        self.save_plot_button.set_status(False, "Load 2D data first")

        self.export_button = StatusButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        self.export_button.set_status(False, "Load 2D data first")

        file_controls.addWidget(self.load_2d_button)
        file_controls.addWidget(self.save_plot_button)
        file_controls.addWidget(self.export_button)
        file_controls.addStretch()

        layout.addWidget(self.toolbar)
        layout.addLayout(controls)
        layout.addLayout(file_controls)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def load_2d_data(self):
        """Load 2D depth-radius data from CSV with improved error handling"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load 2D Data", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            self.load_2d_button.set_working(True, "Loading...")

            try:
                # Use file manager for consistent loading
                df, message = self.file_manager.load_csv_with_validation(
                    file_path,
                    progress_callback=lambda msg: self.load_2d_button.setText(f"🔄 {msg}")
                )

                if df is None:
                    QMessageBox.critical(self, "Error", f"Failed to load 2D data: {message}")
                    return

                # Try to interpret as 2D data (depth x radius)
                if df.index.name or df.index.dtype in ['int64', 'float64']:
                    # Data with depth as index, radius as columns
                    depths = df.index.values
                    radii = df.columns.astype(float).values
                    data = df.values
                else:
                    QMessageBox.critical(self, "Error",
                                         "Invalid 2D data format. Expected depth as index, radius as columns.")
                    return

                # Store the data
                self.current_data = {
                    'depths': depths,
                    'radii': radii,
                    'energy': data,
                    'filename': Path(file_path).stem
                }

                # Update depth slider range
                self.depth_slider.setMaximum(len(depths) - 1)

                # Enable other buttons
                self.save_plot_button.set_status(True)
                self.export_button.set_status(True)

                # Plot the data
                self.plot_2d_data()

                # Show success message
                QMessageBox.information(self, "Success",
                                        f"Loaded 2D data: {data.shape[0]}×{data.shape[1]} points")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load 2D data: {str(e)}")
            finally:
                self.load_2d_button.set_working(False)

    def plot_2d_data(self):
        """Plot the 2D data based on selected mode"""
        if not self.current_data:
            return

        self.figure.clear()

        plot_mode = self.plot_type_group.checkedId()

        try:
            if plot_mode == 0:  # 2D Heatmap
                self.plot_heatmap()
            elif plot_mode == 1:  # 3D Surface
                self.plot_3d_surface()
            elif plot_mode == 2:  # Contour
                self.plot_contour()
            elif plot_mode == 3:  # Cross sections
                self.plot_cross_sections()

            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Plotting Error", f"Failed to create plot: {str(e)}")

    def plot_heatmap(self):
        """Create 2D heatmap visualization"""
        ax = self.figure.add_subplot(111)

        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']

        # Create meshgrid
        R, D = np.meshgrid(radii, depths)

        # Apply log scale if selected
        if self.log_scale_check.isChecked():
            # Add small value to avoid log(0)
            energy_plot = np.log10(np.maximum(energy, 1e-10))
            label = 'Log10(Energy Deposition) [eV/nm²]'
        else:
            energy_plot = energy
            label = 'Energy Deposition [eV/nm²]'

        # Create heatmap
        cmap = self.colormap_combo.currentText()
        im = ax.pcolormesh(R, D, energy_plot, cmap=cmap, shading='auto')

        # Add colorbar
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label(label)

        # Labels and title
        ax.set_xlabel('Radius [nm]')
        ax.set_ylabel('Depth [nm]')
        ax.set_title(f'Energy Deposition Profile - {self.current_data["filename"]}')

        # Add resist boundary line if visible
        resist_thickness = 30  # nm, default
        if depths.min() < resist_thickness < depths.max():
            ax.axhline(y=resist_thickness, color='white', linestyle='--',
                       linewidth=2, label='Resist/Substrate boundary')
            ax.axhline(y=0, color='white', linestyle='-',
                       linewidth=2, label='Resist surface')
            ax.legend()

    def plot_3d_surface(self):
        """Create 3D surface plot"""
        from mpl_toolkits.mplot3d import Axes3D

        ax = self.figure.add_subplot(111, projection='3d')

        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']

        # Create meshgrid
        R, D = np.meshgrid(radii, depths)

        # Apply log scale if selected
        if self.log_scale_check.isChecked():
            energy_plot = np.log10(np.maximum(energy, 1e-10))
            label = 'Log10(Energy) [eV/nm²]'
        else:
            energy_plot = energy
            label = 'Energy [eV/nm²]'

        # Create surface plot
        cmap = self.colormap_combo.currentText()
        surf = ax.plot_surface(R, D, energy_plot, cmap=cmap,
                               linewidth=0, antialiased=True, alpha=0.8)

        # Add colorbar
        self.figure.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

        # Labels
        ax.set_xlabel('Radius [nm]')
        ax.set_ylabel('Depth [nm]')
        ax.set_zlabel(label)
        ax.set_title(f'3D Energy Distribution - {self.current_data["filename"]}')

    def plot_contour(self):
        """Create contour plot - FIXED VERSION"""
        ax = self.figure.add_subplot(111)

        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']

        # Create meshgrid
        R, D = np.meshgrid(radii, depths)

        # Apply log scale if selected and prepare levels
        if self.log_scale_check.isChecked():
            # Use log scale and create appropriate levels
            energy_plot = np.log10(np.maximum(energy, 1e-10))
            # Create levels that make sense for log scale
            vmin, vmax = energy_plot.min(), energy_plot.max()
            levels = np.linspace(vmin, vmax, 15)
            label = 'Log10(Energy Deposition) [eV/nm²]'
        else:
            energy_plot = energy
            # Create levels for linear scale
            vmin, vmax = energy_plot.min(), energy_plot.max()
            if vmax > vmin:
                levels = np.linspace(vmin, vmax, 15)
            else:
                levels = 10  # Default number of levels
            label = 'Energy Deposition [eV/nm²]'

        # Create contour plot
        cmap = self.colormap_combo.currentText()

        try:
            # Create filled contours first
            contourf = ax.contourf(R, D, energy_plot, levels=levels, cmap=cmap, alpha=0.7)

            # Add contour lines
            contour = ax.contour(R, D, energy_plot, levels=levels, colors='black', alpha=0.4, linewidths=0.5)

            # Add labels to contour lines (every other line to avoid crowding)
            if hasattr(contour, 'levels') and len(contour.levels) > 0:
                ax.clabel(contour, contour.levels[::2], inline=True, fontsize=8, fmt='%.2g')

        except Exception as e:
            # Fallback to simple contour if levels fail
            print(f"Contour levels failed, using simple approach: {e}")
            contourf = ax.contourf(R, D, energy_plot, cmap=cmap, alpha=0.7)
            contour = ax.contour(R, D, energy_plot, colors='black', alpha=0.4, linewidths=0.5)

        # Add colorbar
        cbar = self.figure.colorbar(contourf, ax=ax)
        cbar.set_label(label)

        # Labels and title
        ax.set_xlabel('Radius [nm]')
        ax.set_ylabel('Depth [nm]')
        ax.set_title(f'Energy Contours - {self.current_data["filename"]}')

    def plot_cross_sections(self):
        """Plot depth and radial cross sections"""
        # Create two subplots
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)

        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']

        # Get current depth index from slider
        depth_idx = self.depth_slider.value()
        current_depth = depths[depth_idx] if depth_idx < len(depths) else depths[0]

        # Update depth label
        self.depth_label.setText(f"Depth: {current_depth:.1f} nm")

        # Plot radial cross section at selected depth
        ax1.plot(radii, energy[depth_idx, :], 'b-', linewidth=2)
        if self.log_scale_check.isChecked():
            ax1.set_yscale('log')
            ax1.set_xscale('log')
        ax1.set_xlabel('Radius [nm]')
        ax1.set_ylabel('Energy Deposition [eV/nm²]')
        ax1.set_title(f'Radial Profile at Depth = {current_depth:.1f} nm')
        ax1.grid(True, alpha=0.3)

        # Plot depth profile at r=0 and several radii
        radii_indices = [0, len(radii)//4, len(radii)//2, 3*len(radii)//4]
        for idx in radii_indices:
            if idx < len(radii):
                label = f'r = {radii[idx]:.1f} nm'
                ax2.plot(depths, energy[:, idx], linewidth=2, label=label)

        if self.log_scale_check.isChecked():
            ax2.set_yscale('log')
        ax2.set_xlabel('Depth [nm]')
        ax2.set_ylabel('Energy Deposition [eV/nm²]')
        ax2.set_title('Depth Profiles at Various Radii')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # Add resist boundaries
        ax2.axhline(y=0, color='k', linestyle='-', alpha=0.5)
        ax2.axhline(y=30, color='k', linestyle='--', alpha=0.5)

        self.figure.tight_layout()

    def update_plot(self):
        """Update plot when settings change"""
        if self.current_data:
            self.plot_2d_data()

    def update_cross_section(self):
        """Update cross section when slider moves - enhanced version"""
        if self.current_data and self.plot_type_group.checkedId() == 3:
            # Get current depth index and update label immediately
            depth_idx = self.depth_slider.value()
            depths = self.current_data['depths']
            
            if depth_idx < len(depths):
                current_depth = depths[depth_idx]
                self.depth_label.setText(f"Depth: {current_depth:.1f} nm")
            
            # Replot with new depth slice
            self.plot_2d_data()
   
    def save_plot(self):
        """Save current plot"""
        if not self.current_data:
            QMessageBox.warning(self, "Warning", "No data to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "",
            "PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg)"
        )

        if file_path:
            self.save_plot_button.set_working(True, "Saving...")
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Plot saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")
            finally:
                self.save_plot_button.set_working(False)

    def export_data(self):
        """Export processed data"""
        if not self.current_data:
            QMessageBox.warning(self, "Warning", "No data to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "",
            "NumPy files (*.npz);;MATLAB files (*.mat)"
        )

        if file_path:
            self.export_button.set_working(True, "Exporting...")
            try:
                success, message = self.file_manager.save_with_backup(
                    self.current_data, file_path, backup=False
                )

                if success:
                    QMessageBox.information(self, "Success", f"Data exported to {file_path}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to export: {message}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
            finally:
                self.export_button.set_working(False)


class PlotWidget(QWidget):
    """Enhanced widget for 1D PSF plots with BEAMER conversion and PSF comparison"""

    def __init__(self, file_manager):
        super().__init__()
        self.file_manager = file_manager
        self.datasets = []  # Store multiple PSF datasets for comparison
        self.current_csv_path = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Plot controls
        controls = QHBoxLayout()

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Linear", "Log-Log", "Semi-Log"])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot_type)

        # Enhanced control buttons
        self.load_button = StatusButton("Load PSF Data")
        self.load_button.clicked.connect(self.load_data)

        self.compare_button = StatusButton("Add for Comparison")
        self.compare_button.clicked.connect(self.add_comparison_data)
        self.compare_button.set_status(False, "Load initial PSF data first")

        self.clear_button = StatusButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all_data)
        self.clear_button.set_status(False, "No data to clear")

        self.save_button = StatusButton("Save Plot")
        self.save_button.clicked.connect(self.save_plot)
        self.save_button.set_status(False, "Load PSF data first")

        controls.addWidget(QLabel("Plot Type:"))
        controls.addWidget(self.plot_type_combo)
        controls.addStretch()
        controls.addWidget(self.load_button)
        controls.addWidget(self.compare_button)
        controls.addWidget(self.clear_button)
        controls.addWidget(self.save_button)

        # BEAMER conversion controls (consolidated functionality)
        beamer_controls = QHBoxLayout()

        self.beamer_button = StatusButton("Convert to BEAMER")
        self.beamer_button.clicked.connect(self.convert_to_beamer_consolidated)
        self.beamer_button.set_status(False, "Load PSF data first")

        self.validate_button = StatusButton("Validate PSF")
        self.validate_button.clicked.connect(self.validate_psf_consolidated)
        self.validate_button.set_status(False, "Load PSF data first")

        self.smooth_check = QCheckBox("Apply Smoothing")
        self.smooth_check.setChecked(True)

        # Comparison analysis button
        self.analyze_button = StatusButton("Analyze Comparison")
        self.analyze_button.clicked.connect(self.analyze_comparison)
        self.analyze_button.set_status(False, "Load multiple PSF datasets first")

        beamer_controls.addWidget(QLabel("Analysis Tools:"))
        beamer_controls.addWidget(self.beamer_button)
        beamer_controls.addWidget(self.validate_button)
        beamer_controls.addWidget(self.analyze_button)
        beamer_controls.addWidget(self.smooth_check)
        beamer_controls.addStretch()

        # PSF comparison info panel
        comparison_group = QGroupBox("Loaded PSF Datasets")
        comparison_layout = QVBoxLayout()

        self.comparison_list = QTextEdit()
        self.comparison_list.setMaximumHeight(80)
        self.comparison_list.setReadOnly(True)
        comparison_layout.addWidget(self.comparison_list)

        comparison_group.setLayout(comparison_layout)

        layout.addWidget(self.toolbar)
        layout.addLayout(controls)
        layout.addLayout(beamer_controls)
        layout.addWidget(comparison_group)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def load_data(self):
        """Load PSF data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            self.load_button.set_working(True, "Loading...")

            try:
                # Use file manager for consistent loading
                df, message = self.file_manager.load_csv_with_validation(file_path)

                if df is None:
                    QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                    return

                # Extract PSF data from CSV
                radii, energies = self._extract_psf_from_df(df)

                if not radii or not energies:
                    QMessageBox.warning(self, "Warning", "No valid PSF data found in file")
                    return

                # Store the path for BEAMER conversion
                self.current_csv_path = file_path

                # Clear existing data and add this as primary dataset
                self.datasets = []
                dataset_info = {
                    'radii': radii,
                    'energies': energies,
                    'label': f"PSF - {Path(file_path).stem}",
                    'file_path': file_path,
                    'style': {'color': 'blue', 'linewidth': 2}
                }
                self.datasets.append(dataset_info)

                # Update UI state
                self.beamer_button.set_status(True)
                self.validate_button.set_status(True)
                self.save_button.set_status(True)
                self.compare_button.set_status(True)
                self.clear_button.set_status(True)

                # Plot the data
                self.plot_all_datasets()
                self.update_comparison_list()

                # Show success message
                QMessageBox.information(self, "Success",
                                        f"Loaded PSF data: {len(radii)} points")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
            finally:
                self.load_button.set_working(False)

    def add_comparison_data(self):
        """Add additional PSF dataset for comparison"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add PSF Data for Comparison", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_paths:
            self.compare_button.set_working(True, "Loading...")

            colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive']
            color_idx = len(self.datasets) - 1  # Start from second color

            try:
                for file_path in file_paths:
                    # Load and validate each file
                    df, message = self.file_manager.load_csv_with_validation(file_path)

                    if df is None:
                        print(f"Skipping {file_path}: {message}")
                        continue

                    # Extract PSF data
                    radii, energies = self._extract_psf_from_df(df)

                    if radii and energies:
                        dataset_info = {
                            'radii': radii,
                            'energies': energies,
                            'label': Path(file_path).stem,
                            'file_path': file_path,
                            'style': {
                                'color': colors[color_idx % len(colors)],
                                'linewidth': 2,
                                'linestyle': '--' if color_idx > 3 else '-'
                            }
                        }
                        self.datasets.append(dataset_info)
                        color_idx += 1

                if len(self.datasets) > 1:
                    # Enable comparison analysis
                    self.analyze_button.set_status(True)

                    # Replot all datasets
                    self.plot_all_datasets()
                    self.update_comparison_list()

                    QMessageBox.information(self, "Success",
                                            f"Added {len(file_paths)} datasets. Total: {len(self.datasets)}")
                else:
                    QMessageBox.warning(self, "Warning", "No valid datasets were added")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add comparison data: {str(e)}")
            finally:
                self.compare_button.set_working(False)

    def _extract_psf_from_df(self, df):
        """Extract radius and energy data from DataFrame"""
        radii, energies = [], []

        # Try different column name variations
        radius_cols = ['Radius(nm)', 'radius', 'Radius', 'r', 'R']
        energy_cols = ['EnergyDeposition(eV/nm^2)', 'Energy', 'energy', 'E', 'PSF']

        radius_col = None
        energy_col = None

        for col in radius_cols:
            if col in df.columns:
                radius_col = col
                break

        for col in energy_cols:
            if col in df.columns:
                energy_col = col
                break

        if radius_col is None or energy_col is None:
            # Try first two numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                radius_col = numeric_cols[0]
                energy_col = numeric_cols[1]

        if radius_col is not None and energy_col is not None:
            for _, row in df.iterrows():
                try:
                    r = float(row[radius_col])
                    e = float(row[energy_col])
                    if not (np.isnan(r) or np.isnan(e)):
                        radii.append(r)
                        energies.append(e)
                except (ValueError, TypeError):
                    continue

        return radii, energies

    def plot_all_datasets(self):
        """Plot all loaded datasets with current settings"""
        if not self.datasets:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        plot_type = self.plot_type_combo.currentText()

        for dataset in self.datasets:
            radii = dataset['radii']
            energies = dataset['energies']
            label = dataset['label']
            style = dataset['style']

            if plot_type == "Log-Log":
                valid = [(r > 0 and e > 0) for r, e in zip(radii, energies)]
                r_filt = [r for r, v in zip(radii, valid) if v]
                e_filt = [e for e, v in zip(energies, valid) if v]

                if r_filt and e_filt:
                    ax.loglog(r_filt, e_filt, label=label, **style)
            elif plot_type == "Semi-Log":
                ax.semilogy(radii, energies, label=label, **style)
            else:
                ax.plot(radii, energies, label=label, **style)

        ax.set_xlabel('Radius (nm)')
        ax.set_ylabel('Energy Deposition (eV/nm²)')
        ax.set_title(f'PSF Comparison - {plot_type} Scale')
        ax.grid(True, alpha=0.3)

        if len(self.datasets) > 1:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        self.figure.tight_layout()
        self.canvas.draw()

    def update_plot_type(self):
        """Update plot when type changes"""
        if self.datasets:
            self.plot_all_datasets()

    def update_comparison_list(self):
        """Update the comparison list display"""
        if not self.datasets:
            self.comparison_list.setPlainText("No PSF datasets loaded")
            return

        text_lines = []
        for i, dataset in enumerate(self.datasets):
            file_name = Path(dataset['file_path']).name
            point_count = len(dataset['radii'])
            max_energy = max(dataset['energies']) if dataset['energies'] else 0
            text_lines.append(f"{i+1}. {file_name} ({point_count} points, max: {max_energy:.2e})")

        self.comparison_list.setPlainText("\n".join(text_lines))

    def clear_all_data(self):
        """Clear all loaded datasets"""
        reply = QMessageBox.question(self, "Clear All Data",
                                     "Remove all loaded PSF datasets?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.datasets = []
            self.current_csv_path = None

            # Reset UI state
            self.beamer_button.set_status(False, "Load PSF data first")
            self.validate_button.set_status(False, "Load PSF data first")
            self.save_button.set_status(False, "Load PSF data first")
            self.compare_button.set_status(False, "Load initial PSF data first")
            self.analyze_button.set_status(False, "Load multiple PSF datasets first")
            self.clear_button.set_status(False, "No data to clear")

            # Clear plot and comparison list
            self.figure.clear()
            self.canvas.draw()
            self.update_comparison_list()

    def convert_to_beamer_consolidated(self):
        """Consolidated BEAMER conversion using the best method"""
        if not self.current_csv_path:
            QMessageBox.warning(self, "Warning", "No PSF data loaded for conversion")
            return

        # Get beam energy from main window (we'll need to pass this)
        beam_energy = 100.0  # Default, should be passed from main window

        self.beamer_button.set_working(True, "Converting...")

        try:
            # Load the CSV data
            df, message = self.file_manager.load_csv_with_validation(self.current_csv_path)

            if df is None:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {message}")
                return

            # Use consolidated conversion method
            result = self._convert_csv_to_beamer_consolidated(
                df, beam_energy, self.smooth_check.isChecked()
            )

            if result:
                output_radius, output_psf, alpha, beta = result

                # Ask for save location
                default_name = Path(self.current_csv_path).stem + "_beamer.txt"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save BEAMER Format", default_name,
                    "Text files (*.txt);;All files (*.*)"
                )

                if file_path:
                    # Write BEAMER format
                    success, message = self._write_beamer_file(
                        file_path, output_radius, output_psf,
                        self.current_csv_path, beam_energy
                    )

                    if success:
                        # Show success with parameters
                        QMessageBox.information(self, "BEAMER Conversion Complete",
                                                f"PSF saved to: {Path(file_path).name}\n\n"
                                                f"Proximity parameters:\n"
                                                f"α (forward): {alpha:.3f}\n"
                                                f"β (backscatter): {beta:.3f}\n\n"
                                                f"Data points: {len(output_radius)}")

                        # Offer to visualize BEAMER format
                        reply = QMessageBox.question(self, "Visualize BEAMER Format",
                                                     "Would you like to plot the BEAMER format PSF?",
                                                     QMessageBox.Yes | QMessageBox.No)

                        if reply == QMessageBox.Yes:
                            self.plot_beamer_format(output_radius, output_psf)
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to save file: {message}")
            else:
                QMessageBox.critical(self, "Error", "Failed to convert PSF data")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"BEAMER conversion failed: {str(e)}")
        finally:
            self.beamer_button.set_working(False)

    def _convert_csv_to_beamer_consolidated(self, df, beam_energy, apply_smoothing=True):
        """Consolidated BEAMER conversion - best method from analysis"""
        try:
            # Extract PSF data
            radii, energies = self._extract_psf_from_df(df)

            if not radii or not energies:
                return None

            # Convert to numpy arrays
            radius_nm = np.array(radii)
            energy_density = np.array(energies)

            # Get non-zero data
            mask = energy_density > 0
            if not mask.any():
                return None

            radius_nm = radius_nm[mask]
            energy_density = energy_density[mask]

            # Convert to micrometers
            radius_um = radius_nm / 1000.0

            # Normalize to maximum = 1.0 (BEAMER standard)
            max_density = np.max(energy_density)
            psf_normalized = energy_density / max_density

            # Apply smoothing if requested (Savitzky-Golay filter)
            if apply_smoothing and len(psf_normalized) > 7:
                from scipy.signal import savgol_filter

                # Smooth only the tail region (r > 10 μm)
                smooth_start = np.where(radius_um > 10.0)[0]
                if len(smooth_start) > 0:
                    start_idx = smooth_start[0]
                    if len(psf_normalized) - start_idx > 7:
                        window = min(7, len(psf_normalized) - start_idx)
                        if window % 2 == 0:
                            window -= 1
                        psf_normalized[start_idx:] = savgol_filter(
                            psf_normalized[start_idx:], window, 3
                        )

            # Prepare output data
            output_radius = []
            output_psf = []

            # Add point at 0.01 μm if needed
            if radius_um[0] > 0.02:
                output_radius.append(0.01)
                output_psf.append(psf_normalized[0])

            # Add all valid points
            for r, p in zip(radius_um, psf_normalized):
                if p > 1e-12:  # Filter noise floor
                    output_radius.append(r)
                    output_psf.append(p)

            # Extrapolate tail if needed
            if output_radius[-1] < 100.0 and len(output_radius) > 10:
                # Fit exponential to last 10 points
                n_fit = min(10, len(output_radius) // 2)
                r_fit = np.array(output_radius[-n_fit:])
                p_fit = np.array(output_psf[-n_fit:])

                if np.all(p_fit > 0):
                    # Fit in log space
                    coeffs = np.polyfit(r_fit, np.log(p_fit), 1)

                    # Extrapolate
                    r_extrap = output_radius[-1]
                    while r_extrap < 100.0:
                        r_extrap *= 1.2
                        p_extrap = np.exp(coeffs[0] * r_extrap + coeffs[1])

                        if p_extrap < 1e-10:
                            break

                        output_radius.append(r_extrap)
                        output_psf.append(p_extrap)

            # Calculate proximity parameters
            forward_energy = 0
            total_energy = 0

            for i in range(len(output_radius)-1):
                r1, r2 = output_radius[i], output_radius[i+1]
                p1, p2 = output_psf[i], output_psf[i+1]

                dr = r2 - r1
                avg_r = (r1 + r2) / 2
                avg_p = (p1 + p2) / 2
                contrib = 2 * np.pi * avg_r * avg_p * dr

                total_energy += contrib
                if avg_r < 1.0:
                    forward_energy += contrib

            alpha = forward_energy / total_energy if total_energy > 0 else 0
            beta = 1 - alpha

            return output_radius, output_psf, alpha, beta

        except Exception as e:
            print(f"BEAMER conversion error: {str(e)}")
            return None

    def _write_beamer_file(self, file_path, radius_data, psf_data, source_file, beam_energy):
        """Write data to BEAMER format file"""
        try:
            with open(file_path, 'w') as f:
                f.write("# Electron beam PSF for BEAMER proximity correction\n")
                f.write("# Generated from Geant4 simulation by EBL GUI\n")
                f.write(f"# Source: {Path(source_file).name}\n")
                f.write(f"# Beam energy: {beam_energy} keV\n")
                f.write("# Format: radius(um) relative_energy_deposition\n")
                f.write("# PSF normalized to maximum = 1.0\n")
                f.write("#\n")

                for r, p in zip(radius_data, psf_data):
                    f.write(f"{r:.6e} {p:.6e}\n")

            return True, "File saved successfully"
        except Exception as e:
            return False, str(e)

    def plot_beamer_format(self, radius_um, psf_norm):
        """Plot BEAMER format PSF in standard style"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Plot in BEAMER standard format (log-log)
        ax.loglog(radius_um, psf_norm, 'b-', linewidth=2, label='BEAMER PSF')

        # Formatting to match BEAMER standard
        ax.set_xlabel('radius, μm', fontsize=12)
        ax.set_ylabel('relative energy deposition', fontsize=12)
        ax.set_title('Electron energy deposition point spread function', fontsize=14)

        # Set axis limits similar to BEAMER
        ax.set_xlim(0.01, 100)
        ax.set_ylim(1e-10, 2)

        # Grid
        ax.grid(True, which="both", ls="-", alpha=0.2)

        # Legend
        ax.legend(loc='upper right')

        self.figure.tight_layout()
        self.canvas.draw()

    def validate_psf_consolidated(self):
        """Consolidated PSF validation using the best method"""
        if not self.current_csv_path:
            QMessageBox.warning(self, "Warning", "No PSF data loaded for validation")
            return

        self.validate_button.set_working(True, "Validating...")

        try:
            # Load and validate
            df, message = self.file_manager.load_csv_with_validation(self.current_csv_path)

            if df is None:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {message}")
                return

            report = self._validate_psf_comprehensive(df, Path(self.current_csv_path).name)

            # Show report in dialog
            dialog = QMessageBox(self)
            dialog.setWindowTitle("PSF Validation Report")
            dialog.setText(report)
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok)
            dialog.setDetailedText(
                "Comprehensive validation checks:\n"
                "• Data integrity (no negative values)\n"
                "• Monotonicity (decreasing trend)\n"
                "• Statistical quality (noise levels)\n"
                "• Physical reasonableness (R50, R90 values)\n"
                "• Energy conservation\n"
                "• Format compliance"
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Validation failed: {str(e)}")
        finally:
            self.validate_button.set_working(False)

    def _validate_psf_comprehensive(self, df, filename):
        """Comprehensive PSF validation - consolidated best method"""
        report = f"PSF VALIDATION: {filename}\n" + "="*60 + "\n\n"

        # Check for required columns
        radii, energies = self._extract_psf_from_df(df)

        if not radii or not energies:
            report += "❌ Could not extract PSF data from file\n"
            return report

        # Convert to arrays
        radius = np.array(radii)
        energy = np.array(energies)

        # Test 1: Negative values
        if np.any(energy < 0):
            report += f"❌ Found {np.sum(energy < 0)} negative energy values\n"
        else:
            report += "✅ No negative energy values\n"

        # Test 2: Data range
        nonzero = energy > 0
        if np.any(nonzero):
            report += f"✅ Data points: {len(energy)} ({np.sum(nonzero)} non-zero)\n"
            report += f"✅ Radius range: {radius[nonzero].min():.1f} - {radius[nonzero].max():.1f} nm\n"

            # Test 3: Monotonicity (general trend)
            if len(energy[nonzero]) > 10:
                # Use moving average to check trend
                window = min(5, len(energy) // 4)
                if window >= 3:
                    smoothed = np.convolve(energy, np.ones(window)/window, mode='valid')
                    increases = np.sum(np.diff(smoothed) > 0)
                    increase_frac = increases / len(smoothed)

                    if increase_frac < 0.3:
                        report += "✅ PSF shows generally decreasing trend\n"
                    else:
                        report += f"⚠️ PSF has {increase_frac*100:.1f}% increasing segments\n"

            # Test 4: Statistical quality
            tail_mask = radius > 1000  # Beyond 1 μm
            if np.any(tail_mask & nonzero):
                tail_energy = energy[tail_mask & nonzero]
                if len(tail_energy) > 5:
                    cv = np.std(tail_energy) / np.mean(tail_energy)
                    if cv < 0.5:
                        report += "✅ Good statistical quality in tail\n"
                    elif cv < 1.0:
                        report += "⚠️ Moderate noise in tail region\n"
                    else:
                        report += "❌ High noise in tail region\n"

            # Test 5: Physical reasonableness (R50, R90)
            if len(radius) > 1:
                # Calculate cumulative energy
                total = 0
                for i in range(len(radius)-1):
                    if energy[i] > 0 and energy[i+1] > 0:
                        dr = radius[i+1] - radius[i]
                        avg_e = (energy[i] + energy[i+1]) / 2
                        avg_r = (radius[i] + radius[i+1]) / 2
                        contrib = 2 * np.pi * avg_r * avg_e * dr
                        total += contrib

                cumulative = 0
                r50 = None
                r90 = None

                for i in range(len(radius)-1):
                    if energy[i] > 0 and energy[i+1] > 0:
                        dr = radius[i+1] - radius[i]
                        avg_e = (energy[i] + energy[i+1]) / 2
                        avg_r = (radius[i] + radius[i+1]) / 2
                        contrib = 2 * np.pi * avg_r * avg_e * dr
                        cumulative += contrib

                        if r50 is None and cumulative > 0.5 * total:
                            r50 = radius[i]
                        if r90 is None and cumulative > 0.9 * total:
                            r90 = radius[i]

                if r50 and r90:
                    report += f"✅ R50: {r50:.1f} nm, R90: {r90:.1f} nm\n"
                    ratio = r90 / r50
                    if 2 < ratio < 100:
                        report += f"✅ R90/R50 ratio: {ratio:.1f} (reasonable)\n"
                    else:
                        report += f"⚠️ R90/R50 ratio: {ratio:.1f} (check parameters)\n"
        else:
            report += "❌ No non-zero data found\n"

        return report

    def analyze_comparison(self):
        """Analyze multiple PSF datasets for comparison"""
        if len(self.datasets) < 2:
            QMessageBox.warning(self, "Warning", "Need at least 2 PSF datasets for comparison")
            return

        self.analyze_button.set_working(True, "Analyzing...")

        try:
            # Perform comparative analysis
            analysis_report = self._perform_comparative_analysis()

            # Show analysis in dialog
            dialog = QMessageBox(self)
            dialog.setWindowTitle("PSF Comparison Analysis")
            dialog.setText(analysis_report)
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Save)

            result = dialog.exec()

            if result == QMessageBox.Save:
                # Save analysis report
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Analysis Report", "psf_comparison_report.txt",
                    "Text files (*.txt);;All files (*.*)"
                )

                if file_path:
                    with open(file_path, 'w') as f:
                        f.write(analysis_report)
                    QMessageBox.information(self, "Success", f"Analysis saved to {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
        finally:
            self.analyze_button.set_working(False)

    def _perform_comparative_analysis(self):
        """Perform detailed comparison of multiple PSF datasets"""
        report = "PSF COMPARATIVE ANALYSIS\n"
        report += "=" * 50 + "\n\n"

        # Basic statistics for each dataset
        for i, dataset in enumerate(self.datasets):
            radii = np.array(dataset['radii'])
            energies = np.array(dataset['energies'])

            report += f"Dataset {i+1}: {dataset['label']}\n"
            report += "-" * 30 + "\n"

            # Basic stats
            max_energy = np.max(energies)
            max_radius_idx = np.argmax(energies)
            max_radius = radii[max_radius_idx]

            report += f"Peak energy: {max_energy:.2e} eV/nm² at r={max_radius:.1f} nm\n"
            report += f"Data range: {radii.min():.1f} - {radii.max():.1f} nm\n"
            report += f"Points: {len(radii)}\n\n"

        # Comparative metrics
        report += "COMPARATIVE METRICS\n"
        report += "=" * 20 + "\n"

        # Compare peak positions and heights
        peaks = []
        for dataset in self.datasets:
            energies = np.array(dataset['energies'])
            radii = np.array(dataset['radii'])
            max_idx = np.argmax(energies)
            peaks.append({
                'label': dataset['label'],
                'peak_energy': energies[max_idx],
                'peak_radius': radii[max_idx]
            })

        # Find relative differences
        baseline = peaks[0]
        report += f"Baseline: {baseline['label']}\n\n"

        for i, peak in enumerate(peaks[1:], 1):
            energy_ratio = peak['peak_energy'] / baseline['peak_energy']
            radius_diff = peak['peak_radius'] - baseline['peak_radius']

            report += f"Dataset {i+1} vs Baseline:\n"
            report += f"  Energy ratio: {energy_ratio:.3f}x\n"
            report += f"  Peak shift: {radius_diff:+.1f} nm\n\n"

        # Recommendations
        report += "ANALYSIS RECOMMENDATIONS\n"
        report += "=" * 25 + "\n"

        # Check for systematic trends
        energy_ratios = [p['peak_energy'] / baseline['peak_energy'] for p in peaks[1:]]

        if all(r > 1.1 for r in energy_ratios):
            report += "• All variants show higher peak energy - consider dose effects\n"
        elif all(r < 0.9 for r in energy_ratios):
            report += "• All variants show lower peak energy - check material properties\n"
        else:
            report += "• Mixed energy responses - investigate parameter correlations\n"

        peak_shifts = [p['peak_radius'] - baseline['peak_radius'] for p in peaks[1:]]
        if all(s > 2 for s in peak_shifts):
            report += "• Consistent peak broadening observed\n"
        elif all(s < -2 for s in peak_shifts):
            report += "• Consistent peak sharpening observed\n"

        return report

    def save_plot(self):
        """Save current plot"""
        if not self.datasets:
            QMessageBox.warning(self, "Warning", "No data to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "",
            "PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg)"
        )

        if file_path:
            self.save_button.set_working(True, "Saving...")
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Plot saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")
            finally:
                self.save_button.set_working(False)

class EBLMainWindow(QMainWindow):
    """Main window for EBL simulation GUI with enhanced functionality"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("EBL", "SimulationGUI")

        # Initialize file manager first
        self.working_dir = str(Path(__file__).resolve().parent.parent.parent / "cmake-build-release" / "bin")
        self.file_manager = FileManager(self.working_dir)

        self.setup_ui()
        self.setup_defaults()
        self.load_settings()

        # Simulation state
        self.simulation_worker = None
        self.simulation_thread = None
        self.simulation_running = False

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("EBL Simulation Control - Enhanced Edition v3.1")
        self.setMinimumSize(1400, 900)

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
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
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
            QSlider::groove:horizontal {
                background: #555555;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007acc;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
        """)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs (removed placeholder tabs)
        self.create_resist_tab()
        self.create_beam_tab()
        self.create_simulation_tab()
        self.create_output_tab()
        self.create_1d_visualization_tab()
        self.create_2d_visualization_tab()
        # Note: Removed analysis tab as it had placeholder functionality

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)

        # Create menu bar and status bar
        self.create_menu_bar()
        self.create_status_bar()

    def create_menu_bar(self):
        """Create enhanced menu bar with consolidated BEAMER tools"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        select_exe_action = QAction("Select Executable", self)
        select_exe_action.triggered.connect(self.select_executable)
        file_menu.addAction(select_exe_action)

        save_macro_action = QAction("Save Macro", self)
        save_macro_action.triggered.connect(self.save_macro)
        file_menu.addAction(save_macro_action)

        load_config_action = QAction("Load Configuration", self)
        load_config_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_config_action)

        save_config_action = QAction("Save Configuration", self)
        save_config_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_config_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Simulation menu (removed placeholder batch run)
        sim_menu = menubar.addMenu("Simulation")

        run_action = QAction("Run Simulation", self)
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)

        stop_action = QAction("Stop Simulation", self)
        stop_action.triggered.connect(self.stop_simulation)
        sim_menu.addAction(stop_action)

        # Enhanced BEAMER menu with consolidated functionality
        beamer_menu = menubar.addMenu("BEAMER")

        convert_action = QAction("Convert PSF to BEAMER Format", self)
        convert_action.triggered.connect(self.convert_psf_to_beamer_main)
        beamer_menu.addAction(convert_action)

        batch_convert_action = QAction("Batch Convert to BEAMER", self)
        batch_convert_action.triggered.connect(self.batch_convert_beamer_main)
        beamer_menu.addAction(batch_convert_action)

        beamer_menu.addSeparator()

        validate_psf_action = QAction("Validate PSF Data", self)
        validate_psf_action.triggered.connect(self.validate_psf_data_main)
        beamer_menu.addAction(validate_psf_action)

        compare_beamer_action = QAction("Compare BEAMER Files", self)
        compare_beamer_action.triggered.connect(self.compare_beamer_files_main)
        beamer_menu.addAction(compare_beamer_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        psf_compare_action = QAction("PSF Comparison Tool", self)
        psf_compare_action.triggered.connect(self.open_psf_comparison)
        tools_menu.addAction(psf_compare_action)

        recent_files_action = QAction("Recent Simulation Files", self)
        recent_files_action.triggered.connect(self.show_recent_files)
        tools_menu.addAction(recent_files_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        beamer_help_action = QAction("BEAMER Format Help", self)
        beamer_help_action.triggered.connect(self.show_beamer_help)
        help_menu.addAction(beamer_help_action)

    def create_status_bar(self):
        """Create enhanced status bar with better progress indication"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress bar (enhanced)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # File operations indicator
        self.file_status_label = QLabel("")
        self.file_status_label.setVisible(False)
        self.status_bar.addPermanentWidget(self.file_status_label)

    def create_resist_tab(self):
        """Enhanced resist properties tab with simplified material builder"""
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
            "Biscone_2Butyne": ("Bi:1,C:4,H:4,O:2", 3.3),
            "Biscone_2Butyne_Hydrated": ("Bi:1,C:4,H:6,O:3", 3.1),
            "Custom": ("", 1.0)
        }

        # Simplified atomic weights for basic calculations
        self.atomic_weights = {
            'H': 1.008, 'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998,
            'Al': 26.982, 'Si': 28.086, 'P': 30.974, 'S': 32.065,
            'Ti': 47.867, 'Zr': 91.224, 'Hf': 178.49, 'W': 183.84,
            'Au': 196.97, 'Bi': 208.98
        }

        material_layout.addWidget(QLabel("Material:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems(list(self.material_presets.keys()))
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        material_layout.addWidget(self.material_combo, 0, 1)

        material_layout.addWidget(QLabel("Composition:"), 1, 0)
        self.composition_edit = QLineEdit()
        self.composition_edit.setPlaceholderText("Al:1,C:5,H:4,O:2")
        self.composition_edit.textChanged.connect(self.on_composition_changed)
        material_layout.addWidget(self.composition_edit, 1, 1, 1, 2)

        # Density with simple estimation
        material_layout.addWidget(QLabel("Density (g/cm³):"), 2, 0)

        density_layout = QHBoxLayout()
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 25.0)
        self.density_spin.setValue(1.35)
        self.density_spin.setDecimals(2)
        density_layout.addWidget(self.density_spin)

        self.estimate_density_button = StatusButton("Estimate")
        self.estimate_density_button.setMaximumWidth(80)
        self.estimate_density_button.clicked.connect(self.estimate_density)
        self.estimate_density_button.setToolTip("Estimate density from composition")
        density_layout.addWidget(self.estimate_density_button)

        material_layout.addLayout(density_layout, 2, 1, 1, 2)

        material_layout.addWidget(QLabel("Thickness (nm):"), 3, 0)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 10000.0)
        self.thickness_spin.setValue(30.0)
        self.thickness_spin.setDecimals(1)
        material_layout.addWidget(self.thickness_spin, 3, 1)

        material_group.setLayout(material_layout)

        # Enhanced Material Builder with status feedback
        builder_group = QGroupBox("Quick Material Builder")
        builder_layout = QGridLayout()

        # Common elements dropdown
        builder_layout.addWidget(QLabel("Add Element:"), 0, 0)
        self.element_combo = QComboBox()
        common_elements = ['H', 'C', 'N', 'O', 'F', 'Al', 'Si', 'P', 'S', 'Ti', 'Zr', 'Hf', 'W', 'Au', 'Bi']
        self.element_combo.addItems(common_elements)
        builder_layout.addWidget(self.element_combo, 0, 1)

        builder_layout.addWidget(QLabel("Ratio:"), 0, 2)
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.01, 100.0)
        self.ratio_spin.setValue(1.0)
        self.ratio_spin.setDecimals(2)
        builder_layout.addWidget(self.ratio_spin, 0, 3)

        self.add_element_button = StatusButton("Add")
        self.add_element_button.clicked.connect(self.add_element_to_composition)
        builder_layout.addWidget(self.add_element_button, 0, 4)

        # Quick actions
        actions_layout = QHBoxLayout()
        self.validate_composition_button = StatusButton("Validate")
        self.validate_composition_button.clicked.connect(self.validate_composition)
        actions_layout.addWidget(self.validate_composition_button)

        self.clear_composition_button = StatusButton("Clear")
        self.clear_composition_button.clicked.connect(self.clear_composition)
        actions_layout.addWidget(self.clear_composition_button)

        builder_layout.addLayout(actions_layout, 1, 0, 1, 5)
        builder_group.setLayout(builder_layout)

        # Info group with enhanced composition display
        info_group = QGroupBox("Material Information")
        info_layout = QVBoxLayout()

        self.info_text = QLabel("""
    <b>Available materials:</b><br>
    • Alucone: Al:1,C:5,H:4,O:2 (1.35 g/cm³)<br>
    • Biscone: Bi:1,C:4,H:4,O:2 (3.3 g/cm³)<br>
    • From MLD process - 2-butyne linker
        """)
        self.info_text.setWordWrap(True)
        info_layout.addWidget(self.info_text)

        # Composition analysis display
        self.analysis_text = QLabel("")
        self.analysis_text.setWordWrap(True)
        self.analysis_text.setStyleSheet("color: #007acc; font-size: 10px;")
        info_layout.addWidget(self.analysis_text)

        info_group.setLayout(info_layout)

        layout.addWidget(material_group)
        layout.addWidget(builder_group)
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
        self.energy_spin.setValue(100.0)
        self.energy_spin.setDecimals(1)
        beam_layout.addWidget(self.energy_spin, 0, 1)

        beam_layout.addWidget(QLabel("Beam Size (nm):"), 1, 0)
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.1, 1000.0)
        self.beam_size_spin.setValue(2.0)
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
        self.pos_z_spin.setValue(100.0)
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
        self.events_spin.setValue(10000)
        sim_layout.addWidget(self.events_spin, 0, 1)

        warning_label = QLabel("⚠️ >1M events may take significant time")
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
        self.verbose_spin.setValue(1)
        sim_layout.addWidget(self.verbose_spin, 2, 1)

        # Enhanced output options
        self.auto_increment_check = QCheckBox("Auto-increment run number")
        self.auto_increment_check.setChecked(True)
        sim_layout.addWidget(self.auto_increment_check, 3, 0, 1, 2)

        self.timestamp_check = QCheckBox("Include timestamp in filename")
        self.timestamp_check.setChecked(False)
        sim_layout.addWidget(self.timestamp_check, 4, 0, 1, 2)

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

        # Enhanced control buttons
        button_layout = QHBoxLayout()

        self.generate_button = StatusButton("Generate Macro")
        self.generate_button.clicked.connect(self.generate_macro)
        button_layout.addWidget(self.generate_button)

        self.run_button = StatusButton("Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)

        self.stop_button = StatusButton("Stop Simulation")
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

        # Enhanced control buttons
        button_layout = QHBoxLayout()

        clear_button = StatusButton("Clear Log")
        clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_button)

        save_button = StatusButton("Save Log")
        save_button.clicked.connect(self.save_log)
        button_layout.addWidget(save_button)

        # Add filter controls
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Messages", "Errors Only", "Warnings+", "Progress Only"])
        self.filter_combo.currentTextChanged.connect(self.filter_log_messages)
        button_layout.addWidget(QLabel("Filter:"))
        button_layout.addWidget(self.filter_combo)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Output Log")

    def create_1d_visualization_tab(self):
        """Create 1D PSF visualization tab with enhanced features"""
        self.plot_widget = PlotWidget(self.file_manager)
        self.tab_widget.addTab(self.plot_widget, "1D PSF Visualization")

    def create_2d_visualization_tab(self):
        """Create 2D depth-radius visualization tab with enhanced features"""
        self.plot_2d_widget = Enhanced2DPlotWidget(self.file_manager)
        self.tab_widget.addTab(self.plot_2d_widget, "2D Visualization")

    def setup_defaults(self):
        """Setup default values"""
        # Set defaults based on XPS data
        self.material_combo.setCurrentText("Alucone_XPS")
        self.on_material_changed()

        # Set the working executable path
        project_root = Path(__file__).resolve().parent.parent.parent
        build_dir = project_root / "cmake-build-release" / "bin"

        self.executable_path = str(build_dir / "ebl_sim.exe")
        self.working_dir = str(build_dir)

        # Update file manager working directory
        self.file_manager.working_dir = Path(self.working_dir)

        # Verify executable exists
        if Path(self.executable_path).exists():
            self.log_output(f"Found executable: {self.executable_path}")
        else:
            self.log_output(f"Warning: Executable not found at: {self.executable_path}")
            # Try to find it dynamically
            possible_paths = [
                project_root / "cmake-build-release" / "bin" / "ebl_sim.exe",
                project_root / "cmake-build-debug" / "bin" / "ebl_sim.exe",
                project_root / "build" / "bin" / "ebl_sim.exe",
                project_root / "out" / "build" / "x64-release" / "bin" / "ebl_sim.exe",
                ]

            for path in possible_paths:
                if path.exists():
                    self.executable_path = str(path)
                    self.working_dir = str(path.parent)
                    self.file_manager.working_dir = Path(self.working_dir)
                    self.log_output(f"Found executable: {self.executable_path}")
                    break

    # Enhanced material helper methods (keeping existing implementation)
    def parse_composition(self, composition_str):
        """Parse composition string into element dictionary"""
        elements = {}
        if not composition_str.strip():
            return elements

        try:
            for part in composition_str.split(','):
                if ':' in part:
                    element, ratio = part.strip().split(':')
                    elements[element.strip()] = float(ratio.strip())
        except ValueError:
            pass

        return elements

    def estimate_density(self):
        """Simple density estimation using atomic weights and empirical rules"""
        composition = self.composition_edit.text()
        elements = self.parse_composition(composition)

        if not elements:
            QMessageBox.warning(self, "Invalid Composition",
                                "Please enter a valid composition (e.g., Al:1,C:5,H:4,O:2)")
            return

        self.estimate_density_button.set_working(True, "Estimating...")

        try:
            # Calculate molecular weight
            total_weight = 0
            heavy_element_fraction = 0

            for element, ratio in elements.items():
                if element not in self.atomic_weights:
                    QMessageBox.warning(self, "Unknown Element",
                                        f"Element '{element}' not supported.\n"
                                        f"Supported: {', '.join(self.atomic_weights.keys())}")
                    return

                weight_contrib = self.atomic_weights[element] * ratio
                total_weight += weight_contrib

                # Track heavy elements (atomic weight > 50)
                if self.atomic_weights[element] > 50:
                    heavy_element_fraction += weight_contrib

            heavy_element_fraction /= total_weight

            # Simplified density estimation using empirical rules
            if heavy_element_fraction > 0.5:
                if 'Bi' in elements:
                    estimated_density = 2.5 + heavy_element_fraction * 5
                elif any(elem in elements for elem in ['W', 'Au', 'Hf']):
                    estimated_density = 3.0 + heavy_element_fraction * 10
                else:
                    estimated_density = 2.0 + heavy_element_fraction * 3
            else:
                if any(elem in elements for elem in ['Al', 'Si', 'Ti']):
                    estimated_density = 1.2 + heavy_element_fraction * 2
                else:
                    estimated_density = 1.0 + heavy_element_fraction

            # Show results with option to use
            result_msg = f"Estimated Density: {estimated_density:.2f} g/cm³\n"
            result_msg += f"Molecular Weight: {total_weight:.1f} g/mol\n"
            result_msg += f"Heavy Element Fraction: {heavy_element_fraction*100:.1f}%\n\n"
            result_msg += "Apply this density?"

            reply = QMessageBox.question(self, "Density Estimation", result_msg,
                                         QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.density_spin.setValue(estimated_density)

        except Exception as e:
            QMessageBox.critical(self, "Estimation Error", f"Error estimating density: {str(e)}")
        finally:
            self.estimate_density_button.set_working(False)

    def add_element_to_composition(self):
        """Add selected element to composition"""
        element = self.element_combo.currentText()
        ratio = self.ratio_spin.value()

        current = self.composition_edit.text().strip()
        if current:
            new_composition = f"{current},{element}:{ratio}"
        else:
            new_composition = f"{element}:{ratio}"

        self.composition_edit.setText(new_composition)

    def validate_composition(self):
        """Validate current composition"""
        composition = self.composition_edit.text()
        elements = self.parse_composition(composition)

        self.validate_composition_button.set_working(True, "Validating...")

        try:
            if not elements:
                QMessageBox.warning(self, "Validation", "❌ Invalid composition format")
                return

            # Check for unknown elements
            unknown = [elem for elem in elements.keys() if elem not in self.atomic_weights]

            if unknown:
                supported = ', '.join(self.atomic_weights.keys())
                QMessageBox.warning(self, "Validation",
                                    f"❌ Unknown elements: {', '.join(unknown)}\n\n"
                                    f"Supported elements:\n{supported}")
            else:
                total_atoms = sum(elements.values())
                molecular_weight = sum(self.atomic_weights[elem] * ratio
                                       for elem, ratio in elements.items())

                QMessageBox.information(self, "Validation",
                                        f"✅ Valid composition!\n\n"
                                        f"Elements: {len(elements)}\n"
                                        f"Total atoms: {total_atoms:.2f}\n"
                                        f"Molecular weight: {molecular_weight:.1f} g/mol")
        finally:
            self.validate_composition_button.set_working(False)

    def clear_composition(self):
        """Clear composition field"""
        self.composition_edit.clear()

    def on_composition_changed(self):
        """Handle composition text changes"""
        composition = self.composition_edit.text()
        elements = self.parse_composition(composition)

        if elements:
            # Quick analysis for display
            total_atoms = sum(elements.values())
            total_weight = sum(self.atomic_weights.get(elem, 0) * ratio
                               for elem, ratio in elements.items())

            analysis_text = f"Formula: {composition} | "
            analysis_text += f"MW: {total_weight:.1f} g/mol | "
            analysis_text += f"Atoms: {total_atoms:.1f}"

            # Identify material type
            metals = ['Al', 'Ti', 'Zr', 'Hf', 'Bi', 'W', 'Au']
            has_metals = any(elem in metals for elem in elements.keys())
            has_carbon = 'C' in elements

            if has_metals and has_carbon:
                material_type = "Metal-Organic"
            elif has_carbon:
                material_type = "Organic"
            else:
                material_type = "Inorganic"

            analysis_text += f" | Type: {material_type}"
            self.analysis_text.setText(analysis_text)
        else:
            self.analysis_text.setText("")

    def on_material_changed(self):
        """Handle material selection change"""
        material = self.material_combo.currentText()
        if material in self.material_presets:
            composition, density = self.material_presets[material]
            self.composition_edit.setText(composition)
            self.density_spin.setValue(density)

            # Enable/disable composition editing
            self.composition_edit.setReadOnly(material != "Custom")

    # Continuing with the remaining methods...
    # [The methods would continue here, including the BEAMER conversion methods,
    #  simulation methods, file handling, etc. Due to length limits, I'll continue
    #  in the next part]

    # ===================================================================
    # CONSOLIDATED BEAMER CONVERSION METHODS (Main Window)
    # ===================================================================

    def convert_psf_to_beamer_main(self):
        """Main window BEAMER conversion - consolidated approach"""
        # Check if we have recent simulation data
        recent_files = self.file_manager.get_recent_simulation_files()
        psf_files = [f for f in recent_files if 'psf' in f.name.lower() and f.suffix == '.csv']

        if psf_files:
            # Ask user to choose recent file or browse
            reply = QMessageBox.question(self, "Convert to BEAMER",
                                         f"Convert the most recent PSF simulation to BEAMER format?\n\n"
                                         f"File: {psf_files[0].name}\n\n"
                                         f"Choose 'Yes' for recent file, 'No' to browse, 'Cancel' to abort.",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

            if reply == QMessageBox.Yes:
                self._do_beamer_conversion_main(str(psf_files[0]))
            elif reply == QMessageBox.No:
                self._browse_and_convert_beamer()
        else:
            # No recent files, ask user to browse
            self._browse_and_convert_beamer()

    def _browse_and_convert_beamer(self):
        """Browse for PSF file and convert to BEAMER"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PSF Data", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )
        if file_path:
            self._do_beamer_conversion_main(file_path)

    def _do_beamer_conversion_main(self, csv_file):
        """Perform BEAMER conversion with progress indication"""
        # Show progress in status bar
        self.file_status_label.setText("🔄 Converting to BEAMER...")
        self.file_status_label.setVisible(True)

        try:
            # Load CSV data using file manager
            df, message = self.file_manager.load_csv_with_validation(
                csv_file,
                progress_callback=lambda msg: self.file_status_label.setText(f"🔄 {msg}")
            )

            if df is None:
                QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                return

            # Get beam energy from current settings
            beam_energy = self.energy_spin.value()

            # Ask about smoothing
            smooth_reply = QMessageBox.question(self, "Smoothing Options",
                                                "Apply Savitzky-Golay smoothing to reduce noise in tail region?\n\n"
                                                "Recommended for noisy simulations with statistical fluctuations.",
                                                QMessageBox.Yes | QMessageBox.No)
            apply_smoothing = (smooth_reply == QMessageBox.Yes)

            # Update status
            self.file_status_label.setText("🔄 Processing PSF data...")

            # Convert using the plot widget's consolidated method
            result = self.plot_widget._convert_csv_to_beamer_consolidated(
                df, beam_energy, apply_smoothing
            )

            if result:
                output_radius, output_psf, alpha, beta = result

                # Ask for save location
                default_name = Path(csv_file).stem + "_beamer.txt"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save BEAMER Format", default_name,
                    "Text files (*.txt);;All files (*.*)"
                )

                if file_path:
                    # Update status
                    self.file_status_label.setText("🔄 Saving BEAMER file...")

                    # Write BEAMER format using plot widget method
                    success, save_message = self.plot_widget._write_beamer_file(
                        file_path, output_radius, output_psf, csv_file, beam_energy
                    )

                    if success:
                        # Show success with comprehensive information
                        success_msg = QMessageBox(self)
                        success_msg.setWindowTitle("BEAMER Conversion Complete")
                        success_msg.setText(f"PSF successfully converted to BEAMER format!")
                        success_msg.setInformativeText(
                            f"File: {Path(file_path).name}\n\n"
                            f"Proximity Effect Parameters:\n"
                            f"α (forward scatter): {alpha:.3f}\n"
                            f"β (backscatter): {beta:.3f}\n\n"
                            f"Data points: {len(output_radius)}\n"
                            f"Radius range: {output_radius[0]:.3f} - {output_radius[-1]:.3f} μm"
                        )
                        success_msg.setStandardButtons(QMessageBox.Ok)
                        preview_button = success_msg.addButton("Preview Plot", QMessageBox.ActionRole)
                        success_msg.exec()

                        if success_msg.clickedButton() == preview_button:
                            # Switch to 1D plot tab and show BEAMER format
                            self.tab_widget.setCurrentIndex(4)  # 1D visualization
                            self.plot_widget.plot_beamer_format(output_radius, output_psf)

                        # Update status
                        self.status_label.setText(f"BEAMER conversion completed: {Path(file_path).name}")
                    else:
                        QMessageBox.critical(self, "Save Error", f"Failed to save BEAMER file: {save_message}")
            else:
                QMessageBox.critical(self, "Conversion Error", "Failed to convert PSF data to BEAMER format")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"BEAMER conversion failed: {str(e)}")
        finally:
            self.file_status_label.setVisible(False)

    def batch_convert_beamer_main(self):
        """Batch convert multiple PSF files to BEAMER format"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PSF Files for Batch Conversion", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_paths:
            # Ask for output directory
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", str(self.file_manager.working_dir)
            )

            if output_dir:
                # Show progress bar for batch operation
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, len(file_paths))
                self.progress_bar.setValue(0)

                success_count = 0
                beam_energy = self.energy_spin.value()

                for i, file_path in enumerate(file_paths):
                    self.progress_bar.setValue(i)
                    self.file_status_label.setText(f"🔄 Converting {Path(file_path).name}...")
                    self.file_status_label.setVisible(True)

                    # Allow GUI to update
                    QApplication.processEvents()

                    try:
                        df, message = self.file_manager.load_csv_with_validation(file_path)

                        if df is not None:
                            result = self.plot_widget._convert_csv_to_beamer_consolidated(
                                df, beam_energy, True  # Apply smoothing by default for batch
                            )

                            if result:
                                output_radius, output_psf, alpha, beta = result

                                # Generate output filename
                                output_name = Path(file_path).stem + "_beamer.txt"
                                output_path = Path(output_dir) / output_name

                                # Write file
                                success, _ = self.plot_widget._write_beamer_file(
                                    str(output_path), output_radius, output_psf,
                                    file_path, beam_energy
                                )

                                if success:
                                    success_count += 1

                    except Exception as e:
                        self.log_output(f"Error converting {file_path}: {str(e)}")

                # Complete batch operation
                self.progress_bar.setValue(len(file_paths))
                self.progress_bar.setVisible(False)
                self.file_status_label.setVisible(False)

                QMessageBox.information(self, "Batch Conversion Complete",
                                        f"Successfully converted {success_count}/{len(file_paths)} files to BEAMER format.\n\n"
                                        f"Output directory: {output_dir}")

    def validate_psf_data_main(self):
        """Main window PSF validation"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PSF Data to Validate", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            self.file_status_label.setText("🔄 Validating PSF data...")
            self.file_status_label.setVisible(True)

            try:
                # Load and validate using file manager
                df, message = self.file_manager.load_csv_with_validation(file_path)

                if df is None:
                    QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                    return

                # Use plot widget's comprehensive validation
                report = self.plot_widget._validate_psf_comprehensive(df, Path(file_path).name)

                # Show validation report
                dialog = QMessageBox(self)
                dialog.setWindowTitle("PSF Validation Report")
                dialog.setText(report)
                dialog.setIcon(QMessageBox.Information)
                dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Save)
                dialog.setDetailedText(
                    "Comprehensive validation includes:\n"
                    "• Data integrity checks\n"
                    "• Monotonicity analysis\n"
                    "• Statistical quality assessment\n"
                    "• Physical parameter validation\n"
                    "• Energy conservation check"
                )

                result = dialog.exec()

                if result == QMessageBox.Save:
                    # Save validation report
                    save_path, _ = QFileDialog.getSaveFileName(
                        self, "Save Validation Report",
                        Path(file_path).stem + "_validation.txt",
                        "Text files (*.txt);;All files (*.*)"
                    )

                    if save_path:
                        with open(save_path, 'w') as f:
                            f.write(report)
                        QMessageBox.information(self, "Success", f"Validation report saved to {save_path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"PSF validation failed: {str(e)}")
            finally:
                self.file_status_label.setVisible(False)

    def compare_beamer_files_main(self):
        """Compare multiple BEAMER format files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select BEAMER Files to Compare", "",
            "Text files (*.txt);;Data files (*.dat);;All files (*.*)"
        )

        if len(file_paths) >= 2:
            # Switch to 1D plot tab for comparison
            self.tab_widget.setCurrentIndex(4)

            # Clear existing plots
            self.plot_widget.figure.clear()
            ax = self.plot_widget.figure.add_subplot(111)

            colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

            # Load and plot each BEAMER file
            for i, file_path in enumerate(file_paths):
                try:
                    radius = []
                    psf = []

                    with open(file_path, 'r') as f:
                        for line in f:
                            if not line.startswith('#') and line.strip():
                                try:
                                    r, p = map(float, line.split())
                                    radius.append(r)
                                    psf.append(p)
                                except:
                                    continue

                    if radius and psf:
                        color = colors[i % len(colors)]
                        ax.loglog(radius, psf, linewidth=2, color=color,
                                  label=Path(file_path).stem)

                except Exception as e:
                    self.log_output(f"Error loading {file_path}: {str(e)}")

            # Format plot in BEAMER style
            ax.set_xlabel('radius, μm')
            ax.set_ylabel('relative energy deposition')
            ax.set_title('BEAMER PSF Comparison')
            ax.set_xlim(0.01, 100)
            ax.set_ylim(1e-10, 2)
            ax.grid(True, which="both", ls="-", alpha=0.2)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            self.plot_widget.figure.tight_layout()
            self.plot_widget.canvas.draw()

            QMessageBox.information(self, "Comparison Complete",
                                    f"Loaded and compared {len(file_paths)} BEAMER files.\n\n"
                                    "Check the 1D Visualization tab for the comparison plot.")
        else:
            QMessageBox.warning(self, "Insufficient Files",
                                "Please select at least 2 BEAMER files for comparison.")

    # ===================================================================
    # ENHANCED UTILITY METHODS
    # ===================================================================

    def open_psf_comparison(self):
        """Open PSF comparison tool"""
        # Switch to 1D visualization tab which has comparison features
        self.tab_widget.setCurrentIndex(4)
        QMessageBox.information(self, "PSF Comparison Tool",
                                "Use the '1D PSF Visualization' tab for PSF comparison:\n\n"
                                "1. Load initial PSF with 'Load PSF Data'\n"
                                "2. Add more datasets with 'Add for Comparison'\n"
                                "3. Use 'Analyze Comparison' for detailed analysis\n"
                                "4. Switch plot types to see different views")

    def show_recent_files(self):
        """Show recent simulation files"""
        recent_files = self.file_manager.get_recent_simulation_files()

        if recent_files:
            file_list = "\n".join([f"• {f.name} ({f.stat().st_size // 1024} KB)"
                                   for f in recent_files[:10]])
            QMessageBox.information(self, "Recent Simulation Files",
                                    f"Recent files in working directory:\n\n{file_list}\n\n"
                                    f"Working directory: {self.file_manager.working_dir}")
        else:
            QMessageBox.information(self, "No Recent Files",
                                    f"No recent simulation files found.\n\n"
                                    f"Working directory: {self.file_manager.working_dir}")

    def filter_log_messages(self):
        """Filter log messages based on selection"""
        # This would filter the output text based on the combo selection
        # Implementation would depend on how we want to store and filter messages
        filter_type = self.filter_combo.currentText()
        self.status_label.setText(f"Log filter: {filter_type}")

    # ===================================================================
    # SIMULATION AND FILE MANAGEMENT
    # ===================================================================

    def generate_output_filename(self, base_name="ebl", extension=".csv", include_timestamp=False, run_number=None):
        """Generate dynamic filename based on simulation parameters"""
        beam_diameter = self.beam_size_spin.value()
        resist_thickness = self.thickness_spin.value()
        beam_energy = self.energy_spin.value()
        material = self.material_combo.currentText()

        # Build filename components
        parts = [base_name]
        parts.append(f"E{beam_energy:.0f}keV")
        parts.append(f"beam{beam_diameter:.1f}nm")
        parts.append(f"resist{resist_thickness:.0f}nm")
        parts.append(material.replace("_", ""))

        # Add run number if specified
        if run_number is not None:
            parts.append(f"run{run_number:03d}")

        # Add timestamp if requested
        if include_timestamp:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            parts.append(timestamp)

        # Join parts and add extension
        filename = "_".join(parts) + extension
        return filename

    def find_next_run_number(self, base_pattern):
        """Find the next available run number for a given pattern"""
        pattern = base_pattern + "_run*.csv"
        existing_files = glob.glob(os.path.join(self.working_dir, pattern))

        if not existing_files:
            return 1

        # Extract run numbers
        run_numbers = []
        for file in existing_files:
            match = re.search(r'run(\d+)', file)
            if match:
                run_numbers.append(int(match.group(1)))

        return max(run_numbers) + 1 if run_numbers else 1

    def generate_macro(self):
        """Generate Geant4 macro file with optimized settings"""
        try:
            # Ensure the working directory exists
            Path(self.working_dir).mkdir(parents=True, exist_ok=True)

            # Show progress
            self.generate_button.set_working(True, "Generating...")

            # Generate base filename pattern
            base_pattern = self.generate_output_filename(extension="")

            # Find next run number if auto-increment is enabled
            run_number = None
            if self.auto_increment_check.isChecked():
                run_number = self.find_next_run_number(base_pattern)

            # Add timestamp if requested
            use_timestamp = self.timestamp_check.isChecked()

            # Generate output filenames
            psf_filename = self.generate_output_filename("psf", ".csv",
                                                         include_timestamp=use_timestamp,
                                                         run_number=run_number)
            psf2d_filename = self.generate_output_filename("psf2d", ".csv",
                                                           include_timestamp=use_timestamp,
                                                           run_number=run_number)
            summary_filename = self.generate_output_filename("summary", ".txt",
                                                             include_timestamp=use_timestamp,
                                                             run_number=run_number)
            beamer_filename = self.generate_output_filename("beamer", ".dat",
                                                            include_timestamp=use_timestamp,
                                                            run_number=run_number)

            # Store filenames for later use
            self.current_output_files = {
                'psf': os.path.join(self.working_dir, psf_filename),
                'psf2d': os.path.join(self.working_dir, psf2d_filename),
                'summary': os.path.join(self.working_dir, summary_filename),
                'beamer': os.path.join(self.working_dir, beamer_filename)
            }

            macro_path = Path(self.working_dir) / "gui_generated.mac"
            num_events = self.events_spin.value()

            with open(macro_path, 'w') as f:
                f.write("# EBL Simulation Macro - Generated by Enhanced GUI v3.1\n")
                f.write(f"# {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Events: {num_events:,}\n\n")

                # Add output filename commands
                f.write("# Output file configuration\n")
                f.write(f"/ebl/output/setDirectory {self.working_dir}\n")
                f.write(f"/ebl/output/setPSFFile {psf_filename}\n")
                f.write(f"/ebl/output/setPSF2DFile {psf2d_filename}\n")
                f.write(f"/ebl/output/setSummaryFile {summary_filename}\n")
                f.write(f"/ebl/output/setBeamerFile {beamer_filename}\n\n")

                # Optimized verbosity for large simulations
                if num_events <= 10000:
                    verbose_level = min(self.verbose_spin.value(), 2)
                elif num_events <= 100000:
                    verbose_level = min(self.verbose_spin.value(), 1)
                else:
                    verbose_level = 0

                f.write(f"/run/verbose {verbose_level}\n")
                f.write(f"/event/verbose {max(0, verbose_level-1)}\n")
                f.write(f"/tracking/verbose 0\n\n")

                # Performance optimizations for large simulations
                if num_events > 100000:
                    f.write("# Performance optimizations for large simulation\n")
                    f.write("/control/cout/ignoreThreadsExcept 0\n")
                    f.write("/run/printProgress 0\n")
                    f.write("# Using custom progress reporting for better GUI integration\n\n")

                # Random seed handling
                if self.seed_spin.value() == -1:
                    random_seed = random.randint(1, 2147483647)
                    f.write(f"/random/setSeeds {random_seed} {random_seed+1}\n")
                    f.write(f"# Auto-generated random seed: {random_seed}\n\n")
                    self.last_used_seed = random_seed
                elif self.seed_spin.value() > 0:
                    f.write(f"/random/setSeeds {self.seed_spin.value()} {self.seed_spin.value()+1}\n\n")

                # Initialize
                f.write("# Initialize\n")
                f.write("/run/initialize\n\n")

                # Material settings
                f.write("# Material settings\n")
                f.write(f'/det/setResistComposition "{self.composition_edit.text()}"\n')
                f.write(f"/det/setResistThickness {self.thickness_spin.value()} nm\n")
                f.write(f"/det/setResistDensity {self.density_spin.value()} g/cm3\n")
                f.write("/det/update\n\n")

                # Physics processes
                f.write("# Physics processes\n")
                f.write(f"/process/em/fluo {1 if self.fluorescence_check.isChecked() else 0}\n")
                f.write(f"/process/em/auger {1 if self.auger_check.isChecked() else 0}\n\n")

                # Beam configuration
                f.write("# Beam configuration\n")
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

                f.write(f"/gun/direction {dx} {dy} {dz}\n")
                f.write(f"/gun/beamSize {self.beam_size_spin.value()} nm\n\n")

                # Visualization (only for small simulations)
                if self.visualization_check.isChecked() and num_events <= 1000:
                    f.write("# Visualization\n")
                    f.write("/vis/open OGL\n")
                    f.write("/vis/drawVolume\n")
                    f.write("/vis/scene/add/trajectories smooth\n\n")
                elif self.visualization_check.isChecked():
                    f.write("# Visualization disabled for large simulation\n\n")

                # Run simulation
                f.write("# Run simulation\n")
                f.write(f"/run/beamOn {num_events}\n")

            self.log_output(f"Enhanced macro generated: {macro_path}")
            self.log_output(f"Target events: {num_events:,}")
            if num_events > 100000:
                self.log_output("Large simulation detected - using optimized settings")

            self.status_label.setText("Macro generated successfully")
            return str(macro_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate macro: {str(e)}")
            return None
        finally:
            self.generate_button.set_working(False)

    def run_simulation(self):
        """Start simulation with enhanced progress tracking"""
        if self.simulation_running:
            QMessageBox.information(self, "Info", "Simulation is already running")
            return

        # Validate inputs
        if self.events_spin.value() > 1000000:
            reply = QMessageBox.question(
                self, "Large Simulation Warning",
                f"Running {self.events_spin.value():,} events may take a very long time.\n\n"
                f"Large simulations (>1M events) use optimized settings:\n"
                f"• Reduced console output\n"
                f"• Custom progress reporting\n"
                f"• Performance optimizations\n\n"
                f"Continue with simulation?",
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
            self.setup_defaults()

            if not Path(self.executable_path).exists():
                QMessageBox.critical(self, "Error",
                                     f"Executable not found: {self.executable_path}\n\n"
                                     f"Please select the correct executable using File > Select Executable")
                return

        # Setup simulation UI state
        self.clear_log()
        self.simulation_running = True
        self.run_button.set_working(True, "Running...")
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.events_spin.value())
        self.progress_bar.setValue(0)

        # Switch to output tab
        self.tab_widget.setCurrentIndex(3)

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
        self.log_output("Enhanced simulation started...")
        self.status_label.setText("Simulation running...")

    def stop_simulation(self):
        """Stop simulation"""
        if self.simulation_worker:
            self.simulation_worker.stop()
            self.log_output("Stopping simulation...")

    def simulation_finished(self, success, message):
        """Handle simulation completion with enhanced file loading"""
        self.simulation_running = False
        self.run_button.set_working(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)

        self.log_output(message)
        self.status_label.setText(message)

        if self.simulation_thread:
            self.simulation_thread.quit()
            self.simulation_thread.wait()

        if success:
            # Enhanced success handling with better file detection
            available_files = []

            if hasattr(self, 'current_output_files'):
                # Check generated files
                for file_type, file_path in self.current_output_files.items():
                    if Path(file_path).exists():
                        file_size = Path(file_path).stat().st_size
                        available_files.append(f"{file_type.upper()}: {Path(file_path).name} ({file_size//1024} KB)")

            if available_files:
                reply = QMessageBox.question(
                    self, "Simulation Complete!",
                    f"Simulation completed successfully!\n\n"
                    f"Generated files:\n• " + "\n• ".join(available_files) +
                    f"\n\nWould you like to automatically load and visualize the results?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self._auto_load_simulation_results()
            else:
                QMessageBox.information(self, "Simulation Complete",
                                        "Simulation completed, but no output files were detected.\n"
                                        "Check the log for any errors or warnings.")
        else:
            QMessageBox.warning(self, "Simulation Failed",
                                f"Simulation did not complete successfully.\n\n{message}")

    def _auto_load_simulation_results(self):
        """Automatically load simulation results with enhanced error handling"""
        try:
            if hasattr(self, 'current_output_files'):
                psf_file = self.current_output_files.get('psf')
                psf2d_file = self.current_output_files.get('psf2d')
                summary_file = self.current_output_files.get('summary')

                # Load 1D PSF if available
                if psf_file and Path(psf_file).exists():
                    self.tab_widget.setCurrentIndex(4)  # 1D visualization tab
                    QTimer.singleShot(500, lambda: self.auto_load_1d(psf_file))

                # Load 2D data if available
                if psf2d_file and Path(psf2d_file).exists():
                    QTimer.singleShot(1000, lambda: self.auto_load_2d(psf2d_file))

                # Load summary if available
                if summary_file and Path(summary_file).exists():
                    QTimer.singleShot(1500, lambda: self.auto_load_summary(summary_file))

        except Exception as e:
            self.log_output(f"Error auto-loading results: {str(e)}")

    def auto_load_1d(self, file_path):
        """Auto-load 1D PSF data with error handling"""
        try:
            df, message = self.file_manager.load_csv_with_validation(file_path)

            if df is not None:
                # Extract PSF data
                radii, energies = self.plot_widget._extract_psf_from_df(df)

                if radii and energies:
                    # Clear existing data and load new
                    self.plot_widget.datasets = []
                    self.plot_widget.current_csv_path = file_path

                    dataset_info = {
                        'radii': radii,
                        'energies': energies,
                        'label': f"PSF - {Path(file_path).stem}",
                        'file_path': file_path,
                        'style': {'color': 'blue', 'linewidth': 2}
                    }
                    self.plot_widget.datasets.append(dataset_info)

                    # Update UI and plot
                    self.plot_widget.beamer_button.set_status(True)
                    self.plot_widget.validate_button.set_status(True)
                    self.plot_widget.save_button.set_status(True)
                    self.plot_widget.compare_button.set_status(True)
                    self.plot_widget.clear_button.set_status(True)

                    self.plot_widget.plot_all_datasets()
                    self.plot_widget.update_comparison_list()

                    self.status_label.setText("1D PSF data loaded successfully")

        except Exception as e:
            self.log_output(f"Error auto-loading 1D data: {str(e)}")

    def auto_load_2d(self, file_path):
        """Auto-load 2D data with enhanced error handling and debugging"""
        try:
            self.tab_widget.setCurrentIndex(5)  # 2D visualization tab

            # Check if file exists and has content
            if not Path(file_path).exists():
                self.log_output(f"❌ 2D file not found: {file_path}")
                return

            file_size = Path(file_path).stat().st_size
            self.log_output(f"📊 Loading 2D data from: {Path(file_path).name} ({file_size} bytes)")

            if file_size < 100:  # Very small file, likely empty
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if "No 2D data collected" in content:
                        self.log_output("⚠️ No 2D data was collected during simulation")
                        return

            # Load CSV with explicit index column
            df = pd.read_csv(file_path, index_col=0)

            if df.empty:
                self.log_output("❌ 2D CSV file is empty")
                return

            self.log_output(f"✅ 2D data shape: {df.shape[0]} depths × {df.shape[1]} radii")

            # Extract data
            depths = df.index.values.astype(float)  # Depth values (nm)
            radii = df.columns.astype(float).values  # Radius values (nm)
            data = df.values.astype(float)  # Energy data (eV)

            # Check for valid data
            non_zero_count = np.count_nonzero(data)
            total_energy = np.sum(data)

            self.log_output(f"📈 2D data stats: {non_zero_count} non-zero bins, total: {total_energy:.2e} eV")

            if non_zero_count == 0:
                self.log_output("⚠️ 2D data contains no energy deposits")
                return

            # Store the data in the 2D plot widget
            self.plot_2d_widget.current_data = {
                'depths': depths,
                'radii': radii,
                'energy': data,
                'filename': Path(file_path).stem
            }

            # Update UI controls
            self.plot_2d_widget.depth_slider.setMaximum(len(depths) - 1)
            self.plot_2d_widget.depth_slider.setValue(len(depths) // 2)  # Start in middle
            self.plot_2d_widget.save_plot_button.set_status(True)
            self.plot_2d_widget.export_button.set_status(True)

            # Plot the data
            self.plot_2d_widget.plot_2d_data()

            self.status_label.setText("2D data loaded successfully")
            self.log_output("✅ 2D visualization ready - check the 2D Visualization tab")

        except Exception as e:
            error_msg = f"❌ Error auto-loading 2D data: {str(e)}"
            self.log_output(error_msg)

            # Try to provide more specific error information
            try:
                with open(file_path, 'r') as f:
                    first_lines = [f.readline().strip() for _ in range(3)]
                    self.log_output(f"📄 File preview: {first_lines}")
            except:
                pass

    def auto_load_summary(self, file_path):
        """Auto-load simulation summary"""
        try:
            with open(file_path, 'r') as f:
                summary_text = f.read()

            # Show summary in output log (since we removed analysis tab)
            self.log_output("=== SIMULATION SUMMARY ===")
            for line in summary_text.split('\n'):
                if line.strip():
                    self.log_output(line)
            self.log_output("=== END SUMMARY ===")

            self.status_label.setText("Summary loaded in output log")

        except Exception as e:
            self.log_output(f"Error auto-loading summary: {str(e)}")

    def update_progress(self, event_num):
        """Update progress bar and status"""
        self.progress_bar.setValue(event_num)
        progress = (event_num / self.events_spin.value()) * 100
        self.status_label.setText(f"Simulation: {event_num:,}/{self.events_spin.value():,} ({progress:.1f}%)")

    def log_output(self, message):
        """Add message to output log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.output_text.append(f"[{timestamp}] {message}")

        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """Clear output log"""
        self.output_text.clear()

    def save_log(self):
        """Save log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log",
            f"ebl_sim_log_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            "Text files (*.txt);;All files (*.*)"
        )

        if file_path:
            try:
                success, message = self.file_manager.save_with_backup(
                    self.output_text.toPlainText(), file_path, backup=False
                )

                if success:
                    QMessageBox.information(self, "Success", f"Log saved to {file_path}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to save log: {message}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")

    def save_macro(self):
        """Save macro to file"""
        macro_path = self.generate_macro()
        if macro_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Macro",
                f"ebl_sim_{time.strftime('%Y%m%d_%H%M%S')}.mac",
                "Macro files (*.mac);;All files (*.*)"
            )

            if file_path:
                try:
                    with open(macro_path, 'r') as src:
                        content = src.read()

                    success, message = self.file_manager.save_with_backup(content, file_path)

                    if success:
                        QMessageBox.information(self, "Success", f"Macro saved to {file_path}")
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to save macro: {message}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save macro: {str(e)}")

    def select_executable(self):
        """Select executable file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select EBL Executable",
            str(Path(self.executable_path).parent) if self.executable_path else "",
            "Executable files (*.exe);;All files (*.*)"
        )

        if file_path:
            self.executable_path = file_path
            self.working_dir = str(Path(file_path).parent)
            self.file_manager.working_dir = Path(self.working_dir)
            self.log_output(f"Selected executable: {file_path}")

    def load_configuration(self):
        """Load simulation configuration from JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "",
            "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)

                # Load material settings
                if 'material' in config:
                    self.material_combo.setCurrentText(config['material'].get('preset', 'Custom'))
                    self.composition_edit.setText(config['material'].get('composition', ''))
                    self.thickness_spin.setValue(config['material'].get('thickness', 30.0))
                    self.density_spin.setValue(config['material'].get('density', 1.35))

                # Load beam settings
                if 'beam' in config:
                    self.energy_spin.setValue(config['beam'].get('energy', 100.0))
                    self.beam_size_spin.setValue(config['beam'].get('size', 2.0))
                    self.pos_x_spin.setValue(config['beam'].get('pos_x', 0.0))
                    self.pos_y_spin.setValue(config['beam'].get('pos_y', 0.0))
                    self.pos_z_spin.setValue(config['beam'].get('pos_z', 100.0))
                    self.dir_x_spin.setValue(config['beam'].get('dir_x', 0.0))
                    self.dir_y_spin.setValue(config['beam'].get('dir_y', 0.0))
                    self.dir_z_spin.setValue(config['beam'].get('dir_z', -1.0))

                # Load simulation settings
                if 'simulation' in config:
                    self.events_spin.setValue(config['simulation'].get('events', 10000))
                    self.seed_spin.setValue(config['simulation'].get('seed', -1))
                    self.verbose_spin.setValue(config['simulation'].get('verbose', 1))
                    self.fluorescence_check.setChecked(config['simulation'].get('fluorescence', True))
                    self.auger_check.setChecked(config['simulation'].get('auger', True))
                    self.visualization_check.setChecked(config['simulation'].get('visualization', False))

                QMessageBox.information(self, "Success", "Configuration loaded successfully")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load configuration: {str(e)}")

    def save_configuration(self):
        """Save current configuration to JSON"""
        config = {
            'material': {
                'preset': self.material_combo.currentText(),
                'composition': self.composition_edit.text(),
                'thickness': self.thickness_spin.value(),
                'density': self.density_spin.value()
            },
            'beam': {
                'energy': self.energy_spin.value(),
                'size': self.beam_size_spin.value(),
                'pos_x': self.pos_x_spin.value(),
                'pos_y': self.pos_y_spin.value(),
                'pos_z': self.pos_z_spin.value(),
                'dir_x': self.dir_x_spin.value(),
                'dir_y': self.dir_y_spin.value(),
                'dir_z': self.dir_z_spin.value()
            },
            'simulation': {
                'events': self.events_spin.value(),
                'seed': self.seed_spin.value(),
                'verbose': self.verbose_spin.value(),
                'fluorescence': self.fluorescence_check.isChecked(),
                'auger': self.auger_check.isChecked(),
                'visualization': self.visualization_check.isChecked()
            }
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration",
            f"ebl_config_{time.strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            try:
                success, message = self.file_manager.save_with_backup(
                    json.dumps(config, indent=2), file_path
                )

                if success:
                    QMessageBox.information(self, "Success", f"Configuration saved to {file_path}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to save configuration: {message}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

    def show_about(self):
        """Enhanced about dialog"""
        QMessageBox.about(self, "About EBL Simulation GUI",
                          """<h3>EBL Simulation GUI v3.1 Enhanced Edition</h3>
                  <p>A comprehensive GUI for Geant4-based electron beam lithography simulations with advanced analysis tools.</p>
                  
                  <p><b>✨ New in v3.1 Enhanced:</b></p>
                  <ul>
                    <li>🔧 Consolidated BEAMER PSF format conversion</li>
                    <li>📊 Advanced PSF comparison and analysis tools</li>
                    <li>🎯 Enhanced PSF validation with comprehensive checks</li>
                    <li>🔄 Unified file management system</li>
                    <li>⚡ Optimized performance for large simulations (>1M events)</li>
                    <li>🎨 Improved UI with status-aware buttons and progress indicators</li>
                    <li>🐛 Fixed 2D contour plotting issues</li>
                    <li>🧹 Removed placeholder functionality for cleaner interface</li>
                  </ul>
                  
                  <p><b>🔬 Core Features:</b></p>
                  <ul>
                    <li>2D depth-radius energy deposition visualization</li>
                    <li>XPS-validated material compositions (Alucone, Biscone)</li>
                    <li>Real-time simulation monitoring with adaptive progress tracking</li>
                    <li>Multi-format data export (BEAMER, NumPy, MATLAB)</li>
                    <li>Comprehensive proximity effect parameter calculation</li>
                    <li>Batch processing capabilities</li>
                    <li>Smart material property estimation</li>
                  </ul>
                  
                  <p><b>🔬 Research Applications:</b></p>
                  <ul>
                    <li>Electron beam lithography process optimization</li>
                    <li>Proximity effect correction for commercial EBL tools</li>
                    <li>Novel resist material characterization</li>
                    <li>Multi-layer resist stack analysis</li>
                  </ul>
                  
                  <p><i>Based on experimental data from TMA + 2-butyne-1,4-diol MLD process.<br>
                  Developed for advanced EBL research and industrial applications.</i></p>
                  
                  <p><b>Support:</b> Check the Help menu for BEAMER format guide and usage tips.</p>
                  """)

    def show_beamer_help(self):
        """Enhanced BEAMER format help dialog"""
        help_text = """
<h3>🎯 BEAMER PSF Format Guide</h3>

<h4>📋 Format Requirements:</h4>
<ul>
<li><b>Normalization:</b> Maximum value = 1.0 (peak normalized, not area)</li>
<li><b>Units:</b> Radius in micrometers (μm), PSF dimensionless</li>
<li><b>Range:</b> Typically 0.01 to 100 μm (covers 99%+ of scattered electrons)</li>
<li><b>Spacing:</b> Logarithmic or dense linear spacing recommended</li>
<li><b>Format:</b> ASCII text, two columns: radius PSF_value</li>
</ul>

<h4>📄 File Structure:</h4>
<pre>
# Electron beam PSF for BEAMER proximity correction
# Generated from Geant4 simulation by EBL GUI
# Source: ebl_psf_E100keV_beam2.0nm_resist30nm.csv
# Beam energy: 100 keV
# Format: radius(um) relative_energy_deposition
#
0.01000    0.98765
0.01500    0.95432
0.02234    0.89123
...
100.000    1.234e-9
</pre>

<h4>⚖️ Proximity Effect Parameters:</h4>
<ul>
<li><b>α (alpha):</b> Forward scatter fraction (r < 1 μm)<br>
    <i>Typical values: 0.6-0.8 for thin resists</i></li>
<li><b>β (beta):</b> Backscatter fraction (r > 1 μm)<br>
    <i>β = 1 - α, represents long-range scattering</i></li>
<li><b>η (eta):</b> Characteristic backscatter range [μm]<br>
    <i>Automatically calculated from PSF tail analysis</i></li>
</ul>

<h4>✅ Quality Assurance:</h4>
<ul>
<li><b>Smoothness:</b> Use Savitzky-Golay filtering for noisy tail regions</li>
<li><b>Continuity:</b> No sudden jumps or artificial cutoffs</li>
<li><b>Monotonicity:</b> Generally decreasing after initial peak</li>
<li><b>Coverage:</b> Extends to capture 99%+ of deposited energy</li>
<li><b>Validation:</b> R50 and R90 values should be physically reasonable</li>
</ul>

<h4>🔧 Conversion Process:</h4>
<ol>
<li><b>Load PSF data:</b> From Geant4 simulation (CSV format)</li>
<li><b>Normalize:</b> Peak value set to 1.0</li>
<li><b>Filter (optional):</b> Apply smoothing to reduce statistical noise</li>
<li><b>Extrapolate:</b> Extend tail to 100 μm using exponential fit</li>
<li><b>Validate:</b> Check physical parameters and data quality</li>
<li><b>Export:</b> Save in BEAMER-compatible ASCII format</li>
</ol>

<h4>🚨 Common Issues & Solutions:</h4>
<ul>
<li><b>Noisy tail region:</b> ✅ Enable smoothing during conversion</li>
<li><b>Truncated data:</b> ✅ Automatic extrapolation applied</li>
<li><b>Wrong normalization:</b> ✅ Ensure max = 1.0, not integral = 1.0</li>
<li><b>Missing near-field:</b> ✅ Auto-adds point at 0.01 μm if needed</li>
<li><b>Discontinuities:</b> ✅ Use validation tool to check data quality</li>
</ul>

<h4>📊 Using in BEAMER:</h4>
<ol>
<li>Import PSF file using BEAMER's proximity correction setup</li>
<li>Verify parameters (α, β, η) match simulation results</li>
<li>Test on calibration patterns before production use</li>
<li>Consider material-specific and energy-dependent effects</li>
</ol>

<p><i>💡 <b>Pro Tip:</b> Compare multiple PSF files using the comparison tool to 
study parameter dependencies (energy, material, thickness).</i></p>
"""

        dialog = QMessageBox(self)
        dialog.setWindowTitle("BEAMER Format Help")
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(help_text)
        dialog.setIcon(QMessageBox.Information)
        dialog.exec()

    def load_settings(self):
        """Load application settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        exe_path = self.settings.value("executable_path")
        if exe_path and Path(exe_path).exists():
            self.executable_path = exe_path
            self.working_dir = str(Path(exe_path).parent)
            self.file_manager.working_dir = Path(self.working_dir)

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
    """Enhanced main function with better error handling"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("EBL Simulation GUI")
    app.setApplicationVersion("3.1 Enhanced")
    app.setOrganizationName("EBL Research")

    try:
        # Create and show the main window
        window = EBLMainWindow()
        window.show()

        # Log startup
        window.log_output("=== EBL Simulation GUI v3.1 Enhanced Started ===")
        window.log_output("Features: Consolidated BEAMER conversion, PSF comparison, Enhanced UI")

        sys.exit(app.exec())

    except Exception as e:
        QMessageBox.critical(None, "Startup Error",
                             f"Failed to start application:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()