"""
Improved Pattern Dose Heatmap Widget
Top-down view with proper centering and scale visualization
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QComboBox, QSpinBox, QCheckBox,
                              QGroupBox, QFileDialog, QMessageBox, QSlider,
                              QDoubleSpinBox, QRadioButton, QButtonGroup,
                              QFrame)
from PySide6.QtCore import Qt, Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle, Circle
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter


class PatternHeatmapWidget(QWidget):
    """Improved top-down heatmap visualization for pattern dose distribution"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dose_data = None
        self.pattern_info = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup UI with streamlined controls for better visualization"""
        layout = QVBoxLayout(self)
        
        # File controls
        file_group = QGroupBox("Data File")
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel("No pattern dose file loaded")
        self.load_button = QPushButton("Load Pattern Dose File")
        self.load_button.clicked.connect(self.load_dose_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.load_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # View controls
        view_group = QGroupBox("View Settings")
        view_layout = QVBoxLayout()
        
        # Top row - main controls
        main_controls = QHBoxLayout()
        
        main_controls.addWidget(QLabel("View Mode:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems([
            "Full Field (Top-Down)",
            "Pattern Centered", 
            "Pattern + Proximity Zone",
            "Backscatter Overview"
        ])
        self.view_mode_combo.currentTextChanged.connect(self.update_view)
        main_controls.addWidget(self.view_mode_combo)
        
        main_controls.addWidget(QLabel("Z Layer:"))
        self.z_layer_combo = QComboBox()
        self.z_layer_combo.currentTextChanged.connect(self.update_view)
        main_controls.addWidget(self.z_layer_combo)
        
        main_controls.addWidget(QLabel("Resolution:"))
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(50, 500)
        self.resolution_spin.setValue(200)
        self.resolution_spin.setSuffix(" pts")
        self.resolution_spin.valueChanged.connect(self.update_view)
        main_controls.addWidget(self.resolution_spin)
        
        main_controls.addStretch()
        view_layout.addLayout(main_controls)
        
        # Second row - scale and display options
        display_controls = QHBoxLayout()
        
        display_controls.addWidget(QLabel("Color Scale:"))
        self.scale_mode = QButtonGroup()
        
        self.auto_radio = QRadioButton("Auto")
        self.auto_radio.setChecked(True)
        self.scale_mode.addButton(self.auto_radio, 0)
        display_controls.addWidget(self.auto_radio)
        
        self.log_radio = QRadioButton("Log")
        self.scale_mode.addButton(self.log_radio, 1)
        display_controls.addWidget(self.log_radio)
        
        self.manual_radio = QRadioButton("Manual")
        self.scale_mode.addButton(self.manual_radio, 2)
        display_controls.addWidget(self.manual_radio)
        
        # Manual scale controls
        self.min_dose_spin = QDoubleSpinBox()
        self.min_dose_spin.setRange(0.01, 100000)
        self.min_dose_spin.setValue(1.0)
        self.min_dose_spin.setSuffix(" µC/cm²")
        self.min_dose_spin.setEnabled(False)
        display_controls.addWidget(QLabel("Min:"))
        display_controls.addWidget(self.min_dose_spin)
        
        self.max_dose_spin = QDoubleSpinBox()
        self.max_dose_spin.setRange(1, 100000)
        self.max_dose_spin.setValue(5000)
        self.max_dose_spin.setSuffix(" µC/cm²")
        self.max_dose_spin.setEnabled(False)
        display_controls.addWidget(QLabel("Max:"))
        display_controls.addWidget(self.max_dose_spin)
        
        self.scale_mode.buttonClicked.connect(self.on_scale_mode_changed)
        
        display_controls.addStretch()
        view_layout.addLayout(display_controls)
        
        # Third row - overlay options
        overlay_controls = QHBoxLayout()
        
        overlay_controls.addWidget(QLabel("Overlays:"))
        
        self.show_pattern_outline = QCheckBox("Pattern Outline")
        self.show_pattern_outline.setChecked(True)
        self.show_pattern_outline.toggled.connect(self.update_view)
        overlay_controls.addWidget(self.show_pattern_outline)
        
        self.show_grid = QCheckBox("Grid")
        self.show_grid.toggled.connect(self.update_view)
        overlay_controls.addWidget(self.show_grid)
        
        self.show_contours = QCheckBox("Dose Contours")
        self.show_contours.toggled.connect(self.update_view)
        overlay_controls.addWidget(self.show_contours)
        
        self.show_scale_bar = QCheckBox("Scale Bar")
        self.show_scale_bar.setChecked(True)
        self.show_scale_bar.toggled.connect(self.update_view)
        overlay_controls.addWidget(self.show_scale_bar)
        
        overlay_controls.addWidget(QLabel("Colormap:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            'hot', 'viridis', 'plasma', 'inferno', 'turbo',
            'jet', 'coolwarm', 'RdBu_r', 'seismic'
        ])
        self.colormap_combo.currentTextChanged.connect(self.update_view)
        overlay_controls.addWidget(self.colormap_combo)
        
        overlay_controls.addStretch()
        view_layout.addLayout(overlay_controls)
        
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)
        
        # Info panel
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QHBoxLayout(info_frame)
        
        self.info_label = QLabel("Load a pattern dose file to begin visualization")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(info_frame)
        
        # Main visualization
        self.figure = Figure(figsize=(12, 10), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)
        
        # Connect scale controls
        self.min_dose_spin.valueChanged.connect(self.update_view)
        self.max_dose_spin.valueChanged.connect(self.update_view)
        
    def load_dose_file(self):
        """Load pattern dose file"""
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
            
            # Extract pattern information from filename or data
            self.extract_pattern_info(file_path)
            
            # Update UI
            self.update_z_layers()
            self.update_info_display()
            self.update_view()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\\n{str(e)}")
            
    def extract_pattern_info(self, file_path):
        """Extract pattern information from data and filename"""
        if self.dose_data is None:
            return
            
        # Get dose statistics
        dose_vals = self.dose_data['Dose[uC/cm^2]']
        
        # Detect pattern region (high dose area)
        dose_threshold = dose_vals.max() * 0.3  # 30% of max dose
        pattern_mask = dose_vals > dose_threshold
        
        if pattern_mask.any():
            pattern_data = self.dose_data[pattern_mask]
            
            # Calculate pattern bounds
            x_min, x_max = pattern_data['X[nm]'].min(), pattern_data['X[nm]'].max()
            y_min, y_max = pattern_data['Y[nm]'].min(), pattern_data['Y[nm]'].max()
            
            # Pattern center and size
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2
            width = x_max - x_min
            height = y_max - y_min
            
            self.pattern_info = {
                'bounds': {'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max},
                'center': {'x': center_x, 'y': center_y},
                'size': {'width': width, 'height': height},
                'max_dose': dose_vals.max(),
                'dose_range': dose_vals.max() - dose_vals.min(),
                'pattern_area': width * height
            }
        else:
            self.pattern_info = None
            
    def update_z_layers(self):
        """Update Z layer selector"""
        if self.dose_data is None:
            return
            
        z_values = sorted(self.dose_data['Z[nm]'].unique())
        self.z_layer_combo.clear()
        
        # Add integrated option and individual layers
        self.z_layer_combo.addItem("Integrated (All Z)")
        for z in z_values:
            self.z_layer_combo.addItem(f"Z = {z:.1f} nm")
            
    def update_info_display(self):
        """Update information display"""
        if self.dose_data is None or self.pattern_info is None:
            return
            
        info = self.pattern_info
        info_text = f"Pattern: {info['size']['width']:.0f}×{info['size']['height']:.0f} nm"
        info_text += f" | Center: ({info['center']['x']:.0f}, {info['center']['y']:.0f}) nm"
        info_text += f" | Max Dose: {info['max_dose']:.0f} µC/cm²"
        info_text += f" | Grid: {len(self.dose_data['X[nm]'].unique())}×{len(self.dose_data['Y[nm]'].unique())}"
        
        self.info_label.setText(info_text)
        
    def on_scale_mode_changed(self):
        """Handle scale mode changes"""
        manual_mode = self.manual_radio.isChecked()
        self.min_dose_spin.setEnabled(manual_mode)
        self.max_dose_spin.setEnabled(manual_mode)
        
        if not manual_mode and self.dose_data is not None:
            # Auto-set ranges based on data
            dose_vals = self.dose_data['Dose[uC/cm^2]']
            self.min_dose_spin.setValue(max(0.01, dose_vals.min()))
            self.max_dose_spin.setValue(dose_vals.max())
            
        self.update_view()
        
    def create_dose_grid(self):
        """Create interpolated dose grid for visualization"""
        if self.dose_data is None:
            return None, None, None
            
        # Get Z layer selection
        z_text = self.z_layer_combo.currentText()
        if z_text == "Integrated (All Z)" or not z_text:
            # Sum over all Z layers
            data = self.dose_data.groupby(['X[nm]', 'Y[nm]'])['Dose[uC/cm^2]'].sum().reset_index()
        else:
            # Extract Z value and filter
            z_value = float(z_text.split('=')[1].replace(' nm', ''))
            data = self.dose_data[self.dose_data['Z[nm]'] == z_value].copy()
            
        if len(data) == 0:
            return None, None, None
            
        # Determine grid bounds based on view mode
        view_mode = self.view_mode_combo.currentText()
        
        if view_mode == "Pattern Centered" and self.pattern_info:
            # Center on pattern with some margin
            center = self.pattern_info['center']
            size = max(self.pattern_info['size']['width'], self.pattern_info['size']['height'])
            margin = size * 0.6  # 60% margin around pattern
            
            x_min = center['x'] - size/2 - margin
            x_max = center['x'] + size/2 + margin
            y_min = center['y'] - size/2 - margin
            y_max = center['y'] + size/2 + margin
            
        elif view_mode == "Pattern + Proximity Zone" and self.pattern_info:
            # Larger area to show proximity effects
            center = self.pattern_info['center']
            size = max(self.pattern_info['size']['width'], self.pattern_info['size']['height'])
            margin = size * 2.0  # 2x pattern size margin for proximity
            
            x_min = center['x'] - size/2 - margin
            x_max = center['x'] + size/2 + margin
            y_min = center['y'] - size/2 - margin
            y_max = center['y'] + size/2 + margin
            
        else:  # Full field or backscatter overview
            # Use full data range with small margin
            x_range = data['X[nm]'].max() - data['X[nm]'].min()
            y_range = data['Y[nm]'].max() - data['Y[nm]'].min()
            margin = max(x_range, y_range) * 0.05  # 5% margin
            
            x_min = data['X[nm]'].min() - margin
            x_max = data['X[nm]'].max() + margin
            y_min = data['Y[nm]'].min() - margin
            y_max = data['Y[nm]'].max() + margin
            
        # Filter data to bounds
        mask = (
            (data['X[nm]'] >= x_min) & (data['X[nm]'] <= x_max) &
            (data['Y[nm]'] >= y_min) & (data['Y[nm]'] <= y_max)
        )
        data = data[mask]
        
        if len(data) == 0:
            return None, None, None
            
        # Create regular grid
        resolution = self.resolution_spin.value()
        xi = np.linspace(x_min, x_max, resolution)
        yi = np.linspace(y_min, y_max, resolution)
        Xi, Yi = np.meshgrid(xi, yi)
        
        # Interpolate dose values
        points = data[['X[nm]', 'Y[nm]']].values
        values = data['Dose[uC/cm^2]'].values
        
        # Use griddata for smooth interpolation
        Zi = griddata(points, values, (Xi, Yi), method='cubic', fill_value=0)
        
        # Apply slight smoothing to reduce interpolation artifacts
        Zi = gaussian_filter(Zi, sigma=0.8)
        
        # Ensure non-negative values
        Zi = np.maximum(Zi, 0)
        
        return Xi, Yi, Zi
        
    def update_view(self):
        """Update the main visualization"""
        if self.dose_data is None:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Load a pattern dose file to begin', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            self.canvas.draw()
            return
            
        # Create dose grid
        X, Y, dose = self.create_dose_grid()
        
        if dose is None:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data in selected view', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            self.canvas.draw()
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Determine color scaling
        if self.auto_radio.isChecked():
            if self.view_mode_combo.currentText() == "Backscatter Overview":
                # Focus on low doses for backscatter
                vmax = dose.max() * 0.2  # Show up to 20% of max dose
                vmin = dose[dose > 0].min() if (dose > 0).any() else 0.01
                norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
                dose_plot = np.minimum(dose, vmax)
            else:
                vmin = dose[dose > 0].min() if (dose > 0).any() else 0.01
                vmax = dose.max()
                norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
                dose_plot = dose
                
        elif self.log_radio.isChecked():
            vmin = max(0.01, dose[dose > 0].min()) if (dose > 0).any() else 0.01
            vmax = dose.max()
            norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
            dose_plot = np.maximum(dose, vmin)
            
        else:  # Manual
            vmin = self.min_dose_spin.value()
            vmax = self.max_dose_spin.value()
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            dose_plot = np.clip(dose, vmin, vmax)
            
        # Create the heatmap
        colormap = self.colormap_combo.currentText()
        im = ax.pcolormesh(X, Y, dose_plot, norm=norm, cmap=colormap, shading='auto')
        
        # Add colorbar
        cbar = self.figure.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Dose [µC/cm²]', fontsize=12)
        
        # Add pattern outline if requested and available
        if self.show_pattern_outline.isChecked() and self.pattern_info:
            bounds = self.pattern_info['bounds']
            rect = Rectangle(
                (bounds['x_min'], bounds['y_min']),
                bounds['x_max'] - bounds['x_min'],
                bounds['y_max'] - bounds['y_min'],
                fill=False, edgecolor='white', linewidth=2, linestyle='--'
            )
            ax.add_patch(rect)
            
            # Add center marker
            center = self.pattern_info['center']
            ax.plot(center['x'], center['y'], 'w+', markersize=10, markeredgewidth=2)
            
        # Add dose contours if requested
        if self.show_contours.isChecked():
            levels = []
            max_dose = dose.max()
            
            # Add decade levels for log scale
            if self.log_radio.isChecked():
                decade = 1
                while decade < max_dose:
                    if decade >= vmin:
                        levels.append(decade)
                    decade *= 10
            else:
                # Add percentage levels
                for pct in [0.1, 0.25, 0.5, 0.75, 0.9]:
                    level = max_dose * pct
                    if vmin <= level <= vmax:
                        levels.append(level)
                        
            if levels:
                contours = ax.contour(X, Y, dose, levels=levels, colors='white', 
                                    alpha=0.6, linewidths=1)
                ax.clabel(contours, inline=True, fontsize=8, fmt='%.0f')
                
        # Add grid if requested
        if self.show_grid.isChecked():
            ax.grid(True, alpha=0.3, color='white', linestyle=':')
            
        # Add scale bar if requested
        if self.show_scale_bar.isChecked():
            x_range = X.max() - X.min()
            scale_length = 10 ** (np.floor(np.log10(x_range * 0.2)))  # 20% of view width
            
            # Position scale bar in bottom-right
            scale_x = X.max() - x_range * 0.15
            scale_y = Y.min() + (Y.max() - Y.min()) * 0.1
            
            ax.plot([scale_x - scale_length, scale_x], [scale_y, scale_y], 
                   'w-', linewidth=3)
            ax.text(scale_x - scale_length/2, scale_y + (Y.max() - Y.min()) * 0.03,
                   f'{scale_length:.0f} nm', ha='center', va='bottom', 
                   color='white', fontweight='bold')
                   
        # Set labels and title
        ax.set_xlabel('X [nm]', fontsize=12)
        ax.set_ylabel('Y [nm]', fontsize=12)
        ax.set_aspect('equal')
        
        # Create title with key information
        title = f"Pattern Dose Distribution - {self.view_mode_combo.currentText()}"
        if self.pattern_info:
            title += f" | Max: {dose.max():.0f} µC/cm²"
        ax.set_title(title, fontsize=14, pad=20)
        
        # Add view info in corner
        view_info = f"Resolution: {self.resolution_spin.value()}×{self.resolution_spin.value()}"
        if self.z_layer_combo.currentText() != "Integrated (All Z)":
            view_info += f"\\n{self.z_layer_combo.currentText()}"
            
        ax.text(0.02, 0.98, view_info, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', bbox=dict(boxstyle='round', 
               facecolor='black', alpha=0.7), color='white')
               
        self.canvas.draw()