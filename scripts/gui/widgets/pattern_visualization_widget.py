"""
Pattern Dose Visualization Widget
Integrated visualization for pattern exposure results in the EBL GUI
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QComboBox, QSpinBox, QCheckBox,
                              QGroupBox, QFileDialog, QMessageBox, QSlider,
                              QButtonGroup, QRadioButton)
from PySide6.QtCore import Qt, Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.ndimage import gaussian_filter


class PatternVisualizationWidget(QWidget):
    """Widget for visualizing pattern exposure dose distributions"""
    
    # Signals
    data_loaded = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dose_data = None
        self.dose_2d_data = None
        self.current_file = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # File selection group
        file_group = QGroupBox("Pattern Dose Data")
        file_layout = QVBoxLayout()
        
        # File selection
        file_select_layout = QHBoxLayout()
        self.file_label = QLabel("No file loaded")
        self.load_button = QPushButton("Load Dose Data")
        self.load_button.clicked.connect(self.load_dose_file)
        
        file_select_layout.addWidget(QLabel("File:"))
        file_select_layout.addWidget(self.file_label, 1)
        file_select_layout.addWidget(self.load_button)
        file_layout.addLayout(file_select_layout)
        
        # File info
        self.info_label = QLabel("Load a pattern dose file to begin")
        file_layout.addWidget(self.info_label)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Visualization controls
        control_group = QGroupBox("Visualization Controls")
        control_layout = QVBoxLayout()
        
        # Plot type selection
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(QLabel("Plot Type:"))
        
        self.plot_type_group = QButtonGroup(self)
        self.radio_heatmap = QRadioButton("2D Heatmap")
        self.radio_heatmap.setChecked(True)
        self.radio_contour = QRadioButton("Contour")
        self.radio_surface = QRadioButton("3D Surface")
        self.radio_profiles = QRadioButton("Line Profiles")
        
        self.plot_type_group.addButton(self.radio_heatmap, 0)
        self.plot_type_group.addButton(self.radio_contour, 1)
        self.plot_type_group.addButton(self.radio_surface, 2)
        self.plot_type_group.addButton(self.radio_profiles, 3)
        
        plot_type_layout.addWidget(self.radio_heatmap)
        plot_type_layout.addWidget(self.radio_contour)
        plot_type_layout.addWidget(self.radio_surface)
        plot_type_layout.addWidget(self.radio_profiles)
        plot_type_layout.addStretch()
        
        control_layout.addLayout(plot_type_layout)
        
        # Z-slice control
        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel("Z Slice:"))
        
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setEnabled(False)
        self.z_value_label = QLabel("0.0 nm")
        self.z_integrated_check = QCheckBox("Show integrated (all Z)")
        self.z_integrated_check.setChecked(True)
        
        z_layout.addWidget(self.z_slider, 1)
        z_layout.addWidget(self.z_value_label)
        z_layout.addWidget(self.z_integrated_check)
        
        control_layout.addLayout(z_layout)
        
        # Display options
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("Colormap:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 
                                     'hot', 'jet', 'turbo', 'copper'])
        options_layout.addWidget(self.colormap_combo)
        
        self.log_scale_check = QCheckBox("Log Scale")
        self.log_scale_check.setToolTip("Use logarithmic scale to better visualize backscattering")
        options_layout.addWidget(self.log_scale_check)
        
        self.show_grid_check = QCheckBox("Show Grid")
        self.show_grid_check.setChecked(True)
        options_layout.addWidget(self.show_grid_check)
        
        options_layout.addStretch()
        
        control_layout.addLayout(options_layout)
        
        # Edge analysis options
        edge_group = QGroupBox("Edge & Backscattering Analysis")
        edge_layout = QHBoxLayout()
        
        self.show_contours_check = QCheckBox("Show Dose Contours")
        self.show_contours_check.setChecked(True)
        self.show_contours_check.setToolTip("Overlay contour lines to visualize dose levels")
        edge_layout.addWidget(self.show_contours_check)
        
        edge_layout.addWidget(QLabel("Analysis Threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(10, 90)
        self.threshold_spin.setValue(50)
        self.threshold_spin.setSuffix(" %")
        self.threshold_spin.setToolTip("Dose threshold for edge detection")
        edge_layout.addWidget(self.threshold_spin)
        
        self.show_backscatter_check = QCheckBox("Highlight Backscatter")
        self.show_backscatter_check.setToolTip("Emphasize low-dose regions from backscattering")
        edge_layout.addWidget(self.show_backscatter_check)
        
        edge_layout.addStretch()
        edge_group.setLayout(edge_layout)
        control_layout.addWidget(edge_group)
        
        # Update button
        self.update_button = QPushButton("Update Plot")
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self.update_plot)
        control_layout.addWidget(self.update_button)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)
        
        # Connect signals
        self.plot_type_group.buttonClicked.connect(lambda: self.update_plot())
        self.z_slider.valueChanged.connect(self.on_z_slider_changed)
        self.z_integrated_check.toggled.connect(self.on_z_integrated_changed)
        self.colormap_combo.currentTextChanged.connect(lambda: self.update_plot())
        self.log_scale_check.toggled.connect(lambda: self.update_plot())
        self.show_grid_check.toggled.connect(lambda: self.update_plot())
        self.show_contours_check.toggled.connect(lambda: self.update_plot())
        self.threshold_spin.valueChanged.connect(lambda: self.update_plot())
        self.show_backscatter_check.toggled.connect(lambda: self.update_plot())
        
    def load_dose_file(self):
        """Load pattern dose distribution file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Pattern Dose File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            # Load 3D dose data
            self.dose_data = pd.read_csv(file_path, comment='#')
            self.current_file = file_path
            
            # Check for expected columns
            expected_cols = ['X[nm]', 'Y[nm]', 'Z[nm]', 'Energy[keV]', 'Dose[uC/cm^2]']
            if not all(col in self.dose_data.columns for col in expected_cols):
                QMessageBox.warning(self, "Warning", 
                    f"File may not be a pattern dose file.\nExpected columns: {expected_cols}")
            
            # Try to load 2D projection file
            path = Path(file_path)
            dose_2d_path = path.parent / path.name.replace('_distribution', '_2d')
            if dose_2d_path.exists():
                self.dose_2d_data = pd.read_csv(dose_2d_path, comment='#')
                
            # Update UI
            self.file_label.setText(Path(file_path).name)
            self.update_info()
            self.setup_z_slider()
            self.update_button.setEnabled(True)
            
            # Initial plot
            self.update_plot()
            
            # Emit signal
            self.data_loaded.emit(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
            
    def update_info(self):
        """Update information label"""
        if self.dose_data is None:
            return
            
        n_points = len(self.dose_data)
        x_range = self.dose_data['X[nm]'].min(), self.dose_data['X[nm]'].max()
        y_range = self.dose_data['Y[nm]'].min(), self.dose_data['Y[nm]'].max()
        z_range = self.dose_data['Z[nm]'].min(), self.dose_data['Z[nm]'].max()
        
        max_dose = self.dose_data['Dose[uC/cm^2]'].max()
        total_energy = self.dose_data['Energy[keV]'].sum()
        
        info_text = f"Points: {n_points:,}\n"
        info_text += f"X: [{x_range[0]:.1f}, {x_range[1]:.1f}] nm\n"
        info_text += f"Y: [{y_range[0]:.1f}, {y_range[1]:.1f}] nm\n"
        info_text += f"Z: [{z_range[0]:.1f}, {z_range[1]:.1f}] nm\n"
        info_text += f"Max dose: {max_dose:.2f} uC/cm^2\n"
        info_text += f"Total energy: {total_energy:.2e} keV"
        
        self.info_label.setText(info_text)
        
    def setup_z_slider(self):
        """Setup Z-slice slider based on data"""
        if self.dose_data is None:
            return
            
        z_values = np.sort(self.dose_data['Z[nm]'].unique())
        
        if len(z_values) > 1:
            self.z_slider.setEnabled(True)
            self.z_slider.setMinimum(0)
            self.z_slider.setMaximum(len(z_values) - 1)
            self.z_slider.setValue(len(z_values) // 2)
            self.z_values = z_values
            self.on_z_slider_changed(self.z_slider.value())
        else:
            self.z_slider.setEnabled(False)
            self.z_integrated_check.setChecked(True)
            
    def on_z_slider_changed(self, value):
        """Handle Z slider change"""
        if hasattr(self, 'z_values'):
            z_value = self.z_values[value]
            self.z_value_label.setText(f"{z_value:.1f} nm")
            if not self.z_integrated_check.isChecked():
                self.update_plot()
                
    def on_z_integrated_changed(self, checked):
        """Handle integrated checkbox change"""
        self.z_slider.setEnabled(not checked and hasattr(self, 'z_values'))
        self.update_plot()
        
    def create_2d_grid(self, z_slice=None):
        """Create 2D grid from dose data"""
        if self.dose_data is None:
            return None, None, None
            
        # Filter or integrate data
        if z_slice is not None and not self.z_integrated_check.isChecked():
            data = self.dose_data[self.dose_data['Z[nm]'] == z_slice].copy()
        else:
            # Use 2D data if available, otherwise integrate
            if self.dose_2d_data is not None and self.z_integrated_check.isChecked():
                data = self.dose_2d_data.copy()
            else:
                data = self.dose_data.groupby(['X[nm]', 'Y[nm]'])[['Energy[keV]', 'Dose[uC/cm^2]']].sum().reset_index()
                
        # Create grid
        x_unique = np.sort(data['X[nm]'].unique())
        y_unique = np.sort(data['Y[nm]'].unique())
        
        X, Y = np.meshgrid(x_unique, y_unique)
        dose_grid = np.zeros_like(X)
        
        for i, y in enumerate(y_unique):
            for j, x in enumerate(x_unique):
                mask = (data['X[nm]'] == x) & (data['Y[nm]'] == y)
                if mask.any():
                    dose_grid[i, j] = data.loc[mask, 'Dose[uC/cm^2]'].iloc[0]
                    
        return X, Y, dose_grid
        
    def update_plot(self):
        """Update the visualization"""
        if self.dose_data is None:
            return
            
        self.figure.clear()
        
        plot_type = self.plot_type_group.checkedId()
        
        if plot_type == 0:  # Heatmap
            self.plot_heatmap()
        elif plot_type == 1:  # Contour
            self.plot_contour()
        elif plot_type == 2:  # 3D Surface
            self.plot_3d_surface()
        elif plot_type == 3:  # Line Profiles
            self.plot_line_profiles()
            
        self.canvas.draw()
        
    def plot_heatmap(self):
        """Create 2D heatmap with enhanced visualization for edge effects"""
        ax = self.figure.add_subplot(111)
        
        z_slice = self.z_values[self.z_slider.value()] if hasattr(self, 'z_values') and not self.z_integrated_check.isChecked() else None
        X, Y, dose = self.create_2d_grid(z_slice)
        
        if dose is None:
            return
            
        # Apply log scale if requested
        if self.log_scale_check.isChecked() and dose.max() > 0:
            dose_plot = np.log10(dose + 1e-10)
            label = 'log10(Dose) [uC/cm^2]'
            vmin = np.log10(dose.max() * 1e-4)  # Show 4 orders of magnitude
            vmax = np.log10(dose.max())
        else:
            dose_plot = dose
            label = 'Dose [uC/cm^2]'
            vmin = 0
            vmax = dose.max()
            
        # Create heatmap with controlled color range to show backscattering
        im = ax.pcolormesh(X, Y, dose_plot, cmap=self.colormap_combo.currentText(), 
                          shading='auto', vmin=vmin, vmax=vmax)
        
        # Add contour lines to highlight edges and dose levels
        if dose.max() > 0 and self.show_contours_check.isChecked():
            # Add contour lines at key dose levels
            if self.log_scale_check.isChecked():
                # Logarithmic contours
                contour_levels = np.logspace(np.log10(dose.max() * 0.001), 
                                           np.log10(dose.max() * 0.9), 10)
                contour_data = dose
            else:
                # Linear contours including user-defined threshold
                threshold = self.threshold_spin.value() / 100.0
                contour_levels = dose.max() * np.array([0.01, 0.1, 0.3, threshold, 0.7, 0.9])
                contour_data = dose
                
            contours = ax.contour(X, Y, contour_data, levels=contour_levels, 
                                 colors='white', alpha=0.5, linewidths=0.5)
            
            # Label the threshold contour to show edge definition
            threshold_level = dose.max() * (self.threshold_spin.value() / 100.0)
            ax.clabel(contours, [threshold_level], inline=True, 
                     fontsize=8, fmt='%.0f')
                     
        # Highlight backscattering regions if requested
        if self.show_backscatter_check.isChecked() and dose.max() > 0:
            # Create a mask for low-dose regions (1-10% of max)
            backscatter_mask = (dose > dose.max() * 0.01) & (dose < dose.max() * 0.1)
            if backscatter_mask.any():
                # Overlay semi-transparent color on backscatter regions
                ax.contourf(X, Y, backscatter_mask.astype(float), levels=[0.5, 1.5],
                           colors=['yellow'], alpha=0.2)
        
        # Colorbar
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label(label)
        
        # Add dose threshold lines to colorbar
        if not self.log_scale_check.isChecked() and dose.max() > 0:
            # Mark typical resist thresholds
            threshold_doses = [dose.max() * 0.5, dose.max() * 0.3]  # Example thresholds
            for thresh in threshold_doses:
                cbar.ax.axhline(y=thresh, color='red', linestyle='--', alpha=0.5)
        
        # Labels
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        
        # Enhanced title with key metrics
        if dose.max() > 0:
            # Calculate edge metrics
            edge_dose = dose.max() * 0.5  # 50% dose threshold
            above_threshold = dose > edge_dose
            
            if z_slice is not None:
                title = f'Dose Distribution at Z = {z_slice:.1f} nm\n'
            else:
                title = 'Integrated Dose Distribution\n'
                
            title += f'Max: {dose.max():.1f} uC/cm^2, '
            
            # Estimate FWHM for edge broadening
            if above_threshold.any():
                y_mid = dose.shape[0] // 2
                x_profile = dose[y_mid, :]
                above_half = x_profile > edge_dose
                if above_half.any():
                    indices = np.where(above_half)[0]
                    if len(indices) > 1:
                        fwhm = X[0, indices[-1]] - X[0, indices[0]]
                        title += f'FWHM: {fwhm:.1f} nm'
                        
            ax.set_title(title)
        else:
            if z_slice is not None:
                ax.set_title(f'Dose Distribution at Z = {z_slice:.1f} nm')
            else:
                ax.set_title('Integrated Dose Distribution')
            
        ax.set_aspect('equal')
        
        if self.show_grid_check.isChecked():
            ax.grid(True, alpha=0.3)
            
    def plot_contour(self):
        """Create contour plot"""
        ax = self.figure.add_subplot(111)
        
        z_slice = self.z_values[self.z_slider.value()] if hasattr(self, 'z_values') and not self.z_integrated_check.isChecked() else None
        X, Y, dose = self.create_2d_grid(z_slice)
        
        if dose is None:
            return
            
        # Apply smoothing for better contours
        dose_smooth = gaussian_filter(dose, sigma=0.5)
        
        # Create contour plot
        levels = 20
        contourf = ax.contourf(X, Y, dose_smooth, levels=levels, 
                              cmap=self.colormap_combo.currentText(), alpha=0.7)
        contour = ax.contour(X, Y, dose_smooth, levels=levels, colors='black', 
                            alpha=0.4, linewidths=0.5)
        
        # Label contours
        ax.clabel(contour, contour.levels[::2], inline=True, fontsize=8, fmt='%.0f')
        
        # Colorbar
        cbar = self.figure.colorbar(contourf, ax=ax)
        cbar.set_label('Dose [uC/cm^2]')
        
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_title('Dose Distribution Contours')
        ax.set_aspect('equal')
        
        if self.show_grid_check.isChecked():
            ax.grid(True, alpha=0.3)
            
    def plot_3d_surface(self):
        """Create 3D surface plot"""
        ax = self.figure.add_subplot(111, projection='3d')
        
        z_slice = self.z_values[self.z_slider.value()] if hasattr(self, 'z_values') and not self.z_integrated_check.isChecked() else None
        X, Y, dose = self.create_2d_grid(z_slice)
        
        if dose is None:
            return
            
        # Downsample for performance
        step = max(1, len(X) // 30)
        X_down = X[::step, ::step]
        Y_down = Y[::step, ::step]
        dose_down = dose[::step, ::step]
        
        # Create surface
        surf = ax.plot_surface(X_down, Y_down, dose_down, 
                              cmap=self.colormap_combo.currentText(),
                              edgecolor='none', alpha=0.8)
        
        # Colorbar
        self.figure.colorbar(surf, ax=ax, label='Dose [uC/cm^2]', shrink=0.5)
        
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_zlabel('Dose [uC/cm^2]')
        ax.set_title('3D Dose Distribution')
        
    def plot_line_profiles(self):
        """Plot line profiles with edge analysis"""
        # Create two subplots - one for each profile
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212)
        
        X, Y, dose = self.create_2d_grid()
        
        if dose is None:
            return
            
        # Get center indices
        center_y = len(Y) // 2
        center_x = len(X[0]) // 2
        
        # Extract profiles
        x_positions = X[0, :]
        y_positions = Y[:, 0]
        x_profile = dose[center_y, :]
        y_profile = dose[:, center_x]
        
        # Find edges and calculate metrics
        max_dose = max(x_profile.max(), y_profile.max())
        
        # Plot X profile
        ax1.plot(x_positions, x_profile, 'b-', linewidth=2)
        
        # Add dose threshold lines
        for threshold, label, color in [(0.5, '50%', 'red'), 
                                       (0.3, '30%', 'orange'),
                                       (0.1, '10%', 'yellow')]:
            thresh_dose = max_dose * threshold
            ax1.axhline(y=thresh_dose, color=color, linestyle='--', alpha=0.5, 
                       label=f'{label} dose ({thresh_dose:.1f} uC/cm^2)')
            
        # Calculate and show edge metrics for X profile
        self._add_edge_metrics(ax1, x_positions, x_profile, 'X')
        
        ax1.set_ylabel('Dose [uC/cm^2]')
        ax1.set_title('X Profile (through Y=0)')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # Use log scale for better visibility of backscattering
        if self.log_scale_check.isChecked() and max_dose > 0:
            ax1.set_yscale('log')
            ax1.set_ylim(max_dose * 1e-4, max_dose * 2)
        
        # Plot Y profile
        ax2.plot(y_positions, y_profile, 'r-', linewidth=2)
        
        # Add dose threshold lines
        for threshold, label, color in [(0.5, '50%', 'red'), 
                                       (0.3, '30%', 'orange'),
                                       (0.1, '10%', 'yellow')]:
            thresh_dose = max_dose * threshold
            ax2.axhline(y=thresh_dose, color=color, linestyle='--', alpha=0.5, 
                       label=f'{label} dose ({thresh_dose:.1f} uC/cm^2)')
            
        # Calculate and show edge metrics for Y profile
        self._add_edge_metrics(ax2, y_positions, y_profile, 'Y')
        
        ax2.set_xlabel('Position [nm]')
        ax2.set_ylabel('Dose [uC/cm^2]')
        ax2.set_title('Y Profile (through X=0)')
        ax2.legend(loc='upper right', fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        # Use log scale for better visibility of backscattering
        if self.log_scale_check.isChecked() and max_dose > 0:
            ax2.set_yscale('log')
            ax2.set_ylim(max_dose * 1e-4, max_dose * 2)
            
        self.figure.tight_layout()
        
    def _add_edge_metrics(self, ax, positions, profile, axis_name):
        """Add edge broadening metrics to profile plot"""
        if profile.max() == 0:
            return
            
        # Find edges at 50% dose
        half_max = profile.max() * 0.5
        above_half = profile > half_max
        
        if above_half.any():
            indices = np.where(above_half)[0]
            if len(indices) > 1:
                left_edge = positions[indices[0]]
                right_edge = positions[indices[-1]]
                fwhm = right_edge - left_edge
                center = (left_edge + right_edge) / 2
                
                # Mark edges
                ax.axvline(x=left_edge, color='green', linestyle=':', alpha=0.7)
                ax.axvline(x=right_edge, color='green', linestyle=':', alpha=0.7)
                
                # Add FWHM annotation
                ax.annotate('', xy=(right_edge, half_max), xytext=(left_edge, half_max),
                           arrowprops=dict(arrowstyle='<->', color='green'))
                ax.text(center, half_max * 1.1, f'FWHM: {fwhm:.1f} nm', 
                       ha='center', va='bottom', fontsize=9)
                
                # Calculate edge slope (10-90% distance)
                dose_10 = profile.max() * 0.1
                dose_90 = profile.max() * 0.9
                
                # Left edge slope
                left_region = profile[:indices[0] + 5]
                if len(left_region) > 2:
                    mask_10_90 = (left_region > dose_10) & (left_region < dose_90)
                    if mask_10_90.any():
                        edge_indices = np.where(mask_10_90)[0]
                        if len(edge_indices) > 1:
                            edge_width = positions[edge_indices[-1]] - positions[edge_indices[0]]
                            ax.text(positions[indices[0]], profile.max() * 0.05, 
                                   f'Edge: {edge_width:.1f} nm', 
                                   ha='center', va='bottom', fontsize=8, rotation=90)