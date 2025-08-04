"""
Enhanced Pattern Dose Visualizer
Properly shows patterned areas with appropriate scaling and resolution
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QComboBox, QSpinBox, QCheckBox,
                              QGroupBox, QFileDialog, QMessageBox, QSlider,
                              QDoubleSpinBox, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter


class PatternDoseVisualizer(QWidget):
    """Enhanced visualization for pattern dose with proper scaling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dose_data = None
        self.grid_data = None
        self.pattern_bounds = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup UI with enhanced controls"""
        layout = QVBoxLayout(self)
        
        # File controls
        file_group = QGroupBox("Data File")
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file loaded")
        self.load_button = QPushButton("Load Pattern Dose")
        self.load_button.clicked.connect(self.load_dose_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.load_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Visualization controls
        vis_group = QGroupBox("Visualization Controls")
        vis_layout = QVBoxLayout()
        
        # View options
        view_layout = QHBoxLayout()
        view_layout.addWidget(QLabel("View:"))
        
        self.view_combo = QComboBox()
        self.view_combo.addItems([
            "Full Dose Map",
            "Pattern Region Only", 
            "Pattern + Proximity",
            "Backscatter Region",
            "Line Cut Analysis"
        ])
        self.view_combo.currentTextChanged.connect(self.update_visualization)
        view_layout.addWidget(self.view_combo)
        
        view_layout.addWidget(QLabel("Z Layer:"))
        self.z_combo = QComboBox()
        self.z_combo.currentTextChanged.connect(self.update_visualization)
        view_layout.addWidget(self.z_combo)
        
        view_layout.addStretch()
        vis_layout.addLayout(view_layout)
        
        # Scale controls
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Dose Scale:"))
        
        self.scale_mode = QButtonGroup()
        self.linear_radio = QRadioButton("Linear")
        self.log_radio = QRadioButton("Log")
        self.log_radio.setChecked(True)
        self.custom_radio = QRadioButton("Custom")
        
        self.scale_mode.addButton(self.linear_radio, 0)
        self.scale_mode.addButton(self.log_radio, 1)
        self.scale_mode.addButton(self.custom_radio, 2)
        self.scale_mode.buttonClicked.connect(self.update_scale_controls)
        
        scale_layout.addWidget(self.linear_radio)
        scale_layout.addWidget(self.log_radio)
        scale_layout.addWidget(self.custom_radio)
        
        scale_layout.addWidget(QLabel("Min:"))
        self.dose_min_spin = QDoubleSpinBox()
        self.dose_min_spin.setRange(0, 100000)
        self.dose_min_spin.setDecimals(1)
        self.dose_min_spin.setValue(0.1)
        self.dose_min_spin.setSuffix(" µC/cm²")
        self.dose_min_spin.setEnabled(False)
        scale_layout.addWidget(self.dose_min_spin)
        
        scale_layout.addWidget(QLabel("Max:"))
        self.dose_max_spin = QDoubleSpinBox()
        self.dose_max_spin.setRange(0, 100000)
        self.dose_max_spin.setDecimals(1)
        self.dose_max_spin.setValue(10000)
        self.dose_max_spin.setSuffix(" µC/cm²")
        self.dose_max_spin.setEnabled(False)
        scale_layout.addWidget(self.dose_max_spin)
        
        scale_layout.addStretch()
        vis_layout.addLayout(scale_layout)
        
        # Display options
        display_layout = QHBoxLayout()
        
        display_layout.addWidget(QLabel("Colormap:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            'viridis', 'plasma', 'hot', 'jet', 'turbo',
            'RdBu_r', 'seismic', 'coolwarm'
        ])
        self.colormap_combo.currentTextChanged.connect(self.update_visualization)
        display_layout.addWidget(self.colormap_combo)
        
        self.show_pattern_outline = QCheckBox("Show Pattern Outline")
        self.show_pattern_outline.setChecked(True)
        self.show_pattern_outline.toggled.connect(self.update_visualization)
        display_layout.addWidget(self.show_pattern_outline)
        
        self.show_contours = QCheckBox("Show Contours")
        self.show_contours.toggled.connect(self.update_visualization)
        display_layout.addWidget(self.show_contours)
        
        self.interpolate_check = QCheckBox("Interpolate")
        self.interpolate_check.setChecked(True)
        self.interpolate_check.toggled.connect(self.update_visualization)
        display_layout.addWidget(self.interpolate_check)
        
        display_layout.addStretch()
        vis_layout.addLayout(display_layout)
        
        # Threshold analysis
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Analysis Thresholds:"))
        
        threshold_layout.addWidget(QLabel("Pattern:"))
        self.pattern_threshold = QDoubleSpinBox()
        self.pattern_threshold.setRange(0, 50000)
        self.pattern_threshold.setValue(2500)
        self.pattern_threshold.setSuffix(" µC/cm²")
        self.pattern_threshold.valueChanged.connect(self.update_visualization)
        threshold_layout.addWidget(self.pattern_threshold)
        
        threshold_layout.addWidget(QLabel("Crosslink:"))
        self.crosslink_threshold = QDoubleSpinBox()
        self.crosslink_threshold.setRange(0, 10000)
        self.crosslink_threshold.setValue(500)
        self.crosslink_threshold.setSuffix(" µC/cm²")
        self.crosslink_threshold.valueChanged.connect(self.update_visualization)
        threshold_layout.addWidget(self.crosslink_threshold)
        
        threshold_layout.addStretch()
        vis_layout.addLayout(threshold_layout)
        
        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group)
        
        # Info panel
        self.info_label = QLabel("Load a dose file to begin")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)
        
        # Connect scale controls
        self.dose_min_spin.valueChanged.connect(self.update_visualization)
        self.dose_max_spin.valueChanged.connect(self.update_visualization)
        
    def load_dose_file(self):
        """Load and process dose file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Pattern Dose File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            # Load data
            self.dose_data = pd.read_csv(file_path, comment='#')
            self.file_label.setText(Path(file_path).name)
            
            # Analyze data structure
            self.analyze_data()
            
            # Update UI
            self.update_ui_from_data()
            
            # Initial visualization
            self.update_visualization()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
            
    def analyze_data(self):
        """Analyze dose data to find patterns and structure"""
        if self.dose_data is None:
            return
            
        # Get unique coordinates
        x_vals = np.sort(self.dose_data['X[nm]'].unique())
        y_vals = np.sort(self.dose_data['Y[nm]'].unique())
        z_vals = np.sort(self.dose_data['Z[nm]'].unique())
        
        # Detect grid spacing
        if len(x_vals) > 1:
            dx = np.median(np.diff(x_vals))
        else:
            dx = 1
            
        if len(y_vals) > 1:
            dy = np.median(np.diff(y_vals))
        else:
            dy = 1
            
        # Find dose statistics
        dose_vals = self.dose_data['Dose[uC/cm^2]']
        max_dose = dose_vals.max()
        
        # Detect pattern region (high dose area)
        high_dose_mask = dose_vals > max_dose * 0.5
        if high_dose_mask.any():
            pattern_data = self.dose_data[high_dose_mask]
            self.pattern_bounds = {
                'x_min': pattern_data['X[nm]'].min(),
                'x_max': pattern_data['X[nm]'].max(),
                'y_min': pattern_data['Y[nm]'].min(),
                'y_max': pattern_data['Y[nm]'].max()
            }
        else:
            self.pattern_bounds = None
            
        # Update info
        info_text = f"Grid: {len(x_vals)}×{len(y_vals)}×{len(z_vals)}\n"
        info_text += f"Spacing: {dx:.1f}×{dy:.1f} nm\n"
        info_text += f"Dose range: {dose_vals.min():.2e} - {dose_vals.max():.1f} µC/cm²\n"
        
        if self.pattern_bounds:
            pattern_width = self.pattern_bounds['x_max'] - self.pattern_bounds['x_min']
            pattern_height = self.pattern_bounds['y_max'] - self.pattern_bounds['y_min']
            info_text += f"Pattern size: {pattern_width:.0f}×{pattern_height:.0f} nm"
            
        self.info_label.setText(info_text)
        
    def update_ui_from_data(self):
        """Update UI controls based on data"""
        if self.dose_data is None:
            return
            
        # Update Z layer selector
        z_vals = np.sort(self.dose_data['Z[nm]'].unique())
        self.z_combo.clear()
        self.z_combo.addItems([f"{z:.1f} nm" for z in z_vals])
        
        # Set dose scale ranges
        dose_vals = self.dose_data['Dose[uC/cm^2]']
        self.dose_min_spin.setRange(0, dose_vals.max())
        self.dose_max_spin.setRange(0, dose_vals.max())
        
        # Set reasonable defaults based on data range
        max_dose = dose_vals.max()
        if self.log_radio.isChecked():
            # For log scale, set minimum to show full dynamic range
            if max_dose > 1000:
                self.dose_min_spin.setValue(max(0.1, max_dose * 1e-5))  # Show 5 orders of magnitude
            else:
                self.dose_min_spin.setValue(max(0.1, max_dose * 1e-4))  # Show 4 orders of magnitude
            self.dose_max_spin.setValue(max_dose)
        else:
            self.dose_min_spin.setValue(0)
            self.dose_max_spin.setValue(max_dose)
            
        # Update threshold defaults for high doses
        if max_dose > 1000:
            self.pattern_threshold.setValue(max_dose * 0.8)  # 80% of max dose
            self.crosslink_threshold.setValue(max_dose * 0.1)  # 10% of max dose
            
    def update_scale_controls(self):
        """Enable/disable scale controls based on mode"""
        custom_enabled = self.custom_radio.isChecked()
        self.dose_min_spin.setEnabled(custom_enabled)
        self.dose_max_spin.setEnabled(custom_enabled)
        self.update_visualization()
        
    def create_dose_grid(self, z_value=None, view_bounds=None):
        """Create interpolated dose grid for visualization"""
        if self.dose_data is None:
            return None, None, None
            
        # Filter by Z if specified
        if z_value is not None:
            data = self.dose_data[self.dose_data['Z[nm]'] == z_value].copy()
        else:
            # Sum over all Z
            data = self.dose_data.groupby(['X[nm]', 'Y[nm]'])['Dose[uC/cm^2]'].sum().reset_index()
            
        if len(data) == 0:
            return None, None, None
            
        # Apply view bounds if specified
        if view_bounds:
            mask = (
                (data['X[nm]'] >= view_bounds['x_min']) &
                (data['X[nm]'] <= view_bounds['x_max']) &
                (data['Y[nm]'] >= view_bounds['y_min']) &
                (data['Y[nm]'] <= view_bounds['y_max'])
            )
            data = data[mask]
            
        if len(data) == 0:
            return None, None, None
            
        # Create grid for interpolation
        x_range = data['X[nm]'].max() - data['X[nm]'].min()
        y_range = data['Y[nm]'].max() - data['Y[nm]'].min()
        
        # Adaptive resolution based on data range
        resolution = min(200, max(50, int(max(x_range, y_range) / 2)))
        
        xi = np.linspace(data['X[nm]'].min(), data['X[nm]'].max(), resolution)
        yi = np.linspace(data['Y[nm]'].min(), data['Y[nm]'].max(), resolution)
        Xi, Yi = np.meshgrid(xi, yi)
        
        # Interpolate if requested
        if self.interpolate_check.isChecked() and len(data) > 10:
            points = data[['X[nm]', 'Y[nm]']].values
            values = data['Dose[uC/cm^2]'].values
            Zi = griddata(points, values, (Xi, Yi), method='cubic', fill_value=0)
            
            # Apply slight smoothing to remove artifacts
            Zi = gaussian_filter(Zi, sigma=0.5)
        else:
            # Direct gridding without interpolation
            Zi = np.zeros_like(Xi)
            for _, row in data.iterrows():
                # Find nearest grid point
                ix = np.argmin(np.abs(xi - row['X[nm]']))
                iy = np.argmin(np.abs(yi - row['Y[nm]']))
                Zi[iy, ix] = row['Dose[uC/cm^2]']
                
        return Xi, Yi, Zi
        
    def update_visualization(self):
        """Update the visualization based on current settings"""
        if self.dose_data is None:
            return
            
        self.figure.clear()
        
        view_type = self.view_combo.currentText()
        
        # Get Z value
        z_text = self.z_combo.currentText()
        if z_text:
            z_value = float(z_text.replace(' nm', ''))
        else:
            z_value = None
            
        if view_type == "Line Cut Analysis":
            self.plot_line_cuts()
        else:
            self.plot_dose_map(view_type, z_value)
            
        self.canvas.draw()
        
    def plot_dose_map(self, view_type, z_value):
        """Plot 2D dose map with appropriate view"""
        ax = self.figure.add_subplot(111)
        
        # Determine view bounds
        view_bounds = None
        if view_type == "Pattern Region Only" and self.pattern_bounds:
            margin = 20  # nm margin around pattern
            view_bounds = {
                'x_min': self.pattern_bounds['x_min'] - margin,
                'x_max': self.pattern_bounds['x_max'] + margin,
                'y_min': self.pattern_bounds['y_min'] - margin,
                'y_max': self.pattern_bounds['y_max'] + margin
            }
        elif view_type == "Pattern + Proximity" and self.pattern_bounds:
            # Larger region to show proximity effects
            width = self.pattern_bounds['x_max'] - self.pattern_bounds['x_min']
            height = self.pattern_bounds['y_max'] - self.pattern_bounds['y_min']
            margin = max(width, height) * 2
            
            center_x = (self.pattern_bounds['x_min'] + self.pattern_bounds['x_max']) / 2
            center_y = (self.pattern_bounds['y_min'] + self.pattern_bounds['y_max']) / 2
            
            view_bounds = {
                'x_min': center_x - margin,
                'x_max': center_x + margin,
                'y_min': center_y - margin,
                'y_max': center_y + margin
            }
        elif view_type == "Backscatter Region":
            # Focus on low-dose regions
            pass  # Will handle with color scaling
            
        # Create dose grid
        X, Y, dose = self.create_dose_grid(z_value, view_bounds)
        
        if dose is None:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=14)
            return
            
        # Determine color scale
        if self.linear_radio.isChecked():
            norm = mcolors.Normalize(vmin=0, vmax=dose.max())
            dose_plot = dose
        elif self.log_radio.isChecked():
            # Adaptive log scale based on dose range
            max_dose = dose.max()
            if max_dose > 1000:
                vmin = max(max_dose * 1e-5, dose[dose > 0].min()) if (dose > 0).any() else 0.1
            else:
                vmin = max(max_dose * 1e-4, dose[dose > 0].min()) if (dose > 0).any() else 0.1
            vmax = max_dose
            norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
            dose_plot = np.maximum(dose, vmin)
        else:  # Custom
            vmin = self.dose_min_spin.value()
            vmax = self.dose_max_spin.value()
            if self.dose_min_spin.value() > 0:
                norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
                dose_plot = np.maximum(dose, vmin)
            else:
                norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
                dose_plot = dose
                
        # Special handling for backscatter view
        if view_type == "Backscatter Region":
            # Focus on low doses
            max_backscatter = dose.max() * 0.1
            norm = mcolors.Normalize(vmin=0, vmax=max_backscatter)
            dose_plot = np.minimum(dose, max_backscatter)
            
        # Create the plot
        im = ax.pcolormesh(X, Y, dose_plot, norm=norm, 
                          cmap=self.colormap_combo.currentText(), 
                          shading='auto')
        
        # Add colorbar
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label('Dose [µC/cm²]')
        
        # Add pattern outline if requested
        if self.show_pattern_outline.isChecked() and self.pattern_bounds:
            from matplotlib.patches import Rectangle
            rect = Rectangle(
                (self.pattern_bounds['x_min'], self.pattern_bounds['y_min']),
                self.pattern_bounds['x_max'] - self.pattern_bounds['x_min'],
                self.pattern_bounds['y_max'] - self.pattern_bounds['y_min'],
                fill=False, edgecolor='white', linewidth=2, linestyle='--'
            )
            ax.add_patch(rect)
            
        # Add contours if requested
        if self.show_contours.isChecked():
            # Key dose levels
            levels = []
            
            # Add pattern threshold
            if self.pattern_threshold.value() < dose.max():
                levels.append(self.pattern_threshold.value())
                
            # Add crosslink threshold
            if self.crosslink_threshold.value() < dose.max():
                levels.append(self.crosslink_threshold.value())
                
            # Add percentage levels
            for pct in [0.1, 0.5, 0.9]:
                level = dose.max() * pct
                if level not in levels:
                    levels.append(level)
                    
            if levels:
                contours = ax.contour(X, Y, dose, levels=sorted(levels),
                                    colors='white', alpha=0.5, linewidths=1)
                
                # Label the threshold contours
                fmt = {}
                for level in levels:
                    if level == self.pattern_threshold.value():
                        fmt[level] = 'Pattern'
                    elif level == self.crosslink_threshold.value():
                        fmt[level] = 'Crosslink'
                    else:
                        fmt[level] = f'{level:.0f}'
                        
                ax.clabel(contours, levels, inline=True, fmt=fmt, fontsize=8)
                
        # Labels and title
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_aspect('equal')
        
        title = f'Dose Distribution - {view_type}'
        if z_value is not None:
            title += f' at Z={z_value:.1f} nm'
        ax.set_title(title)
        
        # Add statistics box
        stats_text = f'Max: {dose.max():.1f} µC/cm²\n'
        
        # Calculate areas above thresholds
        if self.pattern_threshold.value() < dose.max():
            pattern_area = np.sum(dose > self.pattern_threshold.value()) * (X[0,1] - X[0,0]) * (Y[1,0] - Y[0,0])
            stats_text += f'Pattern area: {pattern_area:.0f} nm²\n'
            
        if self.crosslink_threshold.value() < dose.max():
            crosslink_area = np.sum(dose > self.crosslink_threshold.value()) * (X[0,1] - X[0,0]) * (Y[1,0] - Y[0,0])
            stats_text += f'Crosslink area: {crosslink_area:.0f} nm²'
            
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', bbox=dict(boxstyle='round', 
               facecolor='white', alpha=0.8), fontsize=9)
               
    def plot_line_cuts(self):
        """Plot line cuts through pattern center"""
        # Create subplots
        ax1 = self.figure.add_subplot(221)
        ax2 = self.figure.add_subplot(222)
        ax3 = self.figure.add_subplot(223)
        ax4 = self.figure.add_subplot(224)
        
        # Get current Z
        z_text = self.z_combo.currentText()
        if z_text:
            z_value = float(z_text.replace(' nm', ''))
            data = self.dose_data[self.dose_data['Z[nm]'] == z_value].copy()
        else:
            data = self.dose_data.groupby(['X[nm]', 'Y[nm]'])['Dose[uC/cm^2]'].sum().reset_index()
            
        if len(data) == 0:
            return
            
        # Find pattern center
        if self.pattern_bounds:
            center_x = (self.pattern_bounds['x_min'] + self.pattern_bounds['x_max']) / 2
            center_y = (self.pattern_bounds['y_min'] + self.pattern_bounds['y_max']) / 2
        else:
            # Use dose centroid
            weights = data['Dose[uC/cm^2]']
            center_x = np.average(data['X[nm]'], weights=weights)
            center_y = np.average(data['Y[nm]'], weights=weights)
            
        # X line cut (through Y center)
        tolerance = 5  # nm
        x_cut_data = data[np.abs(data['Y[nm]'] - center_y) < tolerance].sort_values('X[nm]')
        
        if len(x_cut_data) > 0:
            ax1.plot(x_cut_data['X[nm]'], x_cut_data['Dose[uC/cm^2]'], 'b-', linewidth=2)
            ax1.axhline(y=self.pattern_threshold.value(), color='red', linestyle='--', 
                       label=f'Pattern ({self.pattern_threshold.value():.0f})')
            ax1.axhline(y=self.crosslink_threshold.value(), color='orange', linestyle='--',
                       label=f'Crosslink ({self.crosslink_threshold.value():.0f})')
            ax1.set_xlabel('X [nm]')
            ax1.set_ylabel('Dose [µC/cm²]')
            ax1.set_title(f'X Profile at Y={center_y:.0f} nm')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Log scale version
            ax2.plot(x_cut_data['X[nm]'], x_cut_data['Dose[uC/cm^2]'], 'b-', linewidth=2)
            ax2.set_yscale('log')
            max_dose = x_cut_data['Dose[uC/cm^2]'].max()
            if max_dose > 1000:
                ax2.set_ylim(bottom=max(0.1, max_dose * 1e-5))
            else:
                ax2.set_ylim(bottom=max(0.1, max_dose * 1e-4))
            ax2.axhline(y=self.pattern_threshold.value(), color='red', linestyle='--')
            ax2.axhline(y=self.crosslink_threshold.value(), color='orange', linestyle='--')
            ax2.set_xlabel('X [nm]')
            ax2.set_ylabel('Dose [µC/cm²]')
            ax2.set_title('X Profile (Log Scale)')
            ax2.grid(True, alpha=0.3)
            
        # Y line cut (through X center)
        y_cut_data = data[np.abs(data['X[nm]'] - center_x) < tolerance].sort_values('Y[nm]')
        
        if len(y_cut_data) > 0:
            ax3.plot(y_cut_data['Y[nm]'], y_cut_data['Dose[uC/cm^2]'], 'r-', linewidth=2)
            ax3.axhline(y=self.pattern_threshold.value(), color='red', linestyle='--',
                       label=f'Pattern ({self.pattern_threshold.value():.0f})')
            ax3.axhline(y=self.crosslink_threshold.value(), color='orange', linestyle='--',
                       label=f'Crosslink ({self.crosslink_threshold.value():.0f})')
            ax3.set_xlabel('Y [nm]')
            ax3.set_ylabel('Dose [µC/cm²]')
            ax3.set_title(f'Y Profile at X={center_x:.0f} nm')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # Log scale version
            ax4.plot(y_cut_data['Y[nm]'], y_cut_data['Dose[uC/cm^2]'], 'r-', linewidth=2)
            ax4.set_yscale('log')
            max_dose = y_cut_data['Dose[uC/cm^2]'].max()
            if max_dose > 1000:
                ax4.set_ylim(bottom=max(0.1, max_dose * 1e-5))
            else:
                ax4.set_ylim(bottom=max(0.1, max_dose * 1e-4))
            ax4.axhline(y=self.pattern_threshold.value(), color='red', linestyle='--')
            ax4.axhline(y=self.crosslink_threshold.value(), color='orange', linestyle='--')
            ax4.set_xlabel('Y [nm]')
            ax4.set_ylabel('Dose [µC/cm²]')
            ax4.set_title('Y Profile (Log Scale)')
            ax4.grid(True, alpha=0.3)
            
        self.figure.tight_layout()