#!/usr/bin/env python3
"""
Enhanced EBL Simulation GUI with 2D Visualization
------------------------------------------------
An improved GUI for electron beam lithography simulations with support
for 2D depth-radius visualization and better data analysis capabilities.

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

class SimulationWorker(QObject):
    """Worker thread for running simulations"""
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

    def run_simulation(self):
        """Run the simulation in this thread"""
        try:
            args = [self.executable_path, self.macro_path]
            
            # Set up environment variables for Geant4
            env = os.environ.copy()
            g4_path = r"C:\Users\dreec\Geant4Projects\program_files"
            
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
                bufsize=0,
                cwd=self.working_dir,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )

            line_count = 0
            max_lines = 5000

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

                    # Extract progress information
                    if "Processing event" in line:
                        try:
                            event_num = int(line.split()[-1])
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

class Enhanced2DPlotWidget(QWidget):
    """Enhanced widget for 2D depth-radius visualization"""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_data = None

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

        # File controls
        file_controls = QHBoxLayout()
        
        self.load_2d_button = QPushButton("Load 2D Data")
        self.load_2d_button.clicked.connect(self.load_2d_data)
        
        self.save_plot_button = QPushButton("Save Plot")
        self.save_plot_button.clicked.connect(self.save_plot)
        
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)

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
        """Load 2D depth-radius data from CSV"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load 2D Data", "", "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            try:
                # Read the CSV file
                df = pd.read_csv(file_path, index_col=0)
                
                # Extract depth and radius arrays
                depths = df.index.values
                radii = df.columns.astype(float).values
                data = df.values
                
                # Store the data
                self.current_data = {
                    'depths': depths,
                    'radii': radii,
                    'energy': data,
                    'filename': Path(file_path).stem
                }
                
                # Update depth slider range
                self.depth_slider.setMaximum(len(depths) - 1)
                
                # Plot the data
                self.plot_2d_data()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load 2D data: {str(e)}")

    def plot_2d_data(self):
        """Plot the 2D data based on selected mode"""
        if not self.current_data:
            return

        self.figure.clear()
        
        plot_mode = self.plot_type_group.checkedId()
        
        if plot_mode == 0:  # 2D Heatmap
            self.plot_heatmap()
        elif plot_mode == 1:  # 3D Surface
            self.plot_3d_surface()
        elif plot_mode == 2:  # Contour
            self.plot_contour()
        elif plot_mode == 3:  # Cross sections
            self.plot_cross_sections()

        self.canvas.draw()

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
            energy_plot = np.log10(energy + 1e-10)
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
            energy_plot = np.log10(energy + 1e-10)
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
        """Create contour plot"""
        ax = self.figure.add_subplot(111)
        
        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']
        
        # Create meshgrid
        R, D = np.meshgrid(radii, depths)
        
        # Apply log scale if selected
        if self.log_scale_check.isChecked():
            energy_plot = np.log10(energy + 1e-10)
            levels = np.logspace(-2, np.log10(energy.max()), 20)
            label = 'Energy Deposition [eV/nm²]'
        else:
            energy_plot = energy
            levels = 20
            label = 'Energy Deposition [eV/nm²]'
        
        # Create contour plot
        cmap = self.colormap_combo.currentText()
        contour = ax.contour(R, D, energy_plot, levels=levels, cmap=cmap)
        ax.clabel(contour, inline=True, fontsize=8)
        
        # Fill contours
        contourf = ax.contourf(R, D, energy_plot, levels=levels, cmap=cmap, alpha=0.7)
        
        # Add colorbar
        self.figure.colorbar(contourf, ax=ax, label=label)
        
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
        """Update cross section when slider moves"""
        if self.current_data and self.plot_type_group.checkedId() == 3:
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
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Plot saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")

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
            try:
                if file_path.endswith('.npz'):
                    np.savez(file_path, 
                            depths=self.current_data['depths'],
                            radii=self.current_data['radii'],
                            energy=self.current_data['energy'])
                elif file_path.endswith('.mat'):
                    from scipy.io import savemat
                    savemat(file_path, self.current_data)
                    
                QMessageBox.information(self, "Success", f"Data exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")

class PlotWidget(QWidget):
    """Enhanced widget for 1D PSF plots with BEAMER conversion"""

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

        self.load_button = QPushButton("Load PSF Data")
        self.load_button.clicked.connect(self.load_data)

        self.compare_button = QPushButton("Compare Multiple")
        self.compare_button.clicked.connect(self.load_multiple)

        self.save_button = QPushButton("Save Plot")
        self.save_button.clicked.connect(self.save_plot)

        controls.addWidget(QLabel("Plot Type:"))
        controls.addWidget(self.plot_type_combo)
        controls.addStretch()
        controls.addWidget(self.load_button)
        controls.addWidget(self.compare_button)
        controls.addWidget(self.save_button)

        # NEW: BEAMER conversion controls
        beamer_controls = QHBoxLayout()
        
        self.beamer_button = QPushButton("Convert to BEAMER")
        self.beamer_button.clicked.connect(self.convert_to_beamer)
        self.beamer_button.setEnabled(False)
        
        self.validate_button = QPushButton("Validate PSF")
        self.validate_button.clicked.connect(self.validate_psf)
        self.validate_button.setEnabled(False)
        
        self.smooth_check = QCheckBox("Apply Smoothing")
        self.smooth_check.setChecked(True)
        
        beamer_controls.addWidget(QLabel("BEAMER Tools:"))
        beamer_controls.addWidget(self.beamer_button)
        beamer_controls.addWidget(self.validate_button)
        beamer_controls.addWidget(self.smooth_check)
        beamer_controls.addStretch()

        layout.addWidget(self.toolbar)
        layout.addLayout(controls)
        layout.addLayout(beamer_controls)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

        # Store data for replotting and conversion
        self.datasets = []
        self.current_csv_path = None

    def plot_data(self, radii, energies, title="PSF Profile", clear=True):
        """Plot the data with current settings"""
        if clear:
            self.datasets = [(radii, energies, title)]
        else:
            self.datasets.append((radii, energies, title))

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        plot_type = self.plot_type_combo.currentText()

        for radii, energies, label in self.datasets:
            if plot_type == "Log-Log":
                valid = [(r > 0 and e > 0) for r, e in zip(radii, energies)]
                r_filt = [r for r, v in zip(radii, valid) if v]
                e_filt = [e for e, v in zip(energies, valid) if v]

                if r_filt and e_filt:
                    ax.loglog(r_filt, e_filt, linewidth=2, label=label)
            elif plot_type == "Semi-Log":
                ax.semilogy(radii, energies, linewidth=2, label=label)
            else:
                ax.plot(radii, energies, linewidth=2, label=label)

        ax.set_xlabel('Radius (nm)')
        ax.set_ylabel('Energy Deposition (eV/nm²)')
        ax.set_title(f'PSF Profile - {plot_type} Scale')
        ax.grid(True, alpha=0.3)
        
        if len(self.datasets) > 1:
            ax.legend()

        self.figure.tight_layout()
        self.canvas.draw()

    def update_plot_type(self):
        """Update plot when type changes"""
        if self.datasets:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            plot_type = self.plot_type_combo.currentText()
            
            for radii, energies, label in self.datasets:
                if plot_type == "Log-Log":
                    valid = [(r > 0 and e > 0) for r, e in zip(radii, energies)]
                    r_filt = [r for r, v in zip(radii, valid) if v]
                    e_filt = [e for e, v in zip(energies, valid) if v]
                    if r_filt and e_filt:
                        ax.loglog(r_filt, e_filt, linewidth=2, label=label)
                elif plot_type == "Semi-Log":
                    ax.semilogy(radii, energies, linewidth=2, label=label)
                else:
                    ax.plot(radii, energies, linewidth=2, label=label)
            
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Energy Deposition (eV/nm²)')
            ax.set_title(f'PSF Profile - {plot_type} Scale')
            ax.grid(True, alpha=0.3)
            
            if len(self.datasets) > 1:
                ax.legend()
            
            self.figure.tight_layout()
            self.canvas.draw()

    def load_data(self):
        """Load data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data", "", "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            try:
                # Store the path for BEAMER conversion
                self.current_csv_path = file_path
                
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
                    # Enable BEAMER tools
                    self.beamer_button.setEnabled(True)
                    self.validate_button.setEnabled(True)
                else:
                    QMessageBox.warning(self, "Warning", "No valid data found in file")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def load_multiple(self):
        """Load multiple datasets for comparison"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Load Multiple PSF Data", "", "CSV files (*.csv);;All files (*.*)"
        )

        if file_paths:
            self.datasets = []
            
            for file_path in file_paths:
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
                        self.plot_data(radii, energies, Path(file_path).stem, clear=False)

                except Exception as e:
                    print(f"Error loading {file_path}: {str(e)}")
            
            if not self.datasets:
                QMessageBox.warning(self, "Warning", "No valid data found in files")

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

    def convert_to_beamer(self):
        """Convert current PSF data to BEAMER format"""
        if not self.current_csv_path:
            QMessageBox.warning(self, "Warning", "No PSF data loaded")
            return
            
        try:
            # Load the full CSV data
            df = pd.read_csv(self.current_csv_path)
            
            # Get non-zero data
            mask = df['EnergyDeposition(eV/nm^2)'] > 0
            if not mask.any():
                QMessageBox.warning(self, "Warning", "No non-zero energy deposition found")
                return
                
            # Extract data
            radius_nm = df.loc[mask, 'Radius(nm)'].values
            energy_density = df.loc[mask, 'EnergyDeposition(eV/nm^2)'].values
            
            # Convert to micrometers
            radius_um = radius_nm / 1000.0
            
            # Normalize to maximum = 1.0 (BEAMER standard)
            max_density = np.max(energy_density)
            psf_normalized = energy_density / max_density
            
            # Apply smoothing if requested
            if self.smooth_check.isChecked() and len(psf_normalized) > 7:
                from scipy.signal import savgol_filter
                
                # Smooth only the tail region (r > 10 μm)
                smooth_start = np.where(radius_um > 10.0)[0]
                if len(smooth_start) > 0:
                    start_idx = smooth_start[0]
                    if len(psf_normalized) - start_idx > 7:
                        # Apply Savitzky-Golay filter to tail
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
            
            # Ask for save location
            default_name = Path(self.current_csv_path).stem + "_beamer.txt"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save BEAMER Format", default_name,
                "Text files (*.txt);;All files (*.*)"
            )
            
            if file_path:
                # Write BEAMER format
                with open(file_path, 'w') as f:
                    f.write("# Electron beam PSF for BEAMER proximity correction\n")
                    f.write("# Generated from Geant4 simulation by EBL GUI\n")
                    f.write(f"# Source: {Path(self.current_csv_path).name}\n")
                    f.write("# Format: radius(um) relative_energy_deposition\n")
                    f.write("# PSF normalized to maximum = 1.0\n")
                    f.write("#\n")
                    
                    for r, p in zip(output_radius, output_psf):
                        f.write(f"{r:.6e} {p:.6e}\n")
                
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
                
                # Show success message with parameters
                QMessageBox.information(self, "BEAMER Conversion Complete",
                    f"PSF saved to: {file_path}\n\n"
                    f"Proximity effect parameters:\n"
                    f"α (forward scatter): {alpha:.3f}\n"
                    f"β (backscatter): {beta:.3f}\n\n"
                    f"Data points: {len(output_radius)}\n"
                    f"Radius range: {output_radius[0]:.3f} - {output_radius[-1]:.3f} μm")
                
                # Offer to visualize BEAMER format
                reply = QMessageBox.question(self, "Visualize BEAMER Format",
                    "Would you like to plot the BEAMER format PSF?",
                    QMessageBox.Yes | QMessageBox.No)
                    
                if reply == QMessageBox.Yes:
                    self.plot_beamer_format(output_radius, output_psf)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert to BEAMER format: {str(e)}")

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

    def validate_psf(self):
        """Validate PSF data quality"""
        if not self.datasets:
            QMessageBox.warning(self, "Warning", "No PSF data loaded")
            return
            
        # Create validation report
        report = "PSF VALIDATION REPORT\n" + "="*50 + "\n\n"
        
        for radii, energies, label in self.datasets:
            report += f"Dataset: {label}\n"
            report += "-"*30 + "\n"
            
            # Convert to numpy arrays
            r = np.array(radii)
            e = np.array(energies)
            
            # Test 1: Check for negative values
            negative_count = np.sum(e < 0)
            if negative_count > 0:
                report += f"❌ Found {negative_count} negative energy values\n"
            else:
                report += "✅ No negative energy values\n"
                
            # Test 2: Check data range
            nonzero_mask = e > 0
            if np.any(nonzero_mask):
                r_min = r[nonzero_mask].min()
                r_max = r[nonzero_mask].max()
                report += f"✅ Radius range: {r_min:.1f} - {r_max:.1f} nm\n"
            else:
                report += "❌ No non-zero data found\n"
                
            # Test 3: Check monotonicity (general trend)
            if len(e) > 10:
                # Use moving average to check trend
                window = min(5, len(e) // 4)
                if window >= 3:
                    smoothed = np.convolve(e, np.ones(window)/window, mode='valid')
                    increases = np.sum(np.diff(smoothed) > 0)
                    increase_frac = increases / len(smoothed)
                    
                    if increase_frac < 0.3:
                        report += "✅ PSF shows generally decreasing trend\n"
                    else:
                        report += f"⚠️ PSF has {increase_frac*100:.1f}% increasing segments\n"
                        
            # Test 4: Statistical quality
            if np.any(nonzero_mask):
                # Calculate coefficient of variation in tail
                tail_mask = r > 1000  # Beyond 1 μm
                if np.any(tail_mask & nonzero_mask):
                    tail_energy = e[tail_mask & nonzero_mask]
                    if len(tail_energy) > 5:
                        cv = np.std(tail_energy) / np.mean(tail_energy)
                        if cv < 0.5:
                            report += "✅ Good statistical quality in tail\n"
                        elif cv < 1.0:
                            report += "⚠️ Moderate noise in tail region\n"
                        else:
                            report += "❌ High noise in tail region\n"
                            
            # Test 5: Physical reasonableness
            if np.any(e > 0):
                # Calculate cumulative energy
                if len(r) > 1:
                    # Simple trapezoidal integration
                    cumulative = 0
                    total = 0
                    r50 = None
                    r90 = None
                    
                    for i in range(len(r)-1):
                        if e[i] > 0 and e[i+1] > 0:
                            dr = r[i+1] - r[i]
                            avg_e = (e[i] + e[i+1]) / 2
                            avg_r = (r[i] + r[i+1]) / 2
                            contrib = 2 * np.pi * avg_r * avg_e * dr
                            total += contrib
                            
                    cumulative = 0
                    for i in range(len(r)-1):
                        if e[i] > 0 and e[i+1] > 0:
                            dr = r[i+1] - r[i]
                            avg_e = (e[i] + e[i+1]) / 2
                            avg_r = (r[i] + r[i+1]) / 2
                            contrib = 2 * np.pi * avg_r * avg_e * dr
                            cumulative += contrib
                            
                            if r50 is None and cumulative > 0.5 * total:
                                r50 = r[i]
                            if r90 is None and cumulative > 0.9 * total:
                                r90 = r[i]
                                
                    if r50 and r90:
                        report += f"✅ R50: {r50:.1f} nm, R90: {r90:.1f} nm\n"
                        ratio = r90 / r50
                        if 2 < ratio < 100:
                            report += f"✅ R90/R50 ratio: {ratio:.1f} (reasonable)\n"
                        else:
                            report += f"⚠️ R90/R50 ratio: {ratio:.1f} (check parameters)\n"
                            
            report += "\n"
            
        # Show report in dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle("PSF Validation Report")
        dialog.setText(report)
        dialog.setIcon(QMessageBox.Information)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.setDetailedText("This validation checks:\n"
                              "• Data integrity (no negative values)\n"
                              "• Monotonicity (decreasing trend)\n"
                              "• Statistical quality (noise levels)\n"
                              "• Physical reasonableness (R50, R90 values)\n\n"
                              "Use this to verify your PSF calculation is correct.")
        dialog.exec()

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
        self.setWindowTitle("EBL Simulation Control - Enhanced Edition")
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

        # Create tabs
        self.create_resist_tab()
        self.create_beam_tab()
        self.create_simulation_tab()
        self.create_output_tab()
        self.create_1d_visualization_tab()
        self.create_2d_visualization_tab()
        self.create_analysis_tab()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)

        # Create menu bar and status bar
        self.create_menu_bar()
        self.create_status_bar()

    def create_menu_bar(self):
        """Create enhanced menu bar with BEAMER tools"""
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

        # Simulation menu
        sim_menu = menubar.addMenu("Simulation")

        run_action = QAction("Run Simulation", self)
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)

        stop_action = QAction("Stop Simulation", self)
        stop_action.triggered.connect(self.stop_simulation)
        sim_menu.addAction(stop_action)

        batch_action = QAction("Batch Run", self)
        batch_action.triggered.connect(self.batch_run)
        sim_menu.addAction(batch_action)

        # NEW: BEAMER menu
        beamer_menu = menubar.addMenu("BEAMER")
    
        convert_action = QAction("Convert PSF to BEAMER Format", self)
        convert_action.triggered.connect(self.convert_psf_to_beamer)
        beamer_menu.addAction(convert_action)
    
        batch_convert_action = QAction("Batch Convert to BEAMER", self)
        batch_convert_action.triggered.connect(self.batch_convert_beamer)
        beamer_menu.addAction(batch_convert_action)
    
        beamer_menu.addSeparator()
    
        validate_psf_action = QAction("Validate PSF Data", self)
        validate_psf_action.triggered.connect(self.validate_psf_data)
        beamer_menu.addAction(validate_psf_action)
    
        compare_beamer_action = QAction("Compare BEAMER Files", self)
        compare_beamer_action.triggered.connect(self.compare_beamer_files)
        beamer_menu.addAction(compare_beamer_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
        beamer_help_action = QAction("BEAMER Format Help", self)
        beamer_help_action.triggered.connect(self.show_beamer_help)
        help_menu.addAction(beamer_help_action)

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
        self.thickness_spin.setValue(30.0)
        self.thickness_spin.setDecimals(1)
        material_layout.addWidget(self.thickness_spin, 2, 1)

        material_layout.addWidget(QLabel("Density (g/cm³):"), 3, 0)
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
• Pristine Alucone: Al:1,C:5,H:4,O:2 (1.35 g/cm³)<br>
• Exposed Alucone: Al:1,C:5,H:4,O:3 (1.40 g/cm³)<br>
• From TMA + butyne-1,4-diol MLD process
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

        # Add auto-increment checkbox
        self.auto_increment_check = QCheckBox("Auto-increment run number")
        self.auto_increment_check.setChecked(True)
        sim_layout.addWidget(self.auto_increment_check, 3, 0, 1, 2)
    
        # Add option to include timestamp
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

    def create_1d_visualization_tab(self):
        """Create 1D PSF visualization tab"""
        self.plot_widget = PlotWidget()
        self.tab_widget.addTab(self.plot_widget, "1D PSF Visualization")

    def create_2d_visualization_tab(self):
        """Create 2D depth-radius visualization tab"""
        self.plot_2d_widget = Enhanced2DPlotWidget()
        self.tab_widget.addTab(self.plot_2d_widget, "2D Visualization")

    def create_analysis_tab(self):
        """Create analysis tab with summary statistics"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Summary statistics group
        stats_group = QGroupBox("Simulation Summary")
        stats_layout = QGridLayout()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(200)
        stats_layout.addWidget(self.summary_text, 0, 0, 1, 2)

        self.load_summary_button = QPushButton("Load Summary")
        self.load_summary_button.clicked.connect(self.load_summary)
        stats_layout.addWidget(self.load_summary_button, 1, 0)

        self.refresh_summary_button = QPushButton("Refresh")
        self.refresh_summary_button.clicked.connect(self.refresh_summary)
        stats_layout.addWidget(self.refresh_summary_button, 1, 1)

        stats_group.setLayout(stats_layout)

        # Batch analysis group
        batch_group = QGroupBox("Batch Analysis")
        batch_layout = QVBoxLayout()

        batch_info = QLabel("Analyze multiple simulation results for parameter studies")
        batch_layout.addWidget(batch_info)

        batch_button = QPushButton("Load Batch Results")
        batch_button.clicked.connect(self.analyze_batch)
        batch_layout.addWidget(batch_button)

        batch_group.setLayout(batch_layout)

        layout.addWidget(stats_group)
        layout.addWidget(batch_group)
        layout.addStretch()

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Analysis")

    def setup_defaults(self):
        """Setup default values"""
        # Set defaults based on XPS data
        self.material_combo.setCurrentText("Alucone_XPS")
        self.on_material_changed()

        # Set the known working executable path
        self.executable_path = r"C:\Users\dreec\Geant4Projects\EBeamSim\out\build\x64-release\bin\ebl_sim.exe"
        self.working_dir = r"C:\Users\dreec\Geant4Projects\EBeamSim\out\build\x64-release\bin"
        
        # Verify it exists
        if Path(self.executable_path).exists():
            print(f"Found executable: {self.executable_path}")
        else:
            print(f"Warning: Executable not found at: {self.executable_path}")
            # Try to find it dynamically as a fallback
            project_root = Path(__file__).resolve().parents[3]
            
            # List of possible executable locations
            possible_paths = [
                project_root / "out" / "build" / "x64-release" / "bin" / "ebl_sim.exe",
                project_root / "out" / "build" / "x64-debug" / "bin" / "ebl_sim.exe",
                project_root / "build" / "bin" / "Release" / "ebl_sim.exe",
                project_root / "build" / "bin" / "Debug" / "ebl_sim.exe",
            ]
            
            # Find the first existing executable
            for path in possible_paths:
                if path.exists():
                    self.executable_path = str(path)
                    self.working_dir = str(path.parent)
                    print(f"Found executable: {self.executable_path}")
                    break

    def convert_psf_to_beamer(self):
        """Convert PSF data to BEAMER format from menu"""
        # Check if we have recent simulation data
        psf_file = Path(self.working_dir) / "ebl_psf_data.csv"
    
        if psf_file.exists():
            reply = QMessageBox.question(self, "Convert to BEAMER",
                f"Convert the most recent simulation output to BEAMER format?\n\n"
                f"File: {psf_file.name}",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Yes:
                # Use existing file
                self._do_beamer_conversion(str(psf_file))
            elif reply == QMessageBox.No:
                # Let user choose file
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Select PSF Data", str(self.working_dir),
                    "CSV files (*.csv);;All files (*.*)"
                )
                if file_path:
                    self._do_beamer_conversion(file_path)
        else:
            # No recent file, ask user to select
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select PSF Data", "",
                "CSV files (*.csv);;All files (*.*)"
            )
            if file_path:
                self._do_beamer_conversion(file_path)

    def _do_beamer_conversion(self, csv_file):
        """Perform the actual BEAMER conversion"""
        try:
            # Load CSV data
            df = pd.read_csv(csv_file)
        
            # Get beam energy from current settings or ask user
            beam_energy = self.energy_spin.value()
        
            # Ask about smoothing
            smooth_reply = QMessageBox.question(self, "Smoothing",
                "Apply smoothing to reduce noise in tail region?",
                QMessageBox.Yes | QMessageBox.No)
            apply_smoothing = (smooth_reply == QMessageBox.Yes)
        
            # Convert to BEAMER format
            result = self._convert_csv_to_beamer(df, beam_energy, apply_smoothing)
        
            if result:
                output_radius, output_psf, alpha, beta = result
            
                # Ask for save location
                default_name = Path(csv_file).stem + "_beamer.txt"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save BEAMER Format", default_name,
                    "Text files (*.txt);;All files (*.*)"
                )
            
                if file_path:
                    # Write BEAMER format
                    with open(file_path, 'w') as f:
                        f.write("# Electron beam PSF for BEAMER proximity correction\n")
                        f.write("# Generated from Geant4 simulation by EBL GUI\n")
                        f.write(f"# Source: {Path(csv_file).name}\n")
                        f.write(f"# Beam energy: {beam_energy} keV\n")
                        f.write("# Format: radius(um) relative_energy_deposition\n")
                        f.write("# PSF normalized to maximum = 1.0\n")
                        f.write("#\n")
                    
                        for r, p in zip(output_radius, output_psf):
                            f.write(f"{r:.6e} {p:.6e}\n")
                
                    # Show success with preview option
                    msg = QMessageBox(self)
                    msg.setWindowTitle("BEAMER Conversion Complete")
                    msg.setText(f"PSF saved to: {Path(file_path).name}")
                    msg.setInformativeText(
                        f"Proximity parameters:\n"
                        f"α (forward): {alpha:.3f}\n"
                        f"β (backscatter): {beta:.3f}\n\n"
                        f"Data points: {len(output_radius)}"
                    )
                    msg.setStandardButtons(QMessageBox.Ok)
                    preview_button = msg.addButton("Preview", QMessageBox.ActionRole)
                    msg.exec()
                
                    if msg.clickedButton() == preview_button:
                        # Switch to plot tab and show BEAMER format
                        self.tab_widget.setCurrentIndex(4)  # 1D visualization
                        self.plot_widget.plot_beamer_format(output_radius, output_psf)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert to BEAMER format: {str(e)}")

    def _convert_csv_to_beamer(self, df, beam_energy, apply_smoothing=True):
        """Core BEAMER conversion logic"""
        try:
            # Get non-zero data
            mask = df['EnergyDeposition(eV/nm^2)'] > 0
            if not mask.any():
                return None
            
            # Extract data
            radius_nm = df.loc[mask, 'Radius(nm)'].values
            energy_density = df.loc[mask, 'EnergyDeposition(eV/nm^2)'].values
        
            # Convert to micrometers
            radius_um = radius_nm / 1000.0
        
            # Normalize to maximum = 1.0
            max_density = np.max(energy_density)
            psf_normalized = energy_density / max_density
        
            # Apply smoothing if requested
            if apply_smoothing and len(psf_normalized) > 7:
                from scipy.signal import savgol_filter
            
                # Smooth only the tail region
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
                if p > 1e-12:
                    output_radius.append(r)
                    output_psf.append(p)
        
            # Extrapolate tail if needed
            if output_radius[-1] < 100.0 and len(output_radius) > 10:
                n_fit = min(10, len(output_radius) // 2)
                r_fit = np.array(output_radius[-n_fit:])
                p_fit = np.array(output_psf[-n_fit:])
            
                if np.all(p_fit > 0):
                    coeffs = np.polyfit(r_fit, np.log(p_fit), 1)
                
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
            print(f"Conversion error: {str(e)}")
            return None

    def batch_convert_beamer(self):
        """Convert multiple PSF files to BEAMER format"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PSF Files", str(self.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )
    
        if file_paths:
            # Ask for output directory
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", str(self.working_dir)
            )
        
            if output_dir:
                success_count = 0
            
                for file_path in file_paths:
                    try:
                        df = pd.read_csv(file_path)
                        result = self._convert_csv_to_beamer(df, self.energy_spin.value(), True)
                    
                        if result:
                            output_radius, output_psf, alpha, beta = result
                        
                            # Generate output filename
                            output_name = Path(file_path).stem + "_beamer.txt"
                            output_path = Path(output_dir) / output_name
                        
                            # Write file
                            with open(output_path, 'w') as f:
                                f.write("# Electron beam PSF for BEAMER proximity correction\n")
                                f.write("# Generated from Geant4 simulation by EBL GUI\n")
                                f.write(f"# Source: {Path(file_path).name}\n")
                                f.write("# Format: radius(um) relative_energy_deposition\n")
                                f.write("#\n")
                            
                                for r, p in zip(output_radius, output_psf):
                                    f.write(f"{r:.6e} {p:.6e}\n")
                        
                            success_count += 1
                        
                    except Exception as e:
                        print(f"Error converting {file_path}: {str(e)}")
            
                QMessageBox.information(self, "Batch Conversion Complete",
                    f"Successfully converted {success_count}/{len(file_paths)} files")

    def validate_psf_data(self):
        """Validate PSF data from menu"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PSF Data to Validate", str(self.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )
    
        if file_path:
            # Load and validate
            try:
                df = pd.read_csv(file_path)
                report = self._validate_psf_dataframe(df, Path(file_path).name)
            
                # Show report
                dialog = QMessageBox(self)
                dialog.setWindowTitle("PSF Validation Report")
                dialog.setText(report)
                dialog.setIcon(QMessageBox.Information)
                dialog.setDetailedText(
                    "Validation checks:\n"
                    "• Data integrity\n"
                    "• Monotonicity\n"
                    "• Statistical quality\n"
                    "• Physical parameters\n"
                    "• Energy conservation"
                )
                dialog.exec()
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to validate PSF: {str(e)}")

    def _validate_psf_dataframe(self, df, filename):
        """Validate a PSF dataframe"""
        report = f"PSF VALIDATION: {filename}\n" + "="*60 + "\n\n"
    
        # Check for required columns
        required_cols = ['Radius(nm)', 'EnergyDeposition(eV/nm^2)']
        if not all(col in df.columns for col in required_cols):
            report += "❌ Missing required columns\n"
            return report
        
        # Get data
        radius = df['Radius(nm)'].values
        energy = df['EnergyDeposition(eV/nm^2)'].values
    
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
        
            # Test 3: Energy conservation
            if 'BinLower(nm)' in df.columns and 'BinUpper(nm)' in df.columns:
                area = np.pi * (df['BinUpper(nm)'].values**2 - df['BinLower(nm)'].values**2)
                total_energy = np.sum(energy * area)
                report += f"✅ Total integrated energy: {total_energy:.3e} eV·nm²\n"
            
            # Test 4: Monotonicity
            if len(energy[nonzero]) > 10:
                # Check general trend
                mid_idx = len(energy) // 2
                if energy[mid_idx] < energy[0]:
                    report += "✅ PSF shows decreasing trend\n"
                else:
                    report += "⚠️ PSF may not be monotonically decreasing\n"
                
            # Test 5: Noise assessment
            tail_mask = radius > 1000  # Beyond 1 μm
            if np.any(tail_mask & nonzero):
                tail_energy = energy[tail_mask & nonzero]
                if len(tail_energy) > 5:
                    cv = np.std(tail_energy) / np.mean(tail_energy)
                    if cv < 0.5:
                        report += "✅ Good statistical quality\n"
                    else:
                        report += f"⚠️ High noise in tail (CV={cv:.2f})\n"
        else:
            report += "❌ No non-zero data found\n"
        
        return report

    def compare_beamer_files(self):
        """Compare multiple BEAMER format files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select BEAMER Files to Compare", "",
            "Text files (*.txt);;All files (*.*)"
        )
    
        if len(file_paths) >= 2:
            # Switch to plot tab
            self.tab_widget.setCurrentIndex(4)
        
            # Clear existing plots
            self.plot_widget.figure.clear()
            ax = self.plot_widget.figure.add_subplot(111)
        
            # Load and plot each file
            for file_path in file_paths:
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
                        ax.loglog(radius, psf, linewidth=2, 
                                 label=Path(file_path).stem)
                    
                except Exception as e:
                    print(f"Error loading {file_path}: {str(e)}")
        
            # Format plot
            ax.set_xlabel('radius, μm')
            ax.set_ylabel('relative energy deposition')
            ax.set_title('BEAMER PSF Comparison')
            ax.set_xlim(0.01, 100)
            ax.set_ylim(1e-10, 2)
            ax.grid(True, which="both", ls="-", alpha=0.2)
            ax.legend()
        
            self.plot_widget.figure.tight_layout()
            self.plot_widget.canvas.draw()


    def show_beamer_help(self):
        """Show BEAMER format help dialog"""
        help_text = """
<h3>BEAMER PSF Format Guide</h3>

<h4>Format Requirements:</h4>
<ul>
<li><b>Normalization:</b> Maximum value = 1.0 (not area-normalized)</li>
<li><b>Units:</b> Radius in micrometers (μm), PSF unitless</li>
<li><b>Range:</b> Typically 0.01 to 100 μm</li>
<li><b>Scale:</b> Logarithmic spacing recommended</li>
</ul>

<h4>File Format:</h4>
<pre>
# Comment lines start with #
# radius(um) relative_energy_deposition
0.01    0.98765
0.015   0.95432
...
100.0   1.234e-9
</pre>

<h4>Proximity Parameters:</h4>
<ul>
<li><b>α (alpha):</b> Forward scatter fraction (r < 1 μm)</li>
<li><b>β (beta):</b> Backscatter fraction (r > 1 μm)</li>
<li><b>η (eta):</b> Characteristic backscatter range</li>
</ul>

<h4>Quality Checks:</h4>
<ul>
<li>PSF should be smooth and continuous</li>
<li>No sudden jumps or drops to zero</li>
<li>Monotonically decreasing (after initial peak)</li>
<li>Extends to capture 99%+ of deposited energy</li>
</ul>

<h4>Common Issues:</h4>
<ul>
<li><b>Noisy tail:</b> Use smoothing option during conversion</li>
<li><b>Truncated data:</b> Extrapolation automatically applied</li>
<li><b>Wrong normalization:</b> Ensure max = 1.0, not integral = 1.0</li>
</ul>
"""

        dialog = QMessageBox(self)
        dialog.setWindowTitle("BEAMER Format Help")
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(help_text)
        dialog.setIcon(QMessageBox.Information)
        dialog.exec()


    def generate_output_filename(self, base_name="ebl", extension=".csv", include_timestamp=False, run_number=None):
        """Generate dynamic filename based on simulation parameters"""
        # Get current parameters
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
        import re
        import glob
    
        # Look for existing files matching the pattern
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
        """Generate Geant4 macro file with dynamic output names"""
        try:
            # Ensure the working directory exists
            Path(self.working_dir).mkdir(parents=True, exist_ok=True)
        
            # Generate base filename pattern  
            base_pattern = self.generate_output_filename(extension="")
        
            # Find next run number if auto-increment is enabled
            run_number = None
            if hasattr(self, 'auto_increment_check') and self.auto_increment_check.isChecked():
                run_number = self.find_next_run_number(base_pattern)
        
            # Add timestamp if requested
            use_timestamp = hasattr(self, 'timestamp_check') and self.timestamp_check.isChecked()
        
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

            with open(macro_path, 'w') as f:
                f.write("# EBL Simulation Macro - Generated by GUI\n")
                f.write(f"# {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
                # Add output filename commands
                f.write("# Output file configuration\n")
                f.write(f"/ebl/output/setDirectory {self.working_dir}\n")
                f.write(f"/ebl/output/setPSFFile {psf_filename}\n")
                f.write(f"/ebl/output/setPSF2DFile {psf2d_filename}\n")
                f.write(f"/ebl/output/setSummaryFile {summary_filename}\n")
                f.write(f"/ebl/output/setBeamerFile {beamer_filename}\n\n")

                # Verbose settings
                verbose = min(self.verbose_spin.value(), 1) if self.events_spin.value() > 10000 else self.verbose_spin.value()
                f.write(f"/run/verbose {verbose}\n")
                f.write(f"/event/verbose {max(0, verbose-1)}\n")
                f.write(f"/tracking/verbose {max(0, verbose-2)}\n\n")

                # Random seed handling
                if self.seed_spin.value() == -1:
                    # Generate truly random seed
                    import random
                    random_seed = random.randint(1, 2147483647)
                    f.write(f"/random/setSeeds {random_seed} {random_seed+1}\n")
                    f.write(f"# Auto-generated random seed: {random_seed}\n\n")
                    self.last_used_seed = random_seed
                elif self.seed_spin.value() > 0:
                    f.write(f"/random/setSeeds {self.seed_spin.value()} {self.seed_spin.value()+1}\n\n")
                # If seed is 0, don't set any seed (use Geant4 default time-based)

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

                # Visualization
                if self.visualization_check.isChecked():
                    f.write("# Visualization\n")
                    f.write("/vis/open OGL\n")
                    f.write("/vis/drawVolume\n")
                    f.write("/vis/scene/add/trajectories smooth\n\n")

                # Run simulation
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
            self.setup_defaults()
            
            if not Path(self.executable_path).exists():
                QMessageBox.critical(self, "Error", 
                    f"Executable not found: {self.executable_path}\n\n"
                    f"Please select the correct executable using File > Select Executable")
                return

        # Ensure working directory exists
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)

        # Clear log and setup UI
        self.clear_log()
        self.simulation_running = True
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(self.events_spin.value())
        self.progress_bar.setValue(0)

        # Switch to output tab
        self.tab_widget.setCurrentIndex(3)  # Output tab

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
        
            # Check for output files using stored names
            if hasattr(self, 'current_output_files'):
                psf_file = Path(self.current_output_files['psf'])
                psf_2d_file = Path(self.current_output_files['psf2d'])
                summary_file = Path(self.current_output_files['summary'])
                beamer_file = Path(self.current_output_files.get('beamer', ''))
            else:
                # Fallback to default names
                output_dir = Path(self.working_dir)
                psf_file = output_dir / "ebl_psf_data.csv"
                psf_2d_file = output_dir / "ebl_2d_data.csv"
                summary_file = output_dir / "simulation_summary.txt"
                beamer_file = output_dir / "beamer_psf.dat"
        
            available_files = []
            if psf_file.exists():
                available_files.append("1D PSF data")
            if psf_2d_file.exists():
                available_files.append("2D depth-radius data")
            if summary_file.exists():
                available_files.append("Summary statistics")
            if beamer_file.exists():
                available_files.append("BEAMER format")
        
            if available_files:
                reply = QMessageBox.question(
                    self, "Load Results",
                    f"The following output files were generated:\n- " + 
                    "\n- ".join(available_files) + 
                    "\n\nWould you like to load and visualize them?",
                    QMessageBox.Yes | QMessageBox.No
                )
            
                if reply == QMessageBox.Yes:
                    # Load 1D PSF if available
                    if psf_file.exists():
                        self.tab_widget.setCurrentIndex(4)  # 1D visualization tab
                        QTimer.singleShot(500, lambda: self.auto_load_1d(str(psf_file)))
                
                    # Load 2D data if available
                    if psf_2d_file.exists():
                        QTimer.singleShot(1000, lambda: self.auto_load_2d(str(psf_2d_file)))
                
                    # Load summary if available
                    if summary_file.exists():
                        QTimer.singleShot(1500, lambda: self.auto_load_summary(str(summary_file)))

    def auto_load_1d(self, file_path):
        """Auto-load 1D PSF data"""
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
                self.plot_widget.plot_data(radii, energies, "PSF - Latest Simulation")
        except Exception as e:
            print(f"Error auto-loading 1D data: {str(e)}")

    def auto_load_2d(self, file_path):
        """Auto-load 2D data"""
        try:
            self.tab_widget.setCurrentIndex(5)  # 2D visualization tab
            # Read the CSV file
            df = pd.read_csv(file_path, index_col=0)
            
            # Extract depth and radius arrays
            depths = df.index.values
            radii = df.columns.astype(float).values
            data = df.values
            
            # Store the data in the 2D plot widget
            self.plot_2d_widget.current_data = {
                'depths': depths,
                'radii': radii,
                'energy': data,
                'filename': Path(file_path).stem
            }
            
            # Update depth slider range
            self.plot_2d_widget.depth_slider.setMaximum(len(depths) - 1)
            
            # Plot the data
            self.plot_2d_widget.plot_2d_data()
            
        except Exception as e:
            print(f"Error auto-loading 2D data: {str(e)}")

    def auto_load_summary(self, file_path):
        """Auto-load simulation summary"""
        try:
            with open(file_path, 'r') as f:
                summary_text = f.read()
            
            self.summary_text.setPlainText(summary_text)
            self.tab_widget.setCurrentIndex(6)  # Analysis tab
            
        except Exception as e:
            print(f"Error auto-loading summary: {str(e)}")

    def update_progress(self, event_num):
        """Update progress bar"""
        self.progress_bar.setValue(event_num)
        progress = (event_num / self.events_spin.value()) * 100
        self.status_label.setText(f"Simulation running... {event_num}/{self.events_spin.value()} ({progress:.1f}%)")

    def log_output(self, message):
        """Add message to output log"""
        timestamp = time.strftime("%H:%M:%S")
        self.output_text.append(f"[{timestamp}] {message}")

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
                self, "Save Macro", 
                f"ebl_sim_{time.strftime('%Y%m%d_%H%M%S')}.mac",
                "Macro files (*.mac);;All files (*.*)"
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
            self, "Select EBL Executable", 
            str(Path(self.executable_path).parent) if self.executable_path else "",
            "Executable files (*.exe);;All files (*.*)"
        )

        if file_path:
            self.executable_path = file_path
            self.working_dir = str(Path(file_path).parent)
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
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=2)
                QMessageBox.information(self, "Success", f"Configuration saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

    def batch_run(self):
        """Run batch simulations with parameter variations"""
        QMessageBox.information(self, "Batch Run", 
            "Batch simulation feature coming soon!\n\n"
            "This will allow running multiple simulations with:\n"
            "- Energy variations\n"
            "- Material thickness variations\n"
            "- Different resist compositions\n"
            "- Automated result collection")

    def load_summary(self):
        """Load simulation summary file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Summary", "",
            "Text files (*.txt);;All files (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.summary_text.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load summary: {str(e)}")

    def refresh_summary(self):
        """Refresh summary from default location"""
        summary_path = Path(self.working_dir) / "simulation_summary.txt"
        if summary_path.exists():
            try:
                with open(summary_path, 'r') as f:
                    self.summary_text.setPlainText(f.read())
            except Exception as e:
                self.log_output(f"Error refreshing summary: {str(e)}")
        else:
            QMessageBox.information(self, "Info", "No summary file found in working directory")

    def analyze_batch(self):
        """Analyze multiple simulation results"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PSF Data Files", "",
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_paths:
            QMessageBox.information(self, "Batch Analysis",
                f"Selected {len(file_paths)} files for analysis.\n\n"
                "Batch analysis features coming soon:\n"
                "- Parameter extraction from filenames\n"
                "- Trend analysis\n"
                "- Comparative plots\n"
                "- Statistical analysis")

    def show_about(self):
        """Updated about dialog"""
        QMessageBox.about(self, "About EBL Simulation GUI",
                          """<h3>EBL Simulation GUI v3.1 (BEAMER Edition)</h3>
                  <p>A comprehensive GUI for Geant4-based electron beam lithography simulations.</p>
                  <p><b>New in v3.1:</b></p>
                  <ul>
                    <li>BEAMER PSF format conversion</li>
                    <li>PSF validation and quality checks</li>
                    <li>Noise reduction with Savitzky-Golay filtering</li>
                    <li>Automatic tail extrapolation</li>
                    <li>Proximity effect parameter calculation</li>
                    <li>Multi-file comparison tools</li>
                  </ul>
                  <p><b>Key Features:</b></p>
                  <ul>
                    <li>2D depth-radius visualization</li>
                    <li>XPS-based material compositions</li>
                    <li>Real-time simulation monitoring</li>
                    <li>Comprehensive data analysis</li>
                    <li>Export to multiple formats including BEAMER</li>
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
    app.setApplicationVersion("3.0")
    app.setOrganizationName("EBL Research")

    # Create and show the main window
    window = EBLMainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()