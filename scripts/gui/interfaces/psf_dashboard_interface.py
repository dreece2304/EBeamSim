"""
PSF Dashboard Interface - High DPI Optimized Dashboard Design
============================================================

Modern dashboard approach for PSF Analysis with progressive disclosure:
- Main dashboard shows essential info only  
- Parameter sections open in dedicated windows/dialogs
- Optimized for high DPI displays (2880x1800)
- Uses "overview first, zoom and filter, then details on demand" principle
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QTabWidget, QDialog,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QScrollArea, QFrame, QProgressBar, QCheckBox, QSlider, QDialogButtonBox,
    QFormLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QSize
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


class ParameterDetailDialog(QDialog):
    """Base class for parameter detail dialogs"""
    
    parameters_changed = Signal(dict)
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(500, 400)  # Good size for high DPI
        
        # Apply dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 12px;
            }
            QLabel {
                color: #f9fafb;
                font-size: 14px;
                font-weight: 500;
            }
            QDoubleSpinBox, QSpinBox, QComboBox {
                background: #374151;
                border: 2px solid #4b5563;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #f9fafb;
                min-height: 20px;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #6366f1;
                background: #1e293b;
            }
        """)
    
    def create_button_box(self):
        """Create standard OK/Cancel button box"""
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        
        # Style the buttons
        button_box.setStyleSheet("""
            QDialogButtonBox {
                dialogbuttonbox-buttons-have-icons: 0;
            }
            QPushButton {
                background: #6366f1;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                color: white;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #4f46e5;
            }
            QPushButton:pressed {
                background: #4338ca;
            }
        """)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        return button_box


class BeamParametersDialog(ParameterDetailDialog):
    """Beam parameters configuration dialog"""
    
    def __init__(self, parent=None):
        super().__init__("Beam Parameters", parent)
        self.setup_ui()
        self.load_current_values()
    
    def setup_ui(self):
        """Setup beam parameters UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Configure Electron Beam Parameters")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #6366f1;
            margin-bottom: 16px;
        """)
        layout.addWidget(header)
        
        # Parameters form
        form_card = MaterialCard("Beam Configuration")
        form_layout = QFormLayout()
        form_layout.setSpacing(16)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Energy
        energy_label = QLabel("Beam Energy:")
        energy_label.setToolTip("Accelerating voltage of the electron beam")
        self.energy_spin = QDoubleSpinBox()
        self.energy_spin.setRange(1.0, 300.0)
        self.energy_spin.setValue(30.0)
        self.energy_spin.setSuffix(" keV")
        self.energy_spin.setDecimals(1)
        form_layout.addRow(energy_label, self.energy_spin)
        
        # Beam size
        beam_size_label = QLabel("Beam Size (FWHM):")
        beam_size_label.setToolTip("Full width at half maximum of the electron beam")
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.1, 50.0)
        self.beam_size_spin.setValue(1.0)
        self.beam_size_spin.setSuffix(" nm")
        self.beam_size_spin.setDecimals(2)
        form_layout.addRow(beam_size_label, self.beam_size_spin)
        
        # Current
        current_label = QLabel("Beam Current:")
        current_label.setToolTip("Electron beam current")
        self.current_spin = QDoubleSpinBox()
        self.current_spin.setRange(0.1, 1000.0)
        self.current_spin.setValue(10.0)
        self.current_spin.setSuffix(" pA")
        self.current_spin.setDecimals(1)
        form_layout.addRow(current_label, self.current_spin)
        
        # Dwell time
        dwell_label = QLabel("Dwell Time:")
        dwell_label.setToolTip("Time the beam dwells at each point")
        self.dwell_spin = QDoubleSpinBox()
        self.dwell_spin.setRange(0.1, 100.0)
        self.dwell_spin.setValue(1.0)
        self.dwell_spin.setSuffix(" μs")
        self.dwell_spin.setDecimals(1)
        form_layout.addRow(dwell_label, self.dwell_spin)
        
        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_card.layout().addWidget(form_widget)
        layout.addWidget(form_card)
        
        # Quick presets
        presets_card = MaterialCard("Quick Presets")
        presets_layout = QHBoxLayout()
        
        self.jeol_preset_btn = ModernButton("JEOL Standard", "secondary")
        self.high_res_preset_btn = ModernButton("High Resolution", "secondary")
        self.high_current_preset_btn = ModernButton("High Current", "secondary")
        
        self.jeol_preset_btn.clicked.connect(self.apply_jeol_preset)
        self.high_res_preset_btn.clicked.connect(self.apply_high_res_preset)
        self.high_current_preset_btn.clicked.connect(self.apply_high_current_preset)
        
        presets_layout.addWidget(self.jeol_preset_btn)
        presets_layout.addWidget(self.high_res_preset_btn) 
        presets_layout.addWidget(self.high_current_preset_btn)
        presets_layout.addStretch()
        
        presets_widget = QWidget()
        presets_widget.setLayout(presets_layout)
        presets_card.layout().addWidget(presets_widget)
        layout.addWidget(presets_card)
        
        layout.addStretch()
        
        # Button box
        button_box = self.create_button_box()
        layout.addWidget(button_box)
        
        # Connect signals
        self.energy_spin.valueChanged.connect(self.on_parameters_changed)
        self.beam_size_spin.valueChanged.connect(self.on_parameters_changed)
        self.current_spin.valueChanged.connect(self.on_parameters_changed)
        self.dwell_spin.valueChanged.connect(self.on_parameters_changed)
    
    def apply_jeol_preset(self):
        """Apply JEOL standard parameters"""
        self.energy_spin.setValue(30.0)
        self.beam_size_spin.setValue(1.0)
        self.current_spin.setValue(10.0)
        self.dwell_spin.setValue(1.0)
    
    def apply_high_res_preset(self):
        """Apply high resolution parameters"""
        self.energy_spin.setValue(30.0)
        self.beam_size_spin.setValue(0.5)
        self.current_spin.setValue(5.0)
        self.dwell_spin.setValue(2.0)
    
    def apply_high_current_preset(self):
        """Apply high current parameters"""
        self.energy_spin.setValue(30.0)
        self.beam_size_spin.setValue(2.0)
        self.current_spin.setValue(50.0)
        self.dwell_spin.setValue(0.5)
    
    def load_current_values(self):
        """Load current values from main interface"""
        # In real implementation, this would load from parent interface
        pass
    
    def on_parameters_changed(self):
        """Emit parameter changes"""
        params = self.get_parameters()
        self.parameters_changed.emit(params)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current beam parameters"""
        return {
            'energy': self.energy_spin.value(),
            'beam_size': self.beam_size_spin.value(), 
            'current': self.current_spin.value(),
            'dwell_time': self.dwell_spin.value()
        }


class ResistParametersDialog(ParameterDetailDialog):
    """Resist parameters configuration dialog"""
    
    def __init__(self, parent=None):
        super().__init__("Resist Parameters", parent)
        self.setup_ui()
        self.load_current_values()
    
    def setup_ui(self):
        """Setup resist parameters UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Configure Resist Material Properties")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #6366f1;
            margin-bottom: 16px;
        """)
        layout.addWidget(header)
        
        # Material selection
        material_card = MaterialCard("Material Selection")
        material_layout = QFormLayout()
        material_layout.setSpacing(16)
        
        # Material combo
        material_label = QLabel("Resist Material:")
        self.material_combo = QComboBox()
        self.material_combo.addItems([
            "PMMA", "HSQ", "ZEP", "Alucone_XPS", "Alucone_Exposed", "Custom"
        ])
        self.material_combo.setCurrentText("Alucone_XPS")
        material_layout.addRow(material_label, self.material_combo)
        
        material_widget = QWidget()
        material_widget.setLayout(material_layout)
        material_card.layout().addWidget(material_widget)
        layout.addWidget(material_card)
        
        # Physical properties
        props_card = MaterialCard("Physical Properties")
        props_layout = QFormLayout()
        props_layout.setSpacing(16)
        
        # Thickness
        thickness_label = QLabel("Film Thickness:")
        thickness_label.setToolTip("Resist film thickness")
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 1000.0)
        self.thickness_spin.setValue(30.0)
        self.thickness_spin.setSuffix(" nm")
        self.thickness_spin.setDecimals(1)
        props_layout.addRow(thickness_label, self.thickness_spin)
        
        # Density
        density_label = QLabel("Material Density:")
        density_label.setToolTip("Mass density of the resist material")
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 5.0)
        self.density_spin.setValue(1.35)
        self.density_spin.setSuffix(" g/cm³")
        self.density_spin.setDecimals(3)
        props_layout.addRow(density_label, self.density_spin)
        
        # Atomic composition (for custom materials)
        composition_label = QLabel("Atomic Composition:")
        composition_label.setToolTip("Elements and their ratios (for custom materials)")
        self.composition_input = ModernInput("e.g., C8H8O2", "Composition")
        props_layout.addRow(composition_label, self.composition_input)
        
        props_widget = QWidget()
        props_widget.setLayout(props_layout)
        props_card.layout().addWidget(props_widget)
        layout.addWidget(props_card)
        
        # Processing parameters
        process_card = MaterialCard("Processing Parameters")
        process_layout = QFormLayout()
        process_layout.setSpacing(16)
        
        # Development parameters
        dev_time_label = QLabel("Development Time:")
        self.dev_time_spin = QDoubleSpinBox()
        self.dev_time_spin.setRange(1.0, 300.0)
        self.dev_time_spin.setValue(60.0)
        self.dev_time_spin.setSuffix(" sec")
        process_layout.addRow(dev_time_label, self.dev_time_spin)
        
        # Development temperature
        dev_temp_label = QLabel("Development Temperature:")
        self.dev_temp_spin = QDoubleSpinBox()
        self.dev_temp_spin.setRange(15.0, 50.0)
        self.dev_temp_spin.setValue(23.0)
        self.dev_temp_spin.setSuffix(" °C")
        process_layout.addRow(dev_temp_label, self.dev_temp_spin)
        
        process_widget = QWidget()
        process_widget.setLayout(process_layout)
        process_card.layout().addWidget(process_widget)
        layout.addWidget(process_card)
        
        layout.addStretch()
        
        # Button box
        button_box = self.create_button_box()
        layout.addWidget(button_box)
        
        # Connect signals
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        self.thickness_spin.valueChanged.connect(self.on_parameters_changed)
        self.density_spin.valueChanged.connect(self.on_parameters_changed)
    
    def on_material_changed(self, material: str):
        """Handle material selection change"""
        # Update density based on material
        material_densities = {
            "PMMA": 1.18,
            "HSQ": 1.35,
            "ZEP": 1.56,
            "Alucone_XPS": 1.35,
            "Alucone_Exposed": 1.40
        }
        
        if material in material_densities:
            self.density_spin.setValue(material_densities[material])
        
        self.on_parameters_changed()
    
    def load_current_values(self):
        """Load current values from main interface"""
        pass
    
    def on_parameters_changed(self):
        """Emit parameter changes"""
        params = self.get_parameters()
        self.parameters_changed.emit(params)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current resist parameters"""
        return {
            'material': self.material_combo.currentText(),
            'thickness': self.thickness_spin.value(),
            'density': self.density_spin.value(),
            'composition': self.composition_input.text(),
            'dev_time': self.dev_time_spin.value(),
            'dev_temp': self.dev_temp_spin.value()
        }


class SimulationParametersDialog(ParameterDetailDialog):
    """Simulation parameters configuration dialog"""
    
    def __init__(self, parent=None):
        super().__init__("Simulation Parameters", parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup simulation parameters UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Configure Simulation Settings")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #6366f1;
            margin-bottom: 16px;
        """)
        layout.addWidget(header)
        
        # Basic parameters
        basic_card = MaterialCard("Basic Settings")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(16)
        
        # Number of events
        events_label = QLabel("Number of Events:")
        events_label.setToolTip("Number of primary electrons to simulate")
        self.events_spin = QSpinBox()
        self.events_spin.setRange(1000, 10000000)
        self.events_spin.setValue(100000)
        self.events_spin.setGroupSeparatorShown(True)
        basic_layout.addRow(events_label, self.events_spin)
        
        # Random seed
        seed_label = QLabel("Random Seed:")
        seed_label.setToolTip("Seed for random number generator (-1 for random)")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 999999)
        self.seed_spin.setValue(-1)
        self.seed_spin.setSpecialValueText("Random")
        basic_layout.addRow(seed_label, self.seed_spin)
        
        basic_widget = QWidget()
        basic_widget.setLayout(basic_layout)
        basic_card.layout().addWidget(basic_widget)
        layout.addWidget(basic_card)
        
        # Physics options
        physics_card = MaterialCard("Physics Options")
        physics_layout = QVBoxLayout()
        physics_layout.setSpacing(12)
        
        self.fluorescence_check = QCheckBox("Include X-ray Fluorescence")
        self.fluorescence_check.setChecked(True)
        self.fluorescence_check.setToolTip("Include characteristic X-ray production")
        
        self.auger_check = QCheckBox("Include Auger Electrons")
        self.auger_check.setChecked(True)
        self.auger_check.setToolTip("Include Auger electron production")
        
        self.secondaries_check = QCheckBox("Track Secondary Electrons")
        self.secondaries_check.setChecked(True)
        self.secondaries_check.setToolTip("Track low-energy secondary electrons")
        
        self.bremsstrahlung_check = QCheckBox("Include Bremsstrahlung")
        self.bremsstrahlung_check.setChecked(False)
        self.bremsstrahlung_check.setToolTip("Include continuous X-ray production")
        
        physics_layout.addWidget(self.fluorescence_check)
        physics_layout.addWidget(self.auger_check)
        physics_layout.addWidget(self.secondaries_check)
        physics_layout.addWidget(self.bremsstrahlung_check)
        
        physics_widget = QWidget()
        physics_widget.setLayout(physics_layout)
        physics_card.layout().addWidget(physics_widget)
        layout.addWidget(physics_card)
        
        # Performance settings
        perf_card = MaterialCard("Performance Settings")
        perf_layout = QFormLayout()
        perf_layout.setSpacing(16)
        
        # Threading
        threads_label = QLabel("Number of Threads:")
        threads_label.setToolTip("CPU threads for parallel processing")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(4)
        perf_layout.addRow(threads_label, self.threads_spin)
        
        # Cut parameters
        cut_label = QLabel("Production Cuts:")
        cut_label.setToolTip("Minimum energy for particle production")
        self.cut_spin = QDoubleSpinBox()
        self.cut_spin.setRange(0.1, 10.0)
        self.cut_spin.setValue(1.0)
        self.cut_spin.setSuffix(" keV")
        self.cut_spin.setDecimals(1)
        perf_layout.addRow(cut_label, self.cut_spin)
        
        perf_widget = QWidget()
        perf_widget.setLayout(perf_layout)
        perf_card.layout().addWidget(perf_widget)
        layout.addWidget(perf_card)
        
        layout.addStretch()
        
        # Button box
        button_box = self.create_button_box()
        layout.addWidget(button_box)
        
        # Connect signals
        self.events_spin.valueChanged.connect(self.on_parameters_changed)
        self.seed_spin.valueChanged.connect(self.on_parameters_changed)
        self.fluorescence_check.toggled.connect(self.on_parameters_changed)
        self.auger_check.toggled.connect(self.on_parameters_changed)
    
    def on_parameters_changed(self):
        """Emit parameter changes"""
        params = self.get_parameters()
        self.parameters_changed.emit(params)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current simulation parameters"""
        return {
            'events': self.events_spin.value(),
            'seed': self.seed_spin.value(),
            'fluorescence': self.fluorescence_check.isChecked(),
            'auger': self.auger_check.isChecked(),
            'secondaries': self.secondaries_check.isChecked(),
            'bremsstrahlung': self.bremsstrahlung_check.isChecked(),
            'threads': self.threads_spin.value(),
            'cut': self.cut_spin.value()
        }


class PSFDashboardInterface(QWidget):
    """
    Modern PSF Dashboard Interface - High DPI Optimized
    
    Features:
    - Essential information at a glance
    - Parameter details in separate dialogs
    - Large, readable text and controls
    - Progressive disclosure design
    """
    
    simulation_started = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.beam_params = {}
        self.resist_params = {}
        self.sim_params = {}
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the dashboard interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(24)  # Generous spacing for high DPI
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Dashboard header
        self.create_dashboard_header(layout)
        
        # Main dashboard content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)
        
        # Left column - Parameter cards and controls
        left_column = self.create_left_column()
        content_layout.addWidget(left_column)
        
        # Right column - Visualization and key metrics
        right_column = self.create_right_column()
        content_layout.addWidget(right_column, 1)  # Takes more space
        
        layout.addLayout(content_layout, 1)
        
        # Status bar
        self.create_status_section(layout)
    
    def create_dashboard_header(self, layout: QVBoxLayout):
        """Create the dashboard header"""
        header_card = MaterialCard()
        header_layout = QHBoxLayout()
        
        # Title section
        title_section = QVBoxLayout()
        title_label = QLabel("PSF Analysis Dashboard")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #f9fafb;
            margin-bottom: 4px;
        """)
        
        subtitle_label = QLabel("Point Spread Function Characterization & Resist Optimization")
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #9ca3af;
            margin-bottom: 8px;
        """)
        
        title_section.addWidget(title_label)
        title_section.addWidget(subtitle_label)
        title_section.addStretch()
        
        # Quick info section
        info_section = QVBoxLayout()
        self.current_config_label = QLabel("Configuration: Default")
        self.current_config_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #6366f1;
        """)
        
        self.last_run_label = QLabel("Last Run: Never")
        self.last_run_label.setStyleSheet("""
            font-size: 12px;
            color: #9ca3af;
        """)
        
        info_section.addWidget(self.current_config_label)
        info_section.addWidget(self.last_run_label)
        info_section.addStretch()
        
        header_layout.addLayout(title_section, 1)
        header_layout.addLayout(info_section)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_card.layout().addWidget(header_widget)
        
        layout.addWidget(header_card)
    
    def create_left_column(self) -> QWidget:
        """Create left column with parameter cards and controls"""
        column = QWidget()
        column.setFixedWidth(400)  # Wider than original for better visibility
        layout = QVBoxLayout(column)
        layout.setSpacing(16)
        
        # Parameter configuration cards
        self.create_parameter_cards(layout)
        
        # Simulation controls
        self.create_simulation_controls(layout)
        
        layout.addStretch()
        return column
    
    def create_parameter_cards(self, layout: QVBoxLayout):
        """Create parameter configuration cards"""
        # Beam parameters card
        beam_card = MaterialCard("Beam Parameters")
        beam_layout = QVBoxLayout()
        
        # Summary display
        self.beam_summary = QLabel("30.0 keV • 1.0 nm FWHM • 10.0 pA")
        self.beam_summary.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #f9fafb;
            margin-bottom: 8px;
        """)
        
        # Configure button
        self.beam_config_btn = ModernButton("Configure Beam Parameters", "secondary")
        self.beam_config_btn.setMinimumHeight(44)  # Good touch target
        
        beam_layout.addWidget(self.beam_summary)
        beam_layout.addWidget(self.beam_config_btn)
        
        beam_widget = QWidget()
        beam_widget.setLayout(beam_layout)
        beam_card.layout().addWidget(beam_widget)
        
        # Resist parameters card
        resist_card = MaterialCard("Resist Parameters")
        resist_layout = QVBoxLayout()
        
        self.resist_summary = QLabel("Alucone_XPS • 30.0 nm • 1.35 g/cm³")
        self.resist_summary.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #f9fafb;
            margin-bottom: 8px;
        """)
        
        self.resist_config_btn = ModernButton("Configure Resist Parameters", "secondary")
        self.resist_config_btn.setMinimumHeight(44)
        
        resist_layout.addWidget(self.resist_summary)
        resist_layout.addWidget(self.resist_config_btn)
        
        resist_widget = QWidget()
        resist_widget.setLayout(resist_layout)
        resist_card.layout().addWidget(resist_widget)
        
        # Simulation parameters card
        sim_card = MaterialCard("Simulation Parameters")
        sim_layout = QVBoxLayout()
        
        self.sim_summary = QLabel("100,000 events • Physics: Full")
        self.sim_summary.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #f9fafb;
            margin-bottom: 8px;
        """)
        
        self.sim_config_btn = ModernButton("Configure Simulation", "secondary")
        self.sim_config_btn.setMinimumHeight(44)
        
        sim_layout.addWidget(self.sim_summary)
        sim_layout.addWidget(self.sim_config_btn)
        
        sim_widget = QWidget()
        sim_widget.setLayout(sim_layout)
        sim_card.layout().addWidget(sim_widget)
        
        layout.addWidget(beam_card)
        layout.addWidget(resist_card)
        layout.addWidget(sim_card)
    
    def create_simulation_controls(self, layout: QVBoxLayout):
        """Create simulation control section"""
        controls_card = MaterialCard("Simulation Control")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(16)
        
        # Main control buttons
        self.run_button = ModernButton("Run PSF Analysis", "success")
        self.run_button.setMinimumHeight(52)  # Large, prominent button
        self.run_button.setStyleSheet(self.run_button.styleSheet() + """
            ModernButton {
                font-size: 16px;
                font-weight: 700;
            }
        """)
        
        self.stop_button = ModernButton("Stop Simulation", "danger")
        self.stop_button.setMinimumHeight(44)
        self.stop_button.setEnabled(False)
        
        # Progress section
        progress_label = QLabel("Progress:")
        progress_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #f9fafb;
            margin-top: 8px;
        """)
        
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setMinimumHeight(12)  # Thicker progress bar
        
        self.progress_text = QLabel("Ready to simulate")
        self.progress_text.setStyleSheet("""
            font-size: 12px;
            color: #9ca3af;
            margin-top: 4px;
        """)
        
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(progress_label)
        controls_layout.addWidget(self.progress_bar)
        controls_layout.addWidget(self.progress_text)
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_card.layout().addWidget(controls_widget)
        
        layout.addWidget(controls_card)
    
    def create_right_column(self) -> QWidget:
        """Create right column with visualization and metrics"""
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setSpacing(16)
        
        # Key metrics at top
        metrics_card = self.create_key_metrics_card()
        layout.addWidget(metrics_card)
        
        # Visualization area
        viz_card = self.create_visualization_card()
        layout.addWidget(viz_card, 1)  # Takes most space
        
        # Quick analysis tools
        tools_card = self.create_analysis_tools_card()
        layout.addWidget(tools_card)
        
        return column
    
    def create_key_metrics_card(self) -> MaterialCard:
        """Create key metrics display"""
        card = MaterialCard("Key PSF Metrics")
        
        # Metrics grid
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(16)
        
        # Create key metric displays - larger for high DPI
        metrics_data = [
            {"label": "FWHM", "value": "---", "unit": "nm", "description": "Full Width Half Max"},
            {"label": "α (Forward)", "value": "---", "unit": "", "description": "Forward scattering"},
            {"label": "β (Back)", "value": "---", "unit": "", "description": "Backscattering"},
            {"label": "Efficiency", "value": "---", "unit": "%", "description": "Energy efficiency"}
        ]
        
        for i, metric in enumerate(metrics_data):
            metric_widget = self.create_metric_display(
                metric["label"], metric["value"], metric["unit"], metric["description"]
            )
            row, col = divmod(i, 2)
            metrics_layout.addWidget(metric_widget, row, col)
        
        metrics_widget = QWidget()
        metrics_widget.setLayout(metrics_layout)
        card.layout().addWidget(metrics_widget)
        
        return card
    
    def create_metric_display(self, label: str, value: str, unit: str, description: str) -> QWidget:
        """Create individual metric display"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
        """)
        
        # Value
        value_layout = QHBoxLayout()
        value_layout.setSpacing(4)
        
        value_widget = QLabel(value)
        value_widget.setStyleSheet("""
            font-size: 20px;
            font-weight: 800;
            color: #f9fafb;
        """)
        
        unit_widget = QLabel(unit) if unit else QLabel("")
        unit_widget.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #6b7280;
        """)
        
        value_layout.addWidget(value_widget)
        if unit:
            value_layout.addWidget(unit_widget)
        value_layout.addStretch()
        
        # Description
        desc_widget = QLabel(description)
        desc_widget.setStyleSheet("""
            font-size: 10px;
            color: #6b7280;
        """)
        
        layout.addWidget(label_widget)
        layout.addLayout(value_layout)
        layout.addWidget(desc_widget)
        
        # Background
        widget.setStyleSheet("""
            QWidget {
                background: #374151;
                border: 1px solid #4b5563;
                border-radius: 8px;
            }
        """)
        
        return widget
    
    def create_visualization_card(self) -> MaterialCard:
        """Create visualization area"""
        card = MaterialCard("PSF Visualization")
        
        # For now, placeholder for visualization
        viz_layout = QVBoxLayout()
        
        # Visualization controls
        controls_layout = QHBoxLayout()
        
        self.view_radial_btn = ModernButton("Radial Profile", "ghost")
        self.view_2d_btn = ModernButton("2D Map", "ghost")
        self.view_log_btn = ModernButton("Log Scale", "ghost")
        
        controls_layout.addWidget(self.view_radial_btn)
        controls_layout.addWidget(self.view_2d_btn)
        controls_layout.addWidget(self.view_log_btn)
        controls_layout.addStretch()
        
        # Placeholder visualization area
        viz_placeholder = QLabel("PSF visualization will appear here after simulation")
        viz_placeholder.setStyleSheet("""
            background: #374151;
            border: 2px dashed #4b5563;
            border-radius: 8px;
            padding: 40px;
            font-size: 14px;
            color: #9ca3af;
            text-align: center;
        """)
        viz_placeholder.setAlignment(Qt.AlignCenter)
        viz_placeholder.setMinimumHeight(300)
        
        viz_layout.addLayout(controls_layout)
        viz_layout.addWidget(viz_placeholder, 1)
        
        viz_widget = QWidget()
        viz_widget.setLayout(viz_layout)
        card.layout().addWidget(viz_widget)
        
        return card
    
    def create_analysis_tools_card(self) -> MaterialCard:
        """Create analysis tools section"""
        card = MaterialCard("Analysis Tools")
        
        tools_layout = QHBoxLayout()
        
        self.beamer_export_btn = ModernButton("BEAMER Export", "primary")
        self.save_results_btn = ModernButton("Save Results", "secondary")
        self.compare_btn = ModernButton("Compare PSFs", "ghost")
        
        tools_layout.addWidget(self.beamer_export_btn)
        tools_layout.addWidget(self.save_results_btn)
        tools_layout.addWidget(self.compare_btn)
        tools_layout.addStretch()
        
        tools_widget = QWidget()
        tools_widget.setLayout(tools_layout)
        card.layout().addWidget(tools_widget)
        
        return card
    
    def create_status_section(self, layout: QVBoxLayout):
        """Create status section"""
        status_card = MaterialCard()
        status_layout = QHBoxLayout()
        
        # Status indicator
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #10b981;
        """)
        
        # System info
        self.system_info = QLabel("System: Ready • GPU: Available • Geant4: 11.3.2")
        self.system_info.setStyleSheet("""
            font-size: 12px;
            color: #9ca3af;
        """)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.system_info)
        status_layout.addStretch()
        
        status_widget = QWidget()
        status_widget.setLayout(status_layout)
        status_card.layout().addWidget(status_widget)
        
        layout.addWidget(status_card)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Parameter configuration buttons
        self.beam_config_btn.clicked.connect(self.configure_beam_parameters)
        self.resist_config_btn.clicked.connect(self.configure_resist_parameters)
        self.sim_config_btn.clicked.connect(self.configure_simulation_parameters)
        
        # Simulation controls
        self.run_button.clicked.connect(self.start_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)
        
        # Analysis tools
        self.beamer_export_btn.clicked.connect(self.export_to_beamer)
        self.save_results_btn.clicked.connect(self.save_results)
        self.compare_btn.clicked.connect(self.compare_psfs)
    
    def configure_beam_parameters(self):
        """Open beam parameters dialog"""
        dialog = BeamParametersDialog(self)
        dialog.parameters_changed.connect(self.update_beam_parameters)
        
        if dialog.exec() == QDialog.Accepted:
            params = dialog.get_parameters()
            self.update_beam_parameters(params)
    
    def configure_resist_parameters(self):
        """Open resist parameters dialog"""
        dialog = ResistParametersDialog(self)
        dialog.parameters_changed.connect(self.update_resist_parameters)
        
        if dialog.exec() == QDialog.Accepted:
            params = dialog.get_parameters()
            self.update_resist_parameters(params)
    
    def configure_simulation_parameters(self):
        """Open simulation parameters dialog"""
        dialog = SimulationParametersDialog(self)
        dialog.parameters_changed.connect(self.update_sim_parameters)
        
        if dialog.exec() == QDialog.Accepted:
            params = dialog.get_parameters()
            self.update_sim_parameters(params)
    
    def update_beam_parameters(self, params: Dict[str, Any]):
        """Update beam parameters summary"""
        self.beam_params = params
        summary = f"{params.get('energy', 30.0)} keV • {params.get('beam_size', 1.0)} nm FWHM • {params.get('current', 10.0)} pA"
        self.beam_summary.setText(summary)
    
    def update_resist_parameters(self, params: Dict[str, Any]):
        """Update resist parameters summary"""
        self.resist_params = params
        summary = f"{params.get('material', 'Alucone_XPS')} • {params.get('thickness', 30.0)} nm • {params.get('density', 1.35)} g/cm³"
        self.resist_summary.setText(summary)
    
    def update_sim_parameters(self, params: Dict[str, Any]):
        """Update simulation parameters summary"""
        self.sim_params = params
        events = f"{params.get('events', 100000):,}"
        physics = "Full" if params.get('fluorescence', True) and params.get('auger', True) else "Basic"
        summary = f"{events} events • Physics: {physics}"
        self.sim_summary.setText(summary)
    
    def start_simulation(self):
        """Start PSF simulation"""
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValueAnimated(0)
        self.progress_text.setText("Starting simulation...")
        self.status_label.setText("● Running")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #f59e0b;
        """)
        
        # Gather all parameters
        all_params = {
            'type': 'psf_analysis',
            'beam': self.beam_params,
            'resist': self.resist_params,
            'simulation': self.sim_params
        }
        
        self.simulation_started.emit(all_params)
    
    def stop_simulation(self):
        """Stop simulation"""
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_text.setText("Simulation stopped")
        self.status_label.setText("● Ready")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #10b981;
        """)
    
    def update_progress(self, value: int):
        """Update simulation progress"""
        self.progress_bar.setValueAnimated(value)
        self.progress_text.setText(f"Progress: {value}%")
        
        if value >= 100:
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.progress_text.setText("Simulation completed")
            self.status_label.setText("● Complete")
            self.status_label.setStyleSheet("""
                font-size: 14px;
                font-weight: 600;
                color: #10b981;
            """)
    
    def export_to_beamer(self):
        """Export results to BEAMER format"""
        # Placeholder for BEAMER export functionality
        pass
    
    def save_results(self):
        """Save simulation results"""
        # Placeholder for save functionality
        pass
    
    def compare_psfs(self):
        """Compare multiple PSF results"""
        # Placeholder for comparison functionality
        pass