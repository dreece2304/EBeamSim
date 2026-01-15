"""
PSF Analysis Interface - Specialized for Point Spread Function Analysis
=====================================================================

Dedicated interface for PSF characterization, BEAMER integration, and 
resist optimization studies.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QTabWidget,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QScrollArea, QFrame, QProgressBar, QCheckBox, QSlider
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QPixmap, QPalette

# Add path for modern components
sys.path.append(str(Path(__file__).parent.parent / "widgets" / "modern"))
from modern_components import (
    MaterialCard, ModernButton, ModernInput, ModernSlider, 
    ModernProgressBar, ModernTabWidget, ModernMetricCard, create_metric_dashboard
)

# Matplotlib for scientific visualization
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.colors import LogNorm


class PSFVisualizationWidget(QWidget):
    """Advanced PSF visualization with multiple view modes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_matplotlib()
    
    def setup_ui(self):
        """Setup the PSF visualization interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Controls section
        controls = self.create_controls_section()
        layout.addWidget(controls)
        
        # Visualization area
        self.fig = Figure(figsize=(12, 8), dpi=100, facecolor='#1f2937')
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: #1f2937; border-radius: 8px;")
        
        layout.addWidget(self.canvas, 1)
    
    def create_controls_section(self) -> QWidget:
        """Create PSF visualization controls"""
        controls = MaterialCard("PSF Visualization Controls")
        controls_layout = QHBoxLayout()
        
        # View mode selection
        view_group = QGroupBox("View Mode")
        view_layout = QHBoxLayout(view_group)
        
        self.radial_btn = ModernButton("Radial Profile", "secondary")
        self.log_btn = ModernButton("Log Scale", "secondary") 
        self.comparison_btn = ModernButton("Compare PSFs", "secondary")
        self.beamer_btn = ModernButton("BEAMER Export", "primary")
        
        view_layout.addWidget(self.radial_btn)
        view_layout.addWidget(self.log_btn)
        view_layout.addWidget(self.comparison_btn)
        view_layout.addWidget(self.beamer_btn)
        
        # Analysis options
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QHBoxLayout(analysis_group)
        
        self.alpha_beta_btn = ModernButton("α/β Analysis", "ghost")
        self.fwhm_btn = ModernButton("FWHM Analysis", "ghost")
        self.proximity_btn = ModernButton("Proximity Effects", "ghost")
        
        analysis_layout.addWidget(self.alpha_beta_btn)
        analysis_layout.addWidget(self.fwhm_btn)
        analysis_layout.addWidget(self.proximity_btn)
        
        controls_layout.addWidget(view_group)
        controls_layout.addWidget(analysis_group)
        controls_layout.addStretch()
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls.layout().addWidget(controls_widget)
        
        return controls
    
    def setup_matplotlib(self):
        """Setup matplotlib styling for PSF plots"""
        plt.style.use('dark_background')
        
        # Configure matplotlib for dark theme
        self.fig.patch.set_facecolor('#1f2937')
        
        # Create subplots for different views
        self.ax_radial = self.fig.add_subplot(221)
        self.ax_2d = self.fig.add_subplot(222)
        self.ax_log = self.fig.add_subplot(223)
        self.ax_metrics = self.fig.add_subplot(224)
        
        # Style all axes
        for ax in [self.ax_radial, self.ax_2d, self.ax_log, self.ax_metrics]:
            ax.set_facecolor('#374151')
            ax.tick_params(colors='#d1d5db')
            ax.xaxis.label.set_color('#f9fafb')
            ax.yaxis.label.set_color('#f9fafb')
            ax.title.set_color('#f9fafb')
        
        self.fig.tight_layout(pad=3.0)


class PSFParametersWidget(QWidget):
    """PSF simulation parameters optimized for resist characterization"""
    
    parameters_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup PSF parameters interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Beam parameters card
        beam_card = MaterialCard("Beam Parameters")
        beam_layout = QGridLayout()
        
        # Energy
        beam_layout.addWidget(QLabel("Energy (keV):"), 0, 0)
        self.energy_spin = QDoubleSpinBox()
        self.energy_spin.setRange(1.0, 300.0)
        self.energy_spin.setValue(30.0)
        self.energy_spin.setSuffix(" keV")
        beam_layout.addWidget(self.energy_spin, 0, 1)
        
        # Beam size
        beam_layout.addWidget(QLabel("Beam Size (nm):"), 1, 0)
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.1, 50.0)
        self.beam_size_spin.setValue(1.0)
        self.beam_size_spin.setSuffix(" nm")
        beam_layout.addWidget(self.beam_size_spin, 1, 1)
        
        # Current
        beam_layout.addWidget(QLabel("Current (pA):"), 2, 0)
        self.current_spin = QDoubleSpinBox()
        self.current_spin.setRange(0.1, 1000.0)
        self.current_spin.setValue(10.0)
        self.current_spin.setSuffix(" pA")
        beam_layout.addWidget(self.current_spin, 2, 1)
        
        beam_widget = QWidget()
        beam_widget.setLayout(beam_layout)
        beam_card.layout().addWidget(beam_widget)
        
        # Resist parameters card  
        resist_card = MaterialCard("Resist Parameters")
        resist_layout = QGridLayout()
        
        # Material selection
        resist_layout.addWidget(QLabel("Material:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems([
            "PMMA", "HSQ", "ZEP", "Alucone_XPS", "Alucone_Exposed", "Custom"
        ])
        self.material_combo.setCurrentText("Alucone_XPS")
        resist_layout.addWidget(self.material_combo, 0, 1)
        
        # Thickness
        resist_layout.addWidget(QLabel("Thickness (nm):"), 1, 0)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 1000.0)
        self.thickness_spin.setValue(30.0)
        self.thickness_spin.setSuffix(" nm")
        resist_layout.addWidget(self.thickness_spin, 1, 1)
        
        # Density
        resist_layout.addWidget(QLabel("Density (g/cm³):"), 2, 0)
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 5.0)
        self.density_spin.setValue(1.35)
        self.density_spin.setSuffix(" g/cm³")
        resist_layout.addWidget(self.density_spin, 2, 1)
        
        resist_widget = QWidget()
        resist_widget.setLayout(resist_layout)
        resist_card.layout().addWidget(resist_widget)
        
        # Simulation parameters card
        sim_card = MaterialCard("Simulation Parameters")
        sim_layout = QGridLayout()
        
        # Number of events
        sim_layout.addWidget(QLabel("Events:"), 0, 0)
        self.events_spin = QSpinBox()
        self.events_spin.setRange(100, 10000000)
        self.events_spin.setValue(100000)
        self.events_spin.setGroupSeparatorShown(True)
        sim_layout.addWidget(self.events_spin, 0, 1)
        
        # Random seed
        sim_layout.addWidget(QLabel("Random Seed:"), 1, 0)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 999999)
        self.seed_spin.setValue(-1)
        self.seed_spin.setSpecialValueText("Random")
        sim_layout.addWidget(self.seed_spin, 1, 1)
        
        # Physics options
        self.fluorescence_check = QCheckBox("Include Fluorescence")
        self.fluorescence_check.setChecked(True)
        sim_layout.addWidget(self.fluorescence_check, 2, 0)
        
        self.auger_check = QCheckBox("Include Auger Electrons")
        self.auger_check.setChecked(True)
        sim_layout.addWidget(self.auger_check, 2, 1)
        
        sim_widget = QWidget()
        sim_widget.setLayout(sim_layout)
        sim_card.layout().addWidget(sim_widget)
        
        layout.addWidget(beam_card)
        layout.addWidget(resist_card)
        layout.addWidget(sim_card)
        layout.addStretch()
        
        # Connect signals
        self._connect_signals()
    
    def _connect_signals(self):
        """Connect parameter change signals"""
        self.energy_spin.valueChanged.connect(self._emit_parameters)
        self.beam_size_spin.valueChanged.connect(self._emit_parameters)
        self.current_spin.valueChanged.connect(self._emit_parameters)
        self.material_combo.currentTextChanged.connect(self._emit_parameters)
        self.thickness_spin.valueChanged.connect(self._emit_parameters)
        self.density_spin.valueChanged.connect(self._emit_parameters)
        self.events_spin.valueChanged.connect(self._emit_parameters)
        self.seed_spin.valueChanged.connect(self._emit_parameters)
        self.fluorescence_check.toggled.connect(self._emit_parameters)
        self.auger_check.toggled.connect(self._emit_parameters)
    
    def _emit_parameters(self):
        """Emit current parameters"""
        params = {
            'energy': self.energy_spin.value(),
            'beam_size': self.beam_size_spin.value(),
            'current': self.current_spin.value(),
            'material': self.material_combo.currentText(),
            'thickness': self.thickness_spin.value(),
            'density': self.density_spin.value(),
            'events': self.events_spin.value(),
            'seed': self.seed_spin.value(),
            'fluorescence': self.fluorescence_check.isChecked(),
            'auger': self.auger_check.isChecked()
        }
        self.parameters_changed.emit(params)


class PSFMetricsWidget(QWidget):
    """Display PSF analysis metrics and statistics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup metrics dashboard"""
        layout = QVBoxLayout(self)
        
        # Create metrics cards
        self.metrics_data = [
            {"title": "FWHM", "value": "2.1", "unit": "nm", "trend": None},
            {"title": "Alpha (Forward)", "value": "0.85", "unit": "", "trend": "+2%"},
            {"title": "Beta (Backscatter)", "value": "0.15", "unit": "", "trend": "-1%"},
            {"title": "Total Energy", "value": "28.5", "unit": "keV", "trend": None},
            {"title": "Resist Energy", "value": "26.8", "unit": "keV", "trend": "+5%"},
            {"title": "Energy Efficiency", "value": "94.0", "unit": "%", "trend": "+3%"},
            {"title": "Peak Intensity", "value": "45.2", "unit": "eV/nm²", "trend": None},
            {"title": "PSF Range", "value": "15.8", "unit": "nm", "trend": "-2%"}
        ]
        
        dashboard = create_metric_dashboard(self.metrics_data)
        layout.addWidget(dashboard)
    
    def update_metrics(self, psf_data: Dict[str, Any]):
        """Update metrics from PSF analysis results"""
        # Implementation for updating metrics from simulation results
        pass


class PSFAnalysisInterface(QWidget):
    """Complete PSF Analysis Interface"""
    
    simulation_started = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the complete PSF interface"""
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        
        # Left panel - Parameters and controls
        left_panel = QWidget()
        left_panel.setFixedWidth(380)
        left_layout = QVBoxLayout(left_panel)
        
        # Parameters widget
        self.parameters_widget = PSFParametersWidget()
        left_layout.addWidget(self.parameters_widget)
        
        # Control buttons
        controls_card = MaterialCard("Simulation Control")
        controls_layout = QVBoxLayout()
        
        self.run_button = ModernButton("Run PSF Analysis", "success")
        self.stop_button = ModernButton("Stop", "danger")
        self.stop_button.setEnabled(False)
        
        self.progress_bar = ModernProgressBar()
        
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(QLabel("Progress:"))
        controls_layout.addWidget(self.progress_bar)
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_card.layout().addWidget(controls_widget)
        
        left_layout.addWidget(controls_card)
        
        # Right panel - Visualization and results
        right_splitter = QSplitter(Qt.Vertical)
        
        # Visualization
        self.viz_widget = PSFVisualizationWidget()
        right_splitter.addWidget(self.viz_widget)
        
        # Metrics
        self.metrics_widget = PSFMetricsWidget()
        right_splitter.addWidget(self.metrics_widget)
        
        # Set splitter proportions
        right_splitter.setSizes([600, 300])
        
        layout.addWidget(left_panel)
        layout.addWidget(right_splitter, 1)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.run_button.clicked.connect(self.start_psf_simulation)
        self.stop_button.clicked.connect(self.stop_psf_simulation)
        self.parameters_widget.parameters_changed.connect(self.on_parameters_changed)
    
    def start_psf_simulation(self):
        """Start PSF simulation"""
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValueAnimated(0)
        
        # Get current parameters
        params = self.get_current_parameters()
        self.simulation_started.emit(params)
    
    def stop_psf_simulation(self):
        """Stop PSF simulation"""
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current simulation parameters"""
        # Implementation to gather all current parameters
        return {}
    
    def on_parameters_changed(self, params: Dict[str, Any]):
        """Handle parameter changes"""
        # Update preview calculations if needed
        pass
    
    def update_progress(self, value: int):
        """Update simulation progress"""
        self.progress_bar.setValueAnimated(value)
    
    def display_results(self, results: Dict[str, Any]):
        """Display PSF analysis results"""
        self.metrics_widget.update_metrics(results)
        # Update visualization
        pass