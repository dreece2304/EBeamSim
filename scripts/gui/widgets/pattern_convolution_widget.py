#!/usr/bin/env python3
"""
Pattern Convolution Widget for GUI
Real-time pattern dose visualization using PSF convolution
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QSpinBox, QDoubleSpinBox, QGroupBox,
                              QGridLayout, QFileDialog, QComboBox, QCheckBox,
                              QProgressBar, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap

import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psf_convolution import PSFConvolution
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import logging

class ConvolutionWorker(QThread):
    """Worker thread for convolution calculation"""
    progress = Signal(int)
    finished = Signal(object)
    log_message = Signal(str)

    def __init__(self, psf_file, pattern_type, size_um, dose_uc_cm2, shot_pitch_nm):
        super().__init__()
        self.psf_file = psf_file
        self.pattern_type = pattern_type
        self.size_um = size_um
        self.dose_uc_cm2 = dose_uc_cm2
        self.shot_pitch_nm = shot_pitch_nm

    def run(self):
        try:
            # Initialize convolution engine
            self.log_message.emit("Loading PSF data...")
            self.progress.emit(10)
            conv = PSFConvolution(self.psf_file)

            # Convert to 2D
            self.log_message.emit("Converting PSF to 2D grid...")
            self.progress.emit(30)
            conv.radial_to_2d(max_radius_nm=150000, grid_size_nm=100)

            # Create pattern
            self.log_message.emit(f"Creating {self.pattern_type} pattern...")
            self.progress.emit(50)

            if self.pattern_type == "Square":
                conv.create_square_pattern(size_um=self.size_um,
                                          dose_uc_cm2=self.dose_uc_cm2,
                                          shot_pitch_nm=self.shot_pitch_nm)
            # Add other pattern types here

            # Perform convolution
            self.log_message.emit("Calculating dose distribution...")
            self.progress.emit(70)
            conv.convolve_pattern()

            self.progress.emit(100)
            self.log_message.emit("Convolution complete!")
            self.finished.emit(conv)

        except Exception as e:
            self.log_message.emit(f"Error: {str(e)}")
            self.finished.emit(None)


class PatternConvolutionWidget(QWidget):
    """Widget for pattern dose calculation using PSF convolution"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.psf_file = None
        self.conv_result = None
        self.available_psf_files = []
        self.init_ui()
        self.scan_for_psf_files()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # PSF Selection
        psf_group = QGroupBox("PSF Selection")
        psf_layout = QVBoxLayout()

        # Dropdown for available PSF files
        psf_select_layout = QHBoxLayout()
        psf_select_layout.addWidget(QLabel("Available PSFs:"))

        self.psf_combo = QComboBox()
        self.psf_combo.currentTextChanged.connect(self.select_psf_from_combo)
        psf_select_layout.addWidget(self.psf_combo, stretch=1)

        self.refresh_psf_btn = QPushButton("Refresh")
        self.refresh_psf_btn.clicked.connect(self.scan_for_psf_files)
        psf_select_layout.addWidget(self.refresh_psf_btn)

        psf_layout.addLayout(psf_select_layout)

        # Current PSF info
        self.psf_label = QLabel("No PSF loaded")
        self.psf_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        psf_layout.addWidget(self.psf_label)

        # File operations
        psf_file_layout = QHBoxLayout()
        self.load_psf_btn = QPushButton("Load Custom PSF")
        self.load_psf_btn.clicked.connect(self.load_psf)
        psf_file_layout.addWidget(self.load_psf_btn)

        self.use_latest_btn = QPushButton("Use Latest Simulation")
        self.use_latest_btn.clicked.connect(self.use_latest_psf)
        psf_file_layout.addWidget(self.use_latest_btn)

        psf_layout.addLayout(psf_file_layout)
        psf_group.setLayout(psf_layout)

        # Pattern Settings
        pattern_group = QGroupBox("Pattern Settings")
        pattern_layout = QGridLayout()

        pattern_layout.addWidget(QLabel("Pattern Type:"), 0, 0)
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["Square", "Circle", "Line", "Dot Array"])
        pattern_layout.addWidget(self.pattern_combo, 0, 1)

        pattern_layout.addWidget(QLabel("Size (µm):"), 1, 0)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(1, 1000)
        self.size_spin.setValue(100)
        self.size_spin.setSuffix(" µm")
        pattern_layout.addWidget(self.size_spin, 1, 1)

        pattern_layout.addWidget(QLabel("Dose (µC/cm²):"), 2, 0)
        self.dose_spin = QDoubleSpinBox()
        self.dose_spin.setRange(10, 20000)
        self.dose_spin.setValue(500)
        self.dose_spin.setSuffix(" µC/cm²")
        pattern_layout.addWidget(self.dose_spin, 2, 1)

        pattern_layout.addWidget(QLabel("Shot Pitch (nm):"), 3, 0)
        self.pitch_spin = QSpinBox()
        self.pitch_spin.setRange(1, 100)
        self.pitch_spin.setValue(34)
        self.pitch_spin.setSuffix(" nm")
        pattern_layout.addWidget(self.pitch_spin, 3, 1)

        pattern_group.setLayout(pattern_layout)

        # Calculation Controls
        calc_group = QGroupBox("Calculation")
        calc_layout = QVBoxLayout()

        self.calculate_btn = QPushButton("Calculate Dose Distribution")
        self.calculate_btn.clicked.connect(self.calculate_dose)
        self.calculate_btn.setEnabled(False)
        calc_layout.addWidget(self.calculate_btn)

        self.progress_bar = QProgressBar()
        calc_layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(100)
        self.log_output.setReadOnly(True)
        calc_layout.addWidget(self.log_output)

        calc_group.setLayout(calc_layout)

        # Visualization Area
        viz_group = QGroupBox("Dose Distribution Visualization")
        viz_layout = QVBoxLayout()

        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        viz_layout.addWidget(self.canvas)

        # Initial draw to prevent white screen
        self.canvas.draw()

        # View controls
        view_controls = QHBoxLayout()

        self.view_2d_btn = QPushButton("2D View")
        self.view_2d_btn.clicked.connect(self.show_2d_view)
        self.view_2d_btn.setEnabled(False)
        view_controls.addWidget(self.view_2d_btn)

        self.view_3d_btn = QPushButton("3D View")
        self.view_3d_btn.clicked.connect(self.show_3d_view)
        self.view_3d_btn.setEnabled(False)
        view_controls.addWidget(self.view_3d_btn)

        self.export_btn = QPushButton("Export Data")
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setEnabled(False)
        view_controls.addWidget(self.export_btn)

        view_controls.addStretch()

        self.log_scale_check = QCheckBox("Log Scale")
        self.log_scale_check.stateChanged.connect(self.update_visualization)
        view_controls.addWidget(self.log_scale_check)

        viz_layout.addLayout(view_controls)
        viz_group.setLayout(viz_layout)

        # Statistics Panel
        stats_group = QGroupBox("Dose Statistics")
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        stats_layout = QVBoxLayout()
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)

        # Add all groups to main layout
        layout.addWidget(psf_group)
        layout.addWidget(pattern_group)
        layout.addWidget(calc_group)
        layout.addWidget(viz_group)
        layout.addWidget(stats_group)

        self.setLayout(layout)

    def scan_for_psf_files(self):
        """Scan for available PSF files in common locations"""
        self.available_psf_files = []
        self.psf_combo.clear()

        # Look in common directories
        search_paths = [
            Path.cwd(),  # Current directory
            Path.cwd() / "build",  # Build directory
            Path.cwd() / "output",  # Output directory
            Path.home() / "projects" / "ebl-simulation" / "build"  # Project build
        ]

        # Look for PSF files
        psf_patterns = ["psf_*.csv", "*_psf.csv", "ebl_psf_*.csv"]

        for path in search_paths:
            if path.exists():
                for pattern in psf_patterns:
                    for file in path.glob(pattern):
                        # Skip 2D PSF files
                        if "2d" not in file.name.lower() and "pattern" not in file.name.lower():
                            self.available_psf_files.append(file)

        # Sort by modification time (newest first)
        self.available_psf_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Add to combo box
        if self.available_psf_files:
            for file in self.available_psf_files[:10]:  # Show max 10 most recent
                # Create display name with material info if available
                display_name = file.name
                if "snmld" in file.name.lower() or "sn" in file.name.lower():
                    display_name = f"[Sn-MLD] {display_name}"
                elif "alucone" in file.name.lower():
                    display_name = f"[Alucone] {display_name}"
                elif "pmma" in file.name.lower():
                    display_name = f"[PMMA] {display_name}"

                self.psf_combo.addItem(display_name, userData=str(file))

            self.log_output.append(f"Found {len(self.available_psf_files)} PSF files")
            # Auto-select the first (most recent)
            self.psf_combo.setCurrentIndex(0)
        else:
            self.psf_combo.addItem("No PSF files found")
            self.log_output.append("No PSF files found. Run a simulation first.")

    def select_psf_from_combo(self, text):
        """Handle PSF selection from combo box"""
        if text and text != "No PSF files found":
            file_path = self.psf_combo.currentData()
            if file_path and Path(file_path).exists():
                self.psf_file = file_path
                # Extract info from filename
                file_name = Path(file_path).name
                info = f"PSF: {file_name}"

                # Try to get file size and date
                file_stats = Path(file_path).stat()
                size_kb = file_stats.st_size / 1024
                mod_time = datetime.fromtimestamp(file_stats.st_mtime)
                info += f"\nSize: {size_kb:.1f} KB"
                info += f"\nModified: {mod_time.strftime('%Y-%m-%d %H:%M')}"

                self.psf_label.setText(info)
                self.calculate_btn.setEnabled(True)
                self.log_output.append(f"Selected PSF: {file_name}")

    def use_latest_psf(self):
        """Use the most recent PSF file"""
        if self.available_psf_files:
            latest = self.available_psf_files[0]
            self.psf_file = str(latest)
            self.psf_label.setText(f"PSF: {latest.name} (latest)")
            self.calculate_btn.setEnabled(True)
            self.log_output.append(f"Using latest PSF: {latest.name}")

            # Update combo box selection
            for i in range(self.psf_combo.count()):
                if self.psf_combo.itemData(i) == str(latest):
                    self.psf_combo.setCurrentIndex(i)
                    break
        else:
            self.log_output.append("No PSF files available")

    def load_psf(self):
        """Load PSF from custom file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF File", "", "CSV Files (*.csv);;All Files (*.*)")

        if file_path:
            self.psf_file = file_path
            self.psf_label.setText(f"PSF: {os.path.basename(file_path)} (custom)")
            self.calculate_btn.setEnabled(True)
            self.log_output.append(f"Loaded custom PSF: {file_path}")
            # Add to combo box if not already there
            self.psf_combo.addItem(f"[Custom] {os.path.basename(file_path)}", userData=file_path)

    def calculate_dose(self):
        """Calculate dose distribution using convolution"""
        if not self.psf_file:
            self.log_output.append("Error: No PSF loaded")
            return

        # Disable controls during calculation
        self.calculate_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # Create worker thread
        self.worker = ConvolutionWorker(
            self.psf_file,
            self.pattern_combo.currentText(),
            self.size_spin.value(),
            self.dose_spin.value(),
            self.pitch_spin.value()
        )

        # Connect signals
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.log_output.append)
        self.worker.finished.connect(self.calculation_finished)

        # Start calculation
        self.worker.start()

    def calculation_finished(self, result):
        """Handle calculation completion"""
        self.calculate_btn.setEnabled(True)

        if result:
            self.conv_result = result
            self.view_2d_btn.setEnabled(True)
            self.view_3d_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

            # Show 2D view by default
            self.show_2d_view()

            # Update statistics
            self.update_statistics()
        else:
            self.log_output.append("Calculation failed!")

    def show_2d_view(self):
        """Display 2D dose distribution"""
        if not self.conv_result:
            return

        self.figure.clear()

        # Create subplots
        axes = self.figure.subplots(2, 2)

        # Get dose data
        dose_map = self.conv_result.dose_map
        grid_size = self.conv_result.grid_size_nm

        # Convert to physical units
        extent_um = np.array([-dose_map.shape[0]/2, dose_map.shape[0]/2,
                             -dose_map.shape[1]/2, dose_map.shape[1]/2]) * grid_size / 1000

        # 1. Full dose map
        if self.log_scale_check.isChecked():
            data = np.log10(dose_map + 1e-10)
            label = 'log₁₀(Dose)'
        else:
            data = dose_map
            label = 'Dose (µC/cm²)'

        im1 = axes[0, 0].imshow(data, extent=extent_um, cmap='hot', aspect='auto')
        axes[0, 0].set_title('Full Dose Distribution')
        axes[0, 0].set_xlabel('X (µm)')
        axes[0, 0].set_ylabel('Y (µm)')
        self.figure.colorbar(im1, ax=axes[0, 0], label=label)

        # 2. Center zoom
        center = dose_map.shape[0] // 2
        zoom_range = int(self.size_spin.value() * 1500 / grid_size)  # 1.5x pattern size

        dose_center = dose_map[center-zoom_range:center+zoom_range,
                              center-zoom_range:center+zoom_range]

        extent_zoom = np.array([-zoom_range, zoom_range,
                               -zoom_range, zoom_range]) * grid_size / 1000

        im2 = axes[0, 1].imshow(dose_center, extent=extent_zoom, cmap='viridis', aspect='auto')
        axes[0, 1].set_title('Pattern Region')
        axes[0, 1].set_xlabel('X (µm)')
        axes[0, 1].set_ylabel('Y (µm)')
        self.figure.colorbar(im2, ax=axes[0, 1], label='Dose (µC/cm²)')

        # Add pattern boundary
        half_size = self.size_spin.value() / 2
        rect = plt.Rectangle((-half_size, -half_size),
                            self.size_spin.value(),
                            self.size_spin.value(),
                            fill=False, edgecolor='red', linewidth=2)
        axes[0, 1].add_patch(rect)

        # 3. Line cuts
        line_h = dose_map[center, :]
        line_v = dose_map[:, center]
        x = (np.arange(len(line_h)) - center) * grid_size / 1000

        axes[1, 0].plot(x, line_h, 'b-', label='Horizontal')
        axes[1, 0].plot(x, line_v, 'r-', label='Vertical')
        axes[1, 0].set_title('Line Cuts Through Center')
        axes[1, 0].set_xlabel('Position (µm)')
        axes[1, 0].set_ylabel('Dose (µC/cm²)')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].legend()
        axes[1, 0].set_xlim(-self.size_spin.value(), self.size_spin.value())

        # 4. Radial average
        axes[1, 1].axis('off')
        info_text = f"""Pattern: {self.pattern_combo.currentText()}
Size: {self.size_spin.value()} µm
Dose: {self.dose_spin.value()} µC/cm²
Shot Pitch: {self.pitch_spin.value()} nm

Center Dose: {dose_map[center, center]:.1f} µC/cm²
Edge/Center: {self.get_edge_center_ratio():.2f}
Uniformity: {self.get_uniformity():.1f}%"""

        axes[1, 1].text(0.1, 0.8, info_text, transform=axes[1, 1].transAxes,
                       fontsize=10, verticalalignment='top')

        self.figure.tight_layout()
        self.canvas.draw()

    def show_3d_view(self):
        """Display 3D dose distribution"""
        if not self.conv_result:
            return

        self.figure.clear()

        # Create 3D subplot
        ax = self.figure.add_subplot(111, projection='3d')

        # Get dose data (downsample for performance)
        dose_map = self.conv_result.dose_map[::5, ::5]  # Downsample by 5
        grid_size = self.conv_result.grid_size_nm * 5  # Adjust grid size

        # Create mesh
        x = np.arange(dose_map.shape[0]) * grid_size / 1000
        y = np.arange(dose_map.shape[1]) * grid_size / 1000
        x = x - x.mean()
        y = y - y.mean()
        X, Y = np.meshgrid(x, y)

        # Plot surface
        surf = ax.plot_surface(X, Y, dose_map, cmap='plasma',
                              edgecolor='none', alpha=0.9)

        ax.set_title('3D Dose Distribution')
        ax.set_xlabel('X (µm)')
        ax.set_ylabel('Y (µm)')
        ax.set_zlabel('Dose (µC/cm²)')

        self.figure.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        self.canvas.draw()

    def update_visualization(self):
        """Update current visualization"""
        if self.conv_result:
            self.show_2d_view()

    def update_statistics(self):
        """Calculate and display dose statistics"""
        if not self.conv_result:
            return

        dose_map = self.conv_result.dose_map
        center = dose_map.shape[0] // 2
        grid_size = self.conv_result.grid_size_nm

        # Get pattern region
        half_size_px = int(self.size_spin.value() * 500 / grid_size)  # Convert µm to pixels
        dose_inside = dose_map[center-half_size_px:center+half_size_px,
                              center-half_size_px:center+half_size_px]

        stats = f"""Dose Statistics:

Inside Pattern:
  Center: {dose_map[center, center]:.1f} µC/cm²
  Mean: {dose_inside.mean():.1f} µC/cm²
  Std Dev: {dose_inside.std():.1f} µC/cm²
  Min: {dose_inside.min():.1f} µC/cm²
  Max: {dose_inside.max():.1f} µC/cm²

Uniformity: {(1 - dose_inside.std()/dose_inside.mean())*100:.1f}%
Edge/Center Ratio: {dose_inside.min()/dose_map[center, center]:.3f}

Proximity Effect:
  10 µm outside: {self.get_proximity_dose(10):.1f} µC/cm²
  20 µm outside: {self.get_proximity_dose(20):.1f} µC/cm²
  50 µm outside: {self.get_proximity_dose(50):.1f} µC/cm²
"""
        self.stats_text.setText(stats)

    def get_edge_center_ratio(self):
        """Calculate edge to center dose ratio"""
        if not self.conv_result:
            return 0

        dose_map = self.conv_result.dose_map
        center = dose_map.shape[0] // 2
        grid_size = self.conv_result.grid_size_nm

        half_size_px = int(self.size_spin.value() * 500 / grid_size)

        center_dose = dose_map[center, center]
        edge_dose = dose_map[center-half_size_px, center]

        return edge_dose / center_dose if center_dose > 0 else 0

    def get_uniformity(self):
        """Calculate dose uniformity inside pattern"""
        if not self.conv_result:
            return 0

        dose_map = self.conv_result.dose_map
        center = dose_map.shape[0] // 2
        grid_size = self.conv_result.grid_size_nm

        half_size_px = int(self.size_spin.value() * 500 / grid_size)
        dose_inside = dose_map[center-half_size_px:center+half_size_px,
                              center-half_size_px:center+half_size_px]

        mean_dose = dose_inside.mean()
        if mean_dose > 0:
            return (1 - dose_inside.std() / mean_dose) * 100
        return 0

    def get_proximity_dose(self, distance_um):
        """Get dose at specified distance outside pattern"""
        if not self.conv_result:
            return 0

        dose_map = self.conv_result.dose_map
        center = dose_map.shape[0] // 2
        grid_size = self.conv_result.grid_size_nm

        pattern_edge_px = int(self.size_spin.value() * 500 / grid_size)
        distance_px = int(distance_um * 1000 / grid_size)

        sample_point = center - pattern_edge_px - distance_px
        if 0 <= sample_point < dose_map.shape[0]:
            return dose_map[sample_point, center]
        return 0

    def export_data(self):
        """Export dose data and visualizations"""
        if not self.conv_result:
            return

        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")

        if dir_path:
            import os
            from pathlib import Path

            base_name = f"{self.pattern_combo.currentText()}_{self.size_spin.value()}um_{self.dose_spin.value()}uC"

            # Save dose map
            np.save(os.path.join(dir_path, f"{base_name}_dose.npy"),
                   self.conv_result.dose_map)

            # Save current figure
            self.figure.savefig(os.path.join(dir_path, f"{base_name}_visualization.png"),
                              dpi=150, bbox_inches='tight')

            # Save statistics
            with open(os.path.join(dir_path, f"{base_name}_stats.txt"), 'w') as f:
                f.write(self.stats_text.toPlainText())

            self.log_output.append(f"Data exported to {dir_path}")