"""
Visualization widget for PSF data
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFileDialog, QGroupBox,
    QGridLayout, QCheckBox, QSpinBox, QDoubleSpinBox,
    QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from pathlib import Path

class PlotCanvas(FigureCanvas):
    """Custom matplotlib canvas"""
    
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(10, 6), dpi=100)
        super().__init__(self.figure)
        self.setParent(parent)
        
        # Dark theme for matplotlib
        self.figure.patch.set_facecolor('#2b2b2b')
        self.ax = None
        
    def clear_plot(self):
        """Clear the current plot"""
        self.figure.clear()
        self.ax = None
        self.draw()
        
    def create_plot(self, plot_type='linear'):
        """Create a new plot with specified type"""
        self.clear_plot()
        self.ax = self.figure.add_subplot(111)
        
        # Dark theme styling
        self.ax.set_facecolor('#1e1e1e')
        self.ax.spines['bottom'].set_color('#cccccc')
        self.ax.spines['top'].set_color('#cccccc')
        self.ax.spines['left'].set_color('#cccccc')
        self.ax.spines['right'].set_color('#cccccc')
        self.ax.tick_params(colors='#cccccc')
        self.ax.xaxis.label.set_color('#cccccc')
        self.ax.yaxis.label.set_color('#cccccc')
        self.ax.title.set_color('#cccccc')
        
        return self.ax

class PlotWidget(QWidget):
    """Widget for data visualization"""
    
    data_loaded = Signal(str)  # Emitted when data is loaded
    
    def __init__(self):
        super().__init__()
        self.current_data = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Create splitter for plot and controls
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Plot area
        plot_widget = QWidget()
        plot_layout = QVBoxLayout()
        
        # Plot canvas
        self.canvas = PlotCanvas()
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_widget.setLayout(plot_layout)
        
        # Right side - Controls
        control_widget = QWidget()
        control_widget.setMaximumWidth(300)
        control_layout = QVBoxLayout()
        
        # Data loading group
        data_group = QGroupBox("Data")
        data_layout = QVBoxLayout()
        
        self.load_btn = QPushButton("Load PSF Data")
        self.load_btn.clicked.connect(self.load_data_dialog)
        data_layout.addWidget(self.load_btn)
        
        self.file_label = QLabel("No data loaded")
        self.file_label.setWordWrap(True)
        data_layout.addWidget(self.file_label)
        
        data_group.setLayout(data_layout)
        
        # Plot controls group
        plot_group = QGroupBox("Plot Settings")
        plot_layout_controls = QGridLayout()
        
        # Plot type
        plot_layout_controls.addWidget(QLabel("Plot Type:"), 0, 0)
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Linear", "Log-Log", "Semi-Log X", "Semi-Log Y"])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot)
        plot_layout_controls.addWidget(self.plot_type_combo, 0, 1)
        
        # Grid
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.update_plot)
        plot_layout_controls.addWidget(self.grid_check, 1, 0, 1, 2)
        
        # Minor grid
        self.minor_grid_check = QCheckBox("Show Minor Grid")
        self.minor_grid_check.toggled.connect(self.update_plot)
        plot_layout_controls.addWidget(self.minor_grid_check, 2, 0, 1, 2)
        
        # Legend
        self.legend_check = QCheckBox("Show Legend")
        self.legend_check.setChecked(True)
        self.legend_check.toggled.connect(self.update_plot)
        plot_layout_controls.addWidget(self.legend_check, 3, 0, 1, 2)
        
        plot_group.setLayout(plot_layout_controls)
        
        # Analysis group
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QVBoxLayout()
        
        self.normalize_check = QCheckBox("Normalize PSF")
        self.normalize_check.toggled.connect(self.update_plot)
        analysis_layout.addWidget(self.normalize_check)
        
        self.cumulative_check = QCheckBox("Show Cumulative")
        self.cumulative_check.toggled.connect(self.update_plot)
        analysis_layout.addWidget(self.cumulative_check)
        
        # Statistics display
        self.stats_label = QLabel("Statistics:\n--")
        self.stats_label.setStyleSheet("QLabel { background-color: #3c3c3c; padding: 10px; }")
        analysis_layout.addWidget(self.stats_label)
        
        analysis_group.setLayout(analysis_layout)
        
        # Export group
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout()
        
        self.export_plot_btn = QPushButton("Export Plot")
        self.export_plot_btn.clicked.connect(self.export_plot)
        export_layout.addWidget(self.export_plot_btn)
        
        self.export_data_btn = QPushButton("Export Processed Data")
        self.export_data_btn.clicked.connect(self.export_data)
        export_layout.addWidget(self.export_data_btn)
        
        export_group.setLayout(export_layout)
        
        # Add all control groups
        control_layout.addWidget(data_group)
        control_layout.addWidget(plot_group)
        control_layout.addWidget(analysis_group)
        control_layout.addWidget(export_group)
        control_layout.addStretch()
        
        control_widget.setLayout(control_layout)
        
        # Add to splitter
        splitter.addWidget(plot_widget)
        splitter.addWidget(control_widget)
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def load_data_dialog(self):
        """Open file dialog to load data"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data",
            "", "CSV files (*.csv);;DAT files (*.dat);;All files (*.*)"
        )
        
        if file_path:
            self.load_data(file_path)
    
    def load_data(self, file_path):
        """Load PSF data from file"""
        try:
            # Load data
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                # Assume space/tab delimited
                df = pd.read_csv(file_path, sep=r'\s+', header=None)
            
            # Store data
            self.current_data = df
            self.file_label.setText(f"Loaded: {Path(file_path).name}")
            
            # Initial plot
            self.update_plot()
            
            # Update statistics
            self.update_statistics()
            
            # Emit signal
            self.data_loaded.emit(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")
    
    def update_plot(self):
        """Update the plot with current settings"""
        if self.current_data is None:
            return
        
        # Get data
        df = self.current_data
        
        # Assume first two columns are radius and energy
        if len(df.columns) >= 2:
            radius = df.iloc[:, 0].values
            energy = df.iloc[:, 1].values
        else:
            QMessageBox.warning(self, "Warning", "Data must have at least 2 columns")
            return
        
        # Process data based on settings
        if self.normalize_check.isChecked():
            # Normalize PSF
            from scipy.integrate import simpson
            if len(radius) > 1:
                area = simpson(energy * 2 * np.pi * radius, radius)
                if area > 0:
                    energy = energy / area
        
        # Create plot
        plot_type = self.plot_type_combo.currentText()
        ax = self.canvas.create_plot(plot_type)
        
        # Main plot
        if plot_type == "Linear":
            ax.plot(radius, energy, 'b-', linewidth=2, label='PSF')
        elif plot_type == "Log-Log":
            # Filter positive values
            mask = (radius > 0) & (energy > 0)
            if np.any(mask):
                ax.loglog(radius[mask], energy[mask], 'b-', linewidth=2, label='PSF')
        elif plot_type == "Semi-Log X":
            mask = radius > 0
            if np.any(mask):
                ax.semilogx(radius[mask], energy, 'b-', linewidth=2, label='PSF')
        elif plot_type == "Semi-Log Y":
            mask = energy > 0
            if np.any(mask):
                ax.semilogy(radius, energy[mask], 'b-', linewidth=2, label='PSF')
        
        # Cumulative plot
        if self.cumulative_check.isChecked() and len(radius) > 1:
            from scipy.integrate import cumtrapz
            cumulative = cumtrapz(energy * 2 * np.pi * radius, radius, initial=0)
            if np.max(cumulative) > 0:
                cumulative = cumulative / np.max(cumulative)
            
            ax2 = ax.twinx()
            ax2.plot(radius, cumulative, 'r--', linewidth=2, label='Cumulative')
            ax2.set_ylabel('Cumulative Fraction', color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            ax2.set_ylim(0, 1.1)
        
        # Labels and formatting
        ax.set_xlabel('Radius (nm)')
        ylabel = 'Normalized PSF' if self.normalize_check.isChecked() else 'Energy Deposition (eV/nm²)'
        ax.set_ylabel(ylabel)
        ax.set_title('Point Spread Function')
        
        # Grid
        if self.grid_check.isChecked():
            ax.grid(True, alpha=0.3)
        if self.minor_grid_check.isChecked():
            ax.grid(True, which='minor', alpha=0.1)
        
        # Legend
        if self.legend_check.isChecked():
            ax.legend()
        
        # Refresh canvas
        self.canvas.figure.tight_layout()
        self.canvas.draw()
    
    def update_statistics(self):
        """Update statistics display"""
        if self.current_data is None:
            return
        
        df = self.current_data
        radius = df.iloc[:, 0].values
        energy = df.iloc[:, 1].values
        
        # Calculate statistics
        stats_text = "Statistics:\n"
        stats_text += f"Points: {len(radius)}\n"
        stats_text += f"R range: {radius.min():.2f} - {radius.max():.0f} nm\n"
        
        # Find characteristic radii
        max_idx = np.argmax(energy)
        half_max = energy[max_idx] / 2
        
        # Find FWHM
        left_indices = np.where(energy[:max_idx] <= half_max)[0]
        right_indices = np.where(energy[max_idx:] <= half_max)[0]
        
        if len(left_indices) > 0 and len(right_indices) > 0:
            fwhm = radius[max_idx + right_indices[0]] - radius[left_indices[-1]]
            stats_text += f"FWHM: {fwhm:.2f} nm\n"
        
        # Energy containment radii
        if len(radius) > 1:
            from scipy.integrate import cumtrapz
            cumulative = cumtrapz(energy * 2 * np.pi * radius, radius, initial=0)
            if cumulative[-1] > 0:
                cumulative = cumulative / cumulative[-1]
                
                for fraction in [0.5, 0.9, 0.99]:
                    idx = np.argmax(cumulative >= fraction)
                    if idx > 0:
                        stats_text += f"R({fraction*100:.0f}%): {radius[idx]:.1f} nm\n"
        
        self.stats_label.setText(stats_text)
    
    def export_plot(self):
        """Export current plot"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot",
            "psf_plot.png",
            "PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg)"
        )
        
        if file_path:
            try:
                self.canvas.figure.savefig(file_path, dpi=300, bbox_inches='tight',
                                         facecolor=self.canvas.figure.get_facecolor())
                QMessageBox.information(self, "Success", f"Plot saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot:\n{str(e)}")
    
    def export_data(self):
        """Export processed data"""
        if self.current_data is None:
            QMessageBox.warning(self, "Warning", "No data to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data",
            "processed_psf_data.csv",
            "CSV files (*.csv);;All files (*.*)"
        )
        
        if file_path:
            try:
                self.current_data.to_csv(file_path, index=False)
                QMessageBox.information(self, "Success", f"Data saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save data:\n{str(e)}")