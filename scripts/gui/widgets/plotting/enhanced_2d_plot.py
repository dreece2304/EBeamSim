"""
Enhanced 2D plotting widget for depth-radius visualization
Extracted from monolithic GUI for modular architecture
"""

from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, 
    QButtonGroup, QComboBox, QCheckBox, QSlider, QLabel, 
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from core.file_manager import FileManager
from widgets.common.status_button import StatusButton


class Enhanced2DPlotWidget(QWidget):
    """Enhanced widget for 2D depth-radius visualization with fixed contour plotting"""

    def __init__(self, file_manager: FileManager):
        super().__init__()
        self.file_manager = file_manager
        self.current_data: Optional[Dict[str, Any]] = None
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
            label = 'Log10(Energy Deposition) [eV/nm^2]'
        else:
            energy_plot = energy
            label = 'Energy Deposition [eV/nm^2]'

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