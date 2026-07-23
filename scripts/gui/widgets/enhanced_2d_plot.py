"""
Enhanced2DPlotWidget - 2D depth-radius energy visualization

Extracted from ebl_gui.py (July 2026 modularization). Behavior is unchanged;
only the class was moved out of the monolith.
"""

import csv
import re
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import scipy.interpolate

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QPushButton, QRadioButton, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QSlider, QListWidget, QListWidgetItem, QMessageBox, QFileDialog, QDialog,
    QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit, QSizePolicy, QSplitter,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from widgets.common.status_button import StatusButton

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
        # 3D Surface plot removed - confusing and hard to read values
        self.radio_contour = QRadioButton("Contour Plot")
        self.radio_cross = QRadioButton("Cross Sections")
        self.radio_radial_avg = QRadioButton("Radial Average")

        self.plot_type_group = QButtonGroup()
        self.plot_type_group.addButton(self.radio_2d, 0)
        # ID 1 was 3D Surface (removed)
        self.plot_type_group.addButton(self.radio_contour, 2)
        self.plot_type_group.addButton(self.radio_cross, 3)
        self.plot_type_group.addButton(self.radio_radial_avg, 4)
        self.plot_type_group.buttonClicked.connect(self.update_plot)

        plot_type_layout.addWidget(self.radio_2d)
        # self.radio_3d removed
        plot_type_layout.addWidget(self.radio_contour)
        plot_type_layout.addWidget(self.radio_cross)
        plot_type_layout.addWidget(self.radio_radial_avg)
        plot_type_group.setLayout(plot_type_layout)

        # Colormap selection
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'hot', 'jet', 'turbo'])
        self.colormap_combo.currentTextChanged.connect(self.update_plot)

        # Log scale option
        self.log_scale_check = QCheckBox("Log Scale")
        self.log_scale_check.setChecked(True)
        self.log_scale_check.stateChanged.connect(self.update_plot)

        # Smooth interpolation option
        self.smooth_check = QCheckBox("Smooth Interpolation")
        self.smooth_check.setChecked(True)
        self.smooth_check.setToolTip("Apply Gaussian smoothing and high-resolution interpolation")
        self.smooth_check.stateChanged.connect(self.update_plot)

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
        controls.addWidget(self.smooth_check)
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
                    progress_callback=lambda msg: self.load_2d_button.setText(f"[LOADING] {msg}")
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
            # plot_mode == 1 was 3D Surface (removed)
            elif plot_mode == 2:  # Contour
                self.plot_contour()
            elif plot_mode == 3:  # Cross sections
                self.plot_cross_sections()
            elif plot_mode == 4:  # Radial Average
                self.plot_radial_average()
            else:
                # Shouldn't happen, but fallback to heatmap
                self.plot_heatmap()

            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Plotting Error", f"Failed to create plot: {str(e)}")

    def _extract_resist_thickness(self):
        """
        Extract resist thickness from current data filename or metadata

        Returns:
            float: Resist thickness in nm, or 30.0 nm as default
        """
        # Try to get from metadata if available
        if 'metadata' in self.current_data and 'resist_thickness' in self.current_data['metadata']:
            return float(self.current_data['metadata']['resist_thickness'])

        # Try to parse from filename (e.g., "resist30nm" or "30nm")
        filename = self.current_data.get('filename', '')

        # Pattern 1: resist30nm
        match = re.search(r'resist(\d+)nm', filename, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Pattern 2: standalone number followed by nm
        match = re.search(r'(\d+)nm', filename)
        if match:
            # Check if this might be resist thickness (typically 10-200 nm range)
            thickness = float(match.group(1))
            if 10 <= thickness <= 200:
                return thickness

        # Default fallback
        return 30.0

    def _calculate_psf_characteristic_radius(self, energy_2d, radii):
        """
        Calculate characteristic radius where PSF becomes negligible

        Args:
            energy_2d: 2D energy array (depth x radius)
            radii: Array of radius values

        Returns:
            float: Characteristic radius in nm
        """
        # Use surface (depth index 0) or average over top few nm
        energy_surface = energy_2d[0, :]  # First row (surface)

        max_energy = np.max(energy_surface)

        if max_energy == 0:
            return radii[-1]  # Return max radius if no energy

        # Find radius where energy drops to 1% of maximum
        threshold = max_energy * 0.01
        significant_indices = np.where(energy_surface > threshold)[0]

        if len(significant_indices) > 0:
            char_radius = radii[significant_indices[-1]]
            return char_radius
        else:
            return radii[-1]  # Show all data if threshold not reached

    def plot_heatmap(self):
        """Create 2D heatmap visualization with optional smoothing and intelligent axis limits"""
        ax = self.figure.add_subplot(111)

        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']

        # Apply smoothing if requested
        if self.smooth_check.isChecked():
            try:
                from scipy.ndimage import gaussian_filter
                from scipy.interpolate import RectBivariateSpline

                # Apply Gaussian smoothing to reduce noise
                sigma = 1.5  # Smoothing parameter
                energy_smoothed = gaussian_filter(energy, sigma=sigma)

                # Create high-resolution grid (3× upsampling)
                depths_hr = np.linspace(depths.min(), depths.max(), len(depths) * 3)
                radii_hr = np.linspace(radii.min(), radii.max(), len(radii) * 3)

                # Interpolate to high-resolution grid
                interp = RectBivariateSpline(depths, radii, energy_smoothed)
                energy_hr = interp(depths_hr, radii_hr)

                # Use high-resolution data
                R, D = np.meshgrid(radii_hr, depths_hr)
                energy_plot_data = energy_hr

            except ImportError:
                # Fallback if scipy not available
                R, D = np.meshgrid(radii, depths)
                energy_plot_data = energy
        else:
            # No smoothing
            R, D = np.meshgrid(radii, depths)
            energy_plot_data = energy

        # Apply log scale if selected
        if self.log_scale_check.isChecked():
            # Add small value to avoid log(0)
            energy_plot = np.log10(np.maximum(energy_plot_data, 1e-10))
            label = 'Log10(Energy Deposition) [eV/nm^2]'
        else:
            energy_plot = energy_plot_data
            label = 'Energy Deposition [eV/nm^2]'

        # Create heatmap with improved shading
        cmap = self.colormap_combo.currentText()
        shading_method = 'gouraud' if self.smooth_check.isChecked() else 'auto'
        im = ax.pcolormesh(R, D, energy_plot, cmap=cmap, shading=shading_method)

        # Add colorbar
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label(label)

        # Labels and title
        ax.set_xlabel('Radius [nm]')
        ax.set_ylabel('Depth [nm]')
        ax.set_title(f'Energy Deposition Profile - {self.current_data["filename"]}')

        # Apply intelligent axis limits to show only relevant regions
        resist_thickness = self._extract_resist_thickness()

        # Radial limit: Show up to 3× characteristic radius or where energy drops to 1%
        char_radius = self._calculate_psf_characteristic_radius(energy, radii)
        max_radius_display = min(char_radius * 3, radii.max())

        # Depth limits: Show resist region with small margins
        depth_margin_below = resist_thickness * 0.2  # 20% into substrate
        depth_margin_above = resist_thickness * 0.1  # 10% above surface

        ax.set_xlim(0, max_radius_display)
        ax.set_ylim(-depth_margin_below, depth_margin_above)

        # Add resist boundary lines (now they'll always be visible with new limits)
        ax.axhline(y=0, color='white', linestyle='-',
                   linewidth=2, label='Resist surface', alpha=0.8)
        ax.axhline(y=resist_thickness, color='yellow', linestyle='--',
                   linewidth=2, label=f'Resist/Substrate ({resist_thickness:.0f} nm)', alpha=0.8)
        ax.legend(loc='upper right', fontsize=9)

    # plot_3d_surface method removed - 3D visualization was confusing and hard to read values
    # Users can still visualize depth information using Contour Plot or Cross Sections modes

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
            label = 'Log10(Energy Deposition) [eV/nm^2]'
        else:
            energy_plot = energy
            # Create levels for linear scale
            vmin, vmax = energy_plot.min(), energy_plot.max()
            if vmax > vmin:
                levels = np.linspace(vmin, vmax, 15)
            else:
                levels = 10  # Default number of levels
            label = 'Energy Deposition [eV/nm^2]'

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

        # Apply intelligent axis limits (same as heatmap)
        resist_thickness = self._extract_resist_thickness()
        char_radius = self._calculate_psf_characteristic_radius(energy, radii)
        max_radius_display = min(char_radius * 3, radii.max())

        depth_margin_below = resist_thickness * 0.2
        depth_margin_above = resist_thickness * 0.1

        ax.set_xlim(0, max_radius_display)
        ax.set_ylim(-depth_margin_below, depth_margin_above)

        # Add resist boundary lines
        ax.axhline(y=0, color='white', linestyle='-', linewidth=2,
                   label='Resist surface', alpha=0.8)
        ax.axhline(y=resist_thickness, color='yellow', linestyle='--', linewidth=2,
                   label=f'Resist/Substrate ({resist_thickness:.0f} nm)', alpha=0.8)
        ax.legend(loc='upper right', fontsize=9)

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

    def plot_radial_average(self):
        """Create radial average analysis view with 3 panels"""
        from matplotlib.gridspec import GridSpec

        depths = self.current_data['depths']
        radii = self.current_data['radii']
        energy = self.current_data['energy']

        # Get resist thickness
        resist_thickness = self._extract_resist_thickness()

        # Create GridSpec layout: 2 rows, 2 columns
        gs = GridSpec(2, 2, figure=self.figure, height_ratios=[2, 1], width_ratios=[3, 1])

        ax_main = self.figure.add_subplot(gs[0, 0])      # Main radial average
        ax_depth = self.figure.add_subplot(gs[0, 1])     # Depth profiles
        ax_2d = self.figure.add_subplot(gs[1, :])        # 2D overview

        # Calculate radial average (integrated over depth in resist region)
        resist_mask = (depths >= 0) & (depths <= resist_thickness)
        energy_resist = energy[resist_mask, :]

        radial_average = np.mean(energy_resist, axis=0)
        radial_std = np.std(energy_resist, axis=0)

        # Main plot: Depth-averaged radial profile
        use_log = self.log_scale_check.isChecked()

        if use_log:
            ax_main.loglog(radii, radial_average, 'b-', linewidth=2.5, label='Depth Average')
            # Show standard deviation as shaded region
            ax_main.fill_between(radii,
                                np.maximum(radial_average - radial_std, 1e-10),
                                radial_average + radial_std,
                                alpha=0.3, color='blue', label='±1σ')
        else:
            ax_main.plot(radii, radial_average, 'b-', linewidth=2.5, label='Depth Average')
            ax_main.fill_between(radii,
                                radial_average - radial_std,
                                radial_average + radial_std,
                                alpha=0.3, color='blue', label='±1σ')

        ax_main.set_xlabel('Radius [nm]', fontsize=11)
        ax_main.set_ylabel('Average Energy Deposition [eV/nm²]', fontsize=11)
        ax_main.set_title('Depth-Averaged Radial Profile', fontsize=12, fontweight='bold')
        ax_main.grid(True, alpha=0.3, which='both')
        ax_main.legend(fontsize=9)

        # Depth profiles at selected radii
        radii_indices = [0, len(radii)//4, len(radii)//2, 3*len(radii)//4]
        colors = ['red', 'orange', 'green', 'blue']

        for idx, color in zip(radii_indices, colors):
            if idx < len(radii):
                label = f'r={radii[idx]:.0f} nm'
                if use_log:
                    ax_depth.semilogx(energy[:, idx], depths, color=color,
                                     linewidth=2, label=label)
                else:
                    ax_depth.plot(energy[:, idx], depths, color=color,
                                linewidth=2, label=label)

        # Add resist boundaries
        ax_depth.axhline(y=0, color='k', linestyle='-', alpha=0.5, linewidth=1.5)
        ax_depth.axhline(y=resist_thickness, color='k', linestyle='--',
                        alpha=0.5, linewidth=1.5)

        ax_depth.set_ylabel('Depth [nm]', fontsize=10)
        ax_depth.set_xlabel('Energy [eV/nm²]', fontsize=10)
        ax_depth.set_title('Depth Profiles', fontsize=11, fontweight='bold')
        ax_depth.legend(fontsize=8)
        ax_depth.grid(True, alpha=0.3)

        # Limit depth axis to resist region
        depth_margin = resist_thickness * 0.2
        ax_depth.set_ylim(-depth_margin, resist_thickness * 1.1)

        # 2D overview heatmap (compact)
        R, D = np.meshgrid(radii, depths)

        if use_log:
            energy_plot = np.log10(np.maximum(energy, 1e-10))
            label = 'Log10(Energy) [eV/nm²]'
        else:
            energy_plot = energy
            label = 'Energy [eV/nm²]'

        cmap = self.colormap_combo.currentText()
        im = ax_2d.pcolormesh(R, D, energy_plot, cmap=cmap, shading='gouraud')

        ax_2d.set_xlabel('Radius [nm]', fontsize=10)
        ax_2d.set_ylabel('Depth [nm]', fontsize=10)
        ax_2d.set_title('2D Energy Distribution Overview', fontsize=11, fontweight='bold')

        # Apply same axis limits as heatmap
        char_radius = self._calculate_psf_characteristic_radius(energy, radii)
        max_radius_display = min(char_radius * 3, radii.max())
        ax_2d.set_xlim(0, max_radius_display)
        ax_2d.set_ylim(-depth_margin, resist_thickness * 1.1)

        # Colorbar
        cbar = self.figure.colorbar(im, ax=ax_2d, orientation='horizontal',
                                    pad=0.15, aspect=30)
        cbar.set_label(label, fontsize=9)

        self.figure.tight_layout()

    def update_plot(self):
        """Update plot when settings change"""
        if self.current_data:
            self.plot_2d_data()

    def _update_depth_indicator(self, depth_value):
        """
        Update or create depth indicator line on current plot

        Args:
            depth_value: Depth in nm to mark
        """
        try:
            # Get current axes
            ax = self.figure.axes[0] if self.figure.axes else None
            if ax is None:
                return

            # Remove old depth indicator if it exists
            if hasattr(self, '_depth_indicator_line') and self._depth_indicator_line is not None:
                try:
                    self._depth_indicator_line.remove()
                except:
                    pass

            # Add new depth indicator line
            xlim = ax.get_xlim()
            self._depth_indicator_line = ax.plot(
                xlim, [depth_value, depth_value],
                color='cyan', linestyle='-', linewidth=2.5,
                label=f'Depth: {depth_value:.1f} nm',
                alpha=0.8, zorder=10
            )[0]

            # Update legend if it exists
            if ax.get_legend():
                ax.legend(loc='upper right', fontsize=9)

            # Redraw canvas
            self.canvas.draw()

        except Exception as e:
            # Silently fail if update not possible
            pass

    def update_cross_section(self):
        """Update cross section when slider moves - works in all plot modes"""
        if not self.current_data:
            return

        # Get current depth index and update label
        depth_idx = self.depth_slider.value()
        depths = self.current_data['depths']

        if depth_idx < len(depths):
            current_depth = depths[depth_idx]
            self.depth_label.setText(f"Depth: {current_depth:.1f} nm")

            # Store current depth for use in plotting
            self.current_depth_value = current_depth

        # Get current plot mode
        plot_mode = self.plot_type_group.checkedId()

        if plot_mode == 3:
            # Cross sections mode: full replot
            self.plot_2d_data()
        elif plot_mode in [0, 2]:
            # Heatmap or Contour: add/update depth indicator line
            self._update_depth_indicator(current_depth)
        # Mode 1 was 3D (removed), no action needed

    def _show_save_plot_dialog(self):
        """Show dialog for presentation-ready plot export settings"""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                                       QRadioButton, QButtonGroup, QSpinBox, QDoubleSpinBox,
                                       QLabel, QPushButton, QComboBox, QFormLayout)

        dialog = QDialog(self)
        dialog.setWindowTitle("Save Plot - Presentation Settings")
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout()

        # Size presets group
        size_group = QGroupBox("Plot Size")
        size_layout = QVBoxLayout()

        size_button_group = QButtonGroup(dialog)
        size_presets = {
            "Presentation (7×7 cm)": (7, 7),
            "Presentation Wide (10×7 cm)": (10, 7),
            "Presentation Tall (7×10 cm)": (7, 10),
            "Paper Half-Column (8.5×6 cm)": (8.5, 6),
            "Paper Full-Column (17×12 cm)": (17, 12),
            "Paper Full-Page (17×20 cm)": (17, 20),
            "Custom": None
        }

        self._size_radios = {}
        for i, (name, size) in enumerate(size_presets.items()):
            radio = QRadioButton(name)
            size_button_group.addButton(radio, i)
            size_layout.addWidget(radio)
            self._size_radios[name] = (radio, size)

            if name == "Presentation (7×7 cm)":  # Default selection
                radio.setChecked(True)

        # Custom size inputs
        custom_layout = QFormLayout()
        self._custom_width = QDoubleSpinBox()
        self._custom_width.setRange(1, 50)
        self._custom_width.setValue(7)
        self._custom_width.setSuffix(" cm")
        self._custom_width.setEnabled(False)

        self._custom_height = QDoubleSpinBox()
        self._custom_height.setRange(1, 50)
        self._custom_height.setValue(7)
        self._custom_height.setSuffix(" cm")
        self._custom_height.setEnabled(False)

        custom_layout.addRow("Width:", self._custom_width)
        custom_layout.addRow("Height:", self._custom_height)
        size_layout.addLayout(custom_layout)

        # Enable custom inputs when custom radio selected
        def toggle_custom(checked):
            if self._size_radios["Custom"][0].isChecked():
                self._custom_width.setEnabled(True)
                self._custom_height.setEnabled(True)
            else:
                self._custom_width.setEnabled(False)
                self._custom_height.setEnabled(False)

        for radio, _ in self._size_radios.values():
            radio.toggled.connect(toggle_custom)

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # Quality settings group
        quality_group = QGroupBox("Quality Settings")
        quality_layout = QFormLayout()

        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(150, 600)
        self._dpi_spin.setValue(300)
        self._dpi_spin.setSingleStep(50)
        self._dpi_spin.setSuffix(" DPI")
        quality_layout.addRow("Resolution:", self._dpi_spin)

        self._font_scale = QDoubleSpinBox()
        self._font_scale.setRange(0.5, 3.0)
        self._font_scale.setValue(1.3)
        self._font_scale.setSingleStep(0.1)
        self._font_scale.setSuffix("×")
        self._font_scale.setToolTip("Font size multiplier for better readability")
        quality_layout.addRow("Font Scale:", self._font_scale)

        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        # Display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout()

        self._show_legend = QCheckBox("Include legend")
        self._show_legend.setChecked(False)  # Default: no legend
        self._show_legend.setToolTip("Show/hide legend on saved plot")
        display_layout.addWidget(self._show_legend)

        self._show_metrics = QCheckBox("Include metrics (FWHM, R50, R90)")
        self._show_metrics.setChecked(False)  # Default: no metrics
        self._show_metrics.setToolTip("Show/hide statistics text box")
        display_layout.addWidget(self._show_metrics)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG (Raster)", "PDF (Vector)", "SVG (Vector)", "EPS (Vector)"])
        self._format_combo.setCurrentIndex(1)  # Default to PDF
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        save_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Execute dialog
        if dialog.exec() != QDialog.Accepted:
            return None

        # Get selected size
        for name, (radio, size) in self._size_radios.items():
            if radio.isChecked():
                if name == "Custom":
                    size_cm = (self._custom_width.value(), self._custom_height.value())
                else:
                    size_cm = size
                break

        # Get DPI and font scale
        dpi = self._dpi_spin.value()
        font_scale = self._font_scale.value()

        # Get display options
        show_legend = self._show_legend.isChecked()
        show_metrics = self._show_metrics.isChecked()

        # Get format and file path
        format_text = self._format_combo.currentText()
        format_map = {
            "PNG (Raster)": ("PNG files (*.png)", ".png"),
            "PDF (Vector)": ("PDF files (*.pdf)", ".pdf"),
            "SVG (Vector)": ("SVG files (*.svg)", ".svg"),
            "EPS (Vector)": ("EPS files (*.eps)", ".eps")
        }
        file_filter, ext = format_map[format_text]

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", file_filter
        )

        if not file_path:
            return None

        # Ensure correct extension
        if not file_path.lower().endswith(ext):
            file_path += ext

        return file_path, size_cm, dpi, font_scale, show_legend, show_metrics

    def _save_plot_with_settings(self, file_path, size_cm, dpi, font_scale, show_legend, show_metrics):
        """Save plot with presentation-ready formatting"""
        import matplotlib.pyplot as plt

        # Store current figure settings
        old_size = self.figure.get_size_inches()
        old_dpi = self.figure.dpi

        # Convert cm to inches (matplotlib uses inches)
        size_inches = (size_cm[0] / 2.54, size_cm[1] / 2.54)

        # Temporarily modify figure for export
        self.figure.set_size_inches(size_inches)
        self.figure.set_dpi(dpi)

        # Store original visibility states for restoration
        hidden_artists = []

        # Enhance fonts and line widths for all axes
        for ax in self.figure.axes:
            # Increase font sizes
            ax.title.set_fontsize(11 * font_scale)
            ax.title.set_fontweight('bold')
            ax.xaxis.label.set_fontsize(10 * font_scale)
            ax.yaxis.label.set_fontsize(10 * font_scale)
            ax.tick_params(labelsize=9 * font_scale)

            # Make tick marks more visible
            ax.tick_params(width=1.5, length=6)

            # Increase line widths for plot elements
            for line in ax.get_lines():
                current_width = line.get_linewidth()
                line.set_linewidth(current_width * 1.5)

            # Enhance grid if present
            if ax.get_xgridlines():
                ax.grid(True, alpha=0.3, linewidth=0.8)

            # Handle legend visibility
            legend = ax.get_legend()
            if legend:
                if show_legend:
                    # Make legend more readable
                    legend.set_frame_on(True)
                    legend.get_frame().set_alpha(0.9)
                    legend.get_frame().set_linewidth(1.0)
                    for text in legend.get_texts():
                        text.set_fontsize(9 * font_scale)
                else:
                    # Hide legend for export
                    legend.set_visible(False)
                    hidden_artists.append(legend)

            # Handle metrics text box visibility (if present)
            if not show_metrics:
                for text in ax.texts:
                    # Hide text boxes (typically metrics/statistics)
                    if text.get_visible():
                        text.set_visible(False)
                        hidden_artists.append(text)

        # Save with tight bounding box and high quality
        self.figure.savefig(
            file_path,
            dpi=dpi,
            bbox_inches='tight',
            pad_inches=0.05,
            facecolor='white',
            edgecolor='none'
        )

        # Restore original settings
        self.figure.set_size_inches(old_size)
        self.figure.set_dpi(old_dpi)

        # Restore visibility of hidden elements
        for artist in hidden_artists:
            artist.set_visible(True)

        # Reset formatting (re-draw current plot)
        # This will restore original line widths and fonts
        self.canvas.draw()

    def save_plot(self):
        """Save current plot with presentation-ready options"""
        if not self.current_data:
            QMessageBox.warning(self, "Warning", "No data to save")
            return

        result = self._show_save_plot_dialog()
        if not result:
            return

        file_path, size_cm, dpi, font_scale, show_legend, show_metrics = result

        self.save_plot_button.set_working(True, "Saving...")
        try:
            self._save_plot_with_settings(file_path, size_cm, dpi, font_scale, show_legend, show_metrics)
            QMessageBox.information(self, "Success",
                                  f"Plot saved to {Path(file_path).name}\n"
                                  f"Size: {size_cm[0]}×{size_cm[1]} cm @ {dpi} DPI")
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


