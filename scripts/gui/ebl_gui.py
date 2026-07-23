#!/usr/bin/env python3
"""
Enhanced EBL Simulation GUI with 2D Visualization - Part 1
------------------------------------------------
Core improvements including:
- Removed placeholder buttons
- Consolidated BEAMER conversion methods
- Consolidated PSF validation
- Added unified file manager
- Fixed 2D contour plotting
- Better button states and status messages
- PSF comparison functionality

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
import json
import re
import glob
import random

# Qt imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit, QPlainTextEdit,
    QProgressBar, QStatusBar, QMenuBar, QFileDialog, QMessageBox,
    QGroupBox, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QSlider, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal, QSettings, QMutex
from PySide6.QtGui import QFont, QIcon, QAction, QPalette, QColor

# Scientific computing
import numpy as np
import pandas as pd

# Import consolidated BEAMER converter
import scipy.interpolate
# Add services directory to path for direct import
# BEAMER conversion is implemented inline in PlotWidget below
# (the old services/beamer_converter.py was unused and is archived)

# Import Geant4 detector and settings dialog
from core.geant4_detector import Geant4PathDetector, setup_geant4_environment
from widgets.settings_dialog import SettingsDialog
from widgets.common.status_button import StatusButton
from core.validator import SimulationValidator
from core import constants as const

# Import canonical SimulationWorker from threading_utils
from utils.threading_utils import SimulationWorker

# Matplotlib for Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.cm as cm

# Import canonical FileManager from core module
from core.file_manager import FileManager



# SimulationWorker is now imported from utils.threading_utils (canonical implementation)


# Plot widgets extracted to widgets/ (July 2026 modularization)
from widgets.enhanced_2d_plot import Enhanced2DPlotWidget
from widgets.psf_plot_widget import PlotWidget


class EBLMainWindow(QMainWindow):
    """Main window for EBL simulation GUI with enhanced functionality"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("EBL", "SimulationGUI")

        # Initialize file manager first. working_dir is where simulation
        # outputs land (the repo's gitignored output/), not the binary's dir.
        self.working_dir = str(Path(__file__).resolve().parent.parent.parent / "output")
        self.file_manager = FileManager(self.working_dir)

        # Initialize Geant4 path (load from settings or auto-detect)
        self.geant4_path = None
        self._initialize_geant4_path()

        self.setup_ui()
        self.setup_defaults()
        self.load_settings()

        # Simulation state
        self.simulation_worker = None
        self.simulation_thread = None
        self.simulation_running = False

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("EBL Simulation Control - Enhanced Edition v3.1")
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
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #404040;
                border: 1px solid #555555;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                color: #ffffff;
                outline: none;
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

        # Create tabs (removed unused tabs: Pattern Exposure, Proximity Correction)
        self.create_resist_tab()
        self.create_beam_tab()
        self.create_simulation_tab()
        # self.create_pattern_tab()  # REMOVED - Not used
        self.create_output_tab()
        self.create_1d_visualization_tab()
        self.create_2d_visualization_tab()
        self.create_pattern_heatmap_tab()
        # self.create_proximity_correction_tab()  # REMOVED - Not used
        # Note: Removed analysis tab, pattern tab, and proximity correction tab as unused

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)

        # Create menu bar and status bar
        self.create_menu_bar()
        self.create_status_bar()

        # Add tab switching shortcuts
        self.setup_tab_shortcuts()

    def create_menu_bar(self):
        """Create enhanced menu bar with consolidated BEAMER tools"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        select_exe_action = QAction("Select &Executable...", self)
        select_exe_action.setShortcut("Ctrl+E")
        select_exe_action.triggered.connect(self.select_executable)
        file_menu.addAction(select_exe_action)

        save_macro_action = QAction("Save &Macro...", self)
        save_macro_action.setShortcut("Ctrl+M")
        save_macro_action.triggered.connect(self.save_macro)
        file_menu.addAction(save_macro_action)

        load_config_action = QAction("&Load Configuration...", self)
        load_config_action.setShortcut("Ctrl+O")
        load_config_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_config_action)

        save_config_action = QAction("&Save Configuration...", self)
        save_config_action.setShortcut("Ctrl+S")
        save_config_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_config_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Simulation menu
        sim_menu = menubar.addMenu("&Simulation")

        run_action = QAction("&Run Simulation", self)
        run_action.setShortcut("Ctrl+R")
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)

        stop_action = QAction("&Stop Simulation", self)
        stop_action.setShortcut("Esc")
        stop_action.triggered.connect(self.stop_simulation)
        sim_menu.addAction(stop_action)

        sim_menu.addSeparator()

        generate_action = QAction("&Generate Macro", self)
        generate_action.setShortcut("Ctrl+G")
        generate_action.triggered.connect(self.generate_macro)
        sim_menu.addAction(generate_action)

        # Enhanced BEAMER menu with consolidated functionality
        beamer_menu = menubar.addMenu("BEAMER")

        convert_action = QAction("Convert PSF to BEAMER Format", self)
        convert_action.triggered.connect(self.convert_psf_to_beamer_main)
        beamer_menu.addAction(convert_action)

        batch_convert_action = QAction("Batch Convert to BEAMER", self)
        batch_convert_action.triggered.connect(self.batch_convert_beamer_main)
        beamer_menu.addAction(batch_convert_action)

        beamer_menu.addSeparator()

        validate_psf_action = QAction("Validate PSF Data", self)
        validate_psf_action.triggered.connect(self.validate_psf_data_main)
        beamer_menu.addAction(validate_psf_action)

        compare_beamer_action = QAction("Compare BEAMER Files", self)
        compare_beamer_action.triggered.connect(self.compare_beamer_files_main)
        beamer_menu.addAction(compare_beamer_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        psf_compare_action = QAction("&PSF Comparison Tool", self)
        psf_compare_action.setShortcut("Ctrl+P")
        psf_compare_action.triggered.connect(self.open_psf_comparison)
        tools_menu.addAction(psf_compare_action)

        recent_files_action = QAction("&Recent Simulation Files", self)
        recent_files_action.setShortcut("Ctrl+H")
        recent_files_action.triggered.connect(self.show_recent_files)
        tools_menu.addAction(recent_files_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        beamer_help_action = QAction("&BEAMER Format Help", self)
        beamer_help_action.triggered.connect(self.show_beamer_help)
        help_menu.addAction(beamer_help_action)

    def create_status_bar(self):
        """Create enhanced status bar with better progress indication"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress bar (enhanced)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # File operations indicator
        self.file_status_label = QLabel("")

    def setup_tab_shortcuts(self):
        """Setup keyboard shortcuts for tab switching"""
        from PySide6.QtGui import QShortcut, QKeySequence

        # Ctrl+1 through Ctrl+9 for direct tab switching
        for i in range(1, 10):
            if i <= self.tab_widget.count():
                shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
                # Use lambda with default argument to capture current value of i
                shortcut.activated.connect(lambda idx=i-1: self.tab_widget.setCurrentIndex(idx))

        # Ctrl+Tab for next tab
        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self.next_tab)

        # Ctrl+Shift+Tab for previous tab
        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self.previous_tab)

    def next_tab(self):
        """Switch to next tab"""
        current = self.tab_widget.currentIndex()
        next_index = (current + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)

    def previous_tab(self):
        """Switch to previous tab"""
        current = self.tab_widget.currentIndex()
        prev_index = (current - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)

    def create_resist_tab(self):
        """Enhanced resist properties tab with simplified material builder"""
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
            "Biscone_2Butyne": ("Bi:1,C:4,H:4,O:2", 3.3),
            "Biscone_2Butyne_Hydrated": ("Bi:1,C:4,H:6,O:3", 3.1),
            "Sn-MLD": ("Sn:1,C:8,H:8,O:4", 2.0),
            "Custom": ("", 1.0)
        }

        # Simplified atomic weights for basic calculations
        self.atomic_weights = {
            'H': 1.008, 'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998,
            'Al': 26.982, 'Si': 28.086, 'P': 30.974, 'S': 32.065,
            'Ti': 47.867, 'Sn': 118.71, 'Zr': 91.224, 'Hf': 178.49, 'W': 183.84,
            'Au': 196.97, 'Bi': 208.98
        }

        material_layout.addWidget(QLabel("Material:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems(list(self.material_presets.keys()))
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        material_layout.addWidget(self.material_combo, 0, 1)

        material_layout.addWidget(QLabel("Composition:"), 1, 0)
        self.composition_edit = QLineEdit()
        self.composition_edit.setPlaceholderText("Al:1,C:5,H:4,O:2")
        self.composition_edit.textChanged.connect(self.on_composition_changed)
        material_layout.addWidget(self.composition_edit, 1, 1, 1, 2)

        # Density with simple estimation
        material_layout.addWidget(QLabel("Density (g/cm³):"), 2, 0)

        density_layout = QHBoxLayout()
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 25.0)
        self.density_spin.setValue(1.35)
        self.density_spin.setDecimals(2)
        density_layout.addWidget(self.density_spin)

        self.estimate_density_button = StatusButton("Estimate")
        self.estimate_density_button.setMaximumWidth(80)
        self.estimate_density_button.clicked.connect(self.estimate_density)
        self.estimate_density_button.setToolTip("Estimate density from composition")
        density_layout.addWidget(self.estimate_density_button)

        material_layout.addLayout(density_layout, 2, 1, 1, 2)

        material_layout.addWidget(QLabel("Thickness (nm):"), 3, 0)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 10000.0)
        self.thickness_spin.setValue(30.0)
        self.thickness_spin.setDecimals(1)
        material_layout.addWidget(self.thickness_spin, 3, 1)

        material_group.setLayout(material_layout)

        # Enhanced Material Builder with status feedback
        builder_group = QGroupBox("Quick Material Builder")
        builder_layout = QGridLayout()

        # Common elements dropdown
        builder_layout.addWidget(QLabel("Add Element:"), 0, 0)
        self.element_combo = QComboBox()
        common_elements = ['H', 'C', 'N', 'O', 'F', 'Al', 'Si', 'P', 'S', 'Ti', 'Zr', 'Hf', 'W', 'Au', 'Bi']
        self.element_combo.addItems(common_elements)
        builder_layout.addWidget(self.element_combo, 0, 1)

        builder_layout.addWidget(QLabel("Ratio:"), 0, 2)
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.01, 100.0)
        self.ratio_spin.setValue(1.0)
        self.ratio_spin.setDecimals(2)
        builder_layout.addWidget(self.ratio_spin, 0, 3)

        self.add_element_button = StatusButton("Add")
        self.add_element_button.clicked.connect(self.add_element_to_composition)
        builder_layout.addWidget(self.add_element_button, 0, 4)

        # Quick actions
        actions_layout = QHBoxLayout()
        self.validate_composition_button = StatusButton("Validate")
        self.validate_composition_button.clicked.connect(self.validate_composition)
        actions_layout.addWidget(self.validate_composition_button)

        self.clear_composition_button = StatusButton("Clear")
        self.clear_composition_button.clicked.connect(self.clear_composition)
        actions_layout.addWidget(self.clear_composition_button)

        builder_layout.addLayout(actions_layout, 1, 0, 1, 5)
        builder_group.setLayout(builder_layout)

        # Info group with enhanced composition display
        info_group = QGroupBox("Material Information")
        info_layout = QVBoxLayout()

        self.info_text = QLabel("""
    <b>Available materials:</b><br>
    • Alucone: Al:1,C:5,H:4,O:2 (1.35 g/cm³)<br>
    • Biscone: Bi:1,C:4,H:4,O:2 (3.3 g/cm³)<br>
    • From MLD process - 2-butyne linker
        """)
        self.info_text.setWordWrap(True)
        info_layout.addWidget(self.info_text)

        # Composition analysis display
        self.analysis_text = QLabel("")
        self.analysis_text.setWordWrap(True)
        self.analysis_text.setStyleSheet("color: #007acc; font-size: 10px;")
        info_layout.addWidget(self.analysis_text)

        info_group.setLayout(info_layout)

        layout.addWidget(material_group)
        layout.addWidget(builder_group)
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

        # NOTE: Point source (0nm) is default for PSF generation because BEAMER
        # applies short-range blur correction for beam diameter separately.
        beam_layout.addWidget(QLabel("Beam Size (nm):"), 1, 0)
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.0, 1000.0)  # Allow 0 for point source
        self.beam_size_spin.setValue(0.0)  # Point source default (BEAMER handles blur)
        self.beam_size_spin.setDecimals(1)
        self.beam_size_spin.setToolTip(
            "Leave at 0 (point source) for BEAMER PSFs - BEAMER applies the tool's "
            "beam blur separately, so a finite size here would double-count it.")
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

        # Enhanced output options
        self.auto_increment_check = QCheckBox("Auto-increment run number")
        self.auto_increment_check.setChecked(True)
        sim_layout.addWidget(self.auto_increment_check, 3, 0, 1, 2)

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

        # Enhanced control buttons
        button_layout = QHBoxLayout()

        self.generate_button = StatusButton("Generate Macro")
        self.generate_button.clicked.connect(self.generate_macro)
        button_layout.addWidget(self.generate_button)

        self.run_button = StatusButton("Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)

        self.stop_button = StatusButton("Stop Simulation")
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

    def create_pattern_tab(self):
        """Create pattern exposure tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # JEOL Mode Selection
        mode_group = QGroupBox("JEOL Operating Mode")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        self.mode3_radio = QRadioButton("Mode 3 (4th Lens) - 500 um field, 1.0 nm grid")
        self.mode6_radio = QRadioButton("Mode 6 (5th Lens) - 62.5 um field, 0.125 nm grid")
        self.mode3_radio.setChecked(True)
        
        self.mode_group.addButton(self.mode3_radio, 0)
        self.mode_group.addButton(self.mode6_radio, 1)
        
        mode_layout.addWidget(self.mode3_radio)
        mode_layout.addWidget(self.mode6_radio)
        mode_group.setLayout(mode_layout)
        
        # Pattern Parameters
        pattern_group = QGroupBox("Pattern Parameters")
        pattern_layout = QGridLayout()
        
        pattern_layout.addWidget(QLabel("Pattern Type:"), 0, 0)
        self.pattern_type_combo = QComboBox()
        self.pattern_type_combo.addItems(["Square", "Single Spot", "Line", "Custom"])
        pattern_layout.addWidget(self.pattern_type_combo, 0, 1)
        
        pattern_layout.addWidget(QLabel("Pattern Size (nm):"), 1, 0)
        self.pattern_size_spin = QDoubleSpinBox()
        self.pattern_size_spin.setRange(1, 50000)
        self.pattern_size_spin.setValue(1000)
        self.pattern_size_spin.setSuffix(" nm")
        pattern_layout.addWidget(self.pattern_size_spin, 1, 1)
        
        pattern_layout.addWidget(QLabel("Center X (nm):"), 2, 0)
        self.pattern_x_spin = QDoubleSpinBox()
        self.pattern_x_spin.setRange(-250000, 250000)
        self.pattern_x_spin.setValue(0)
        self.pattern_x_spin.setSuffix(" nm")
        pattern_layout.addWidget(self.pattern_x_spin, 2, 1)
        
        pattern_layout.addWidget(QLabel("Center Y (nm):"), 3, 0)
        self.pattern_y_spin = QDoubleSpinBox()
        self.pattern_y_spin.setRange(-250000, 250000)
        self.pattern_y_spin.setValue(0)
        self.pattern_y_spin.setSuffix(" nm")
        pattern_layout.addWidget(self.pattern_y_spin, 3, 1)
        
        pattern_group.setLayout(pattern_layout)
        
        # Exposure Parameters
        exposure_group = QGroupBox("Exposure Parameters")
        exposure_layout = QGridLayout()
        
        exposure_layout.addWidget(QLabel("Beam Current:"), 0, 0)
        self.beam_current_combo = QComboBox()
        # JEOL available currents from documentation
        jeol_currents = ["0.5 nA", "1 nA", "2 nA", "5 nA", "8 nA", "10 nA", "20 nA"]
        self.beam_current_combo.addItems(jeol_currents)
        self.beam_current_combo.setCurrentText("2 nA")
        exposure_layout.addWidget(self.beam_current_combo, 0, 1)
        
        exposure_layout.addWidget(QLabel("Dose (uC/cm^2):"), 1, 0)
        self.dose_spin = QDoubleSpinBox()
        self.dose_spin.setRange(10, 2000)
        self.dose_spin.setValue(300)
        self.dose_spin.setSuffix(" uC/cm^2")
        exposure_layout.addWidget(self.dose_spin, 1, 1)
        
        exposure_layout.addWidget(QLabel("Shot Pitch:"), 2, 0)
        self.shot_pitch_spin = QSpinBox()
        self.shot_pitch_spin.setRange(1, 20)
        self.shot_pitch_spin.setValue(4)
        self.shot_pitch_spin.setSingleStep(1)  # Allow 1 as well as even numbers
        exposure_layout.addWidget(self.shot_pitch_spin, 2, 1)
        
        # Add tooltip to explain constraint
        self.shot_pitch_spin.setToolTip("Must be 1 or even number (2, 4, 6, ...)")
        
        # Calculate and display dwell time
        self.dwell_time_label = QLabel("Dwell Time: calculating...")
        exposure_layout.addWidget(self.dwell_time_label, 3, 0, 1, 2)
        
        self.clock_freq_label = QLabel("Clock Frequency: calculating...")
        exposure_layout.addWidget(self.clock_freq_label, 4, 0, 1, 2)
        
        self.electrons_per_point_label = QLabel("Electrons/point: calculating...")
        exposure_layout.addWidget(self.electrons_per_point_label, 5, 0, 1, 2)
        
        exposure_group.setLayout(exposure_layout)
        
        # Connect signals to update calculations
        self.beam_current_combo.currentTextChanged.connect(self.update_dwell_time)
        self.dose_spin.valueChanged.connect(self.update_dwell_time)
        self.shot_pitch_spin.valueChanged.connect(self.update_dwell_time)
        self.mode_group.buttonClicked.connect(self.update_dwell_time)
        
        # Dose Grid Parameters
        grid_group = QGroupBox("Dose Grid Settings")
        grid_layout = QGridLayout()
        
        grid_layout.addWidget(QLabel("Grid Resolution X:"), 0, 0)
        self.grid_nx_spin = QSpinBox()
        self.grid_nx_spin.setRange(10, 1000)
        self.grid_nx_spin.setValue(200)
        grid_layout.addWidget(self.grid_nx_spin, 0, 1)
        
        grid_layout.addWidget(QLabel("Grid Resolution Y:"), 1, 0)
        self.grid_ny_spin = QSpinBox()
        self.grid_ny_spin.setRange(10, 1000)
        self.grid_ny_spin.setValue(200)
        grid_layout.addWidget(self.grid_ny_spin, 1, 1)
        
        grid_layout.addWidget(QLabel("Grid Resolution Z:"), 2, 0)
        self.grid_nz_spin = QSpinBox()
        self.grid_nz_spin.setRange(10, 100)
        self.grid_nz_spin.setValue(20)
        grid_layout.addWidget(self.grid_nz_spin, 2, 1)
        
        grid_group.setLayout(grid_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.pattern_mode_check = QCheckBox("Enable Pattern Mode")
        self.pattern_mode_check.setChecked(False)
        button_layout.addWidget(self.pattern_mode_check)
        
        button_layout.addStretch()
        
        self.validate_pattern_btn = StatusButton("Validate Settings")
        self.validate_pattern_btn.clicked.connect(self.validate_pattern_settings)
        button_layout.addWidget(self.validate_pattern_btn)
        
        # Add all groups to layout
        layout.addWidget(mode_group)
        layout.addWidget(pattern_group)
        layout.addWidget(exposure_group)
        layout.addWidget(grid_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Pattern Exposure")
        
        # Initial calculation
        self.update_dwell_time()

    def update_dwell_time(self):
        """Calculate and display dwell time based on JEOL parameters"""
        # Get mode-specific parameters
        if self.mode3_radio.isChecked():
            machine_grid = 1.0  # nm
        else:
            machine_grid = 0.125  # nm
        
        # Calculate exposure grid
        exposure_grid = self.shot_pitch_spin.value() * machine_grid
        
        # Calculate clock frequency (MHz)
        beam_current_text = self.beam_current_combo.currentText()
        beam_current = float(beam_current_text.split()[0])  # Extract number from "X nA"
        dose = self.dose_spin.value()  # uC/cm^2
        
        clock_freq = (beam_current * 1000.0 * 100.0) / (dose * exposure_grid * exposure_grid)
        
        # Check 50 MHz limit
        if clock_freq > 50:
            clock_freq = 50
            actual_dose = (beam_current * 1000.0 * 100.0) / (50.0 * exposure_grid * exposure_grid)
            self.dwell_time_label.setText(f"Dwell Time: {1.0/clock_freq:.3f} us (Dose limited to {actual_dose:.1f} uC/cm^2)")
            self.dwell_time_label.setStyleSheet("color: orange;")
        else:
            dwell_time = 1.0 / clock_freq  # microseconds
            self.dwell_time_label.setText(f"Dwell Time: {dwell_time:.3f} us")
            self.dwell_time_label.setStyleSheet("")
        
        self.clock_freq_label.setText(f"Clock Frequency: {clock_freq:.2f} MHz")
        
        # Calculate electrons per point
        dwell_time_seconds = 1.0 / (clock_freq * 1e6)  # Convert MHz to Hz
        electrons_per_second = beam_current * 1e-9 / 1.602176634e-19  # nA to electrons/s
        electrons_per_point = int(electrons_per_second * dwell_time_seconds)
        
        # Update electrons per point label if it exists
        if hasattr(self, 'electrons_per_point_label'):
            self.electrons_per_point_label.setText(f"Electrons/point: {electrons_per_point}")
    
    def validate_pattern_settings(self):
        """Validate pattern exposure settings"""
        # Check shot pitch
        shot_pitch = self.shot_pitch_spin.value()
        if shot_pitch != 1 and shot_pitch % 2 != 0:
            QMessageBox.warning(self, "Invalid Settings", 
                               f"Shot pitch must be 1 or an even number. Current value: {shot_pitch}")
            return
        
        # Check if pattern fits within field
        pattern_size = self.pattern_size_spin.value()
        
        if self.mode3_radio.isChecked():
            field_size = 500000  # nm
        else:
            field_size = 62500  # nm
        
        if pattern_size > field_size:
            QMessageBox.warning(self, "Invalid Settings", 
                               f"Pattern size ({pattern_size} nm) exceeds field size ({field_size} nm)")
            return
        
        # Check pattern position
        pattern_x = abs(self.pattern_x_spin.value())
        pattern_y = abs(self.pattern_y_spin.value())
        max_coord = max(pattern_x, pattern_y) + pattern_size/2
        
        if max_coord > field_size/2:
            QMessageBox.warning(self, "Invalid Settings", 
                               "Pattern extends beyond field boundaries")
            return
        
        QMessageBox.information(self, "Valid Settings", 
                               "Pattern settings are valid for the selected mode")

    def create_output_tab(self):
        """Create output log tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Output text with memory leak prevention
        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        self.output_text.setMaximumBlockCount(const.MAX_GUI_OUTPUT_LINES)  # Prevent memory leak
        layout.addWidget(self.output_text)

        # Enhanced control buttons
        button_layout = QHBoxLayout()

        clear_button = StatusButton("Clear Log")
        clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_button)

        save_button = StatusButton("Save Log")
        save_button.clicked.connect(self.save_log)
        button_layout.addWidget(save_button)

        # Add filter controls
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Messages", "Errors Only", "Warnings+", "Progress Only"])
        self.filter_combo.currentTextChanged.connect(self.filter_log_messages)
        button_layout.addWidget(QLabel("Filter:"))
        button_layout.addWidget(self.filter_combo)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        self.tab_widget.addTab(widget, "Output Log")

    def create_1d_visualization_tab(self):
        """Create 1D PSF visualization tab with enhanced features"""
        self.plot_widget = PlotWidget(self.file_manager)
        self.tab_widget.addTab(self.plot_widget, "1D PSF Visualization")

    def create_2d_visualization_tab(self):
        """Create 2D depth-radius visualization tab with enhanced features"""
        self.plot_2d_widget = Enhanced2DPlotWidget(self.file_manager)
        self.tab_widget.addTab(self.plot_2d_widget, "2D Visualization")
        
    def create_proximity_correction_tab(self):
        """Create proximity effect correction tab"""
        from widgets.proximity_correction_widget import ProximityCorrectionWidget
        self.proximity_correction_widget = ProximityCorrectionWidget()
        self.tab_widget.addTab(self.proximity_correction_widget, "Proximity Correction")
        
    def create_pattern_heatmap_tab(self):
        """Create improved pattern heatmap visualization tab"""
        from widgets.pattern_heatmap_widget import PatternHeatmapWidget
        self.pattern_heatmap_widget = PatternHeatmapWidget()
        self.tab_widget.addTab(self.pattern_heatmap_widget, "Pattern Heatmap")

    def setup_defaults(self):
        """Setup default values"""
        # Set defaults based on XPS data
        self.material_combo.setCurrentText("Alucone_XPS")
        self.on_material_changed()

        # Set the working executable path (cross-platform)
        import platform
        project_root = Path(__file__).resolve().parent.parent.parent
        exe_ext = ".exe" if platform.system() == "Windows" else ""

        # Try to find executable dynamically
        possible_paths = [
            # Linux/WSL standard build
            project_root / "build" / "bin" / ("ebl_sim" + exe_ext),
            # Windows CLion/CMake builds
            project_root / "cmake-build-release" / "bin" / ("ebl_sim" + exe_ext),
            project_root / "cmake-build-debug" / "bin" / ("ebl_sim" + exe_ext),
            # Visual Studio builds
            project_root / "out" / "build" / "x64-release" / "bin" / ("ebl_sim" + exe_ext),
            project_root / "out" / "build" / "x64-Release" / "bin" / ("ebl_sim" + exe_ext),
        ]

        self.executable_path = ""
        # Outputs always go to the repo's output/ dir regardless of which
        # build directory the binary was found in
        self.working_dir = str(project_root / "output")
        self.file_manager.working_dir = Path(self.working_dir)

        for path in possible_paths:
            if path.exists():
                self.executable_path = str(path)
                self.log_output(f"Found executable: {self.executable_path}")
                break

        if not self.executable_path:
            self.log_output("Warning: ebl_sim executable not found - build it first:")
            self.log_output("  mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j8")
            self.log_output("or use File > Select Executable if it is built elsewhere.")
            self.status_label.setText("ebl_sim not found - build it or use File > Select Executable")

    # Enhanced material helper methods (keeping existing implementation)
    def parse_composition(self, composition_str):
        """Parse composition string into element dictionary"""
        elements = {}
        if not composition_str.strip():
            return elements

        for part in composition_str.split(','):
            if ':' not in part:
                continue
            try:
                element, ratio = part.strip().split(':')
                elements[element.strip()] = float(ratio.strip())
            except ValueError:
                # Report the bad token instead of silently returning {} -
                # callers show their own "invalid composition" warnings
                self.log_output(f"[WARNING] Malformed composition token ignored: '{part.strip()}'")

        return elements

    def estimate_density(self):
        """Simple density estimation using atomic weights and empirical rules"""
        composition = self.composition_edit.text()
        elements = self.parse_composition(composition)

        if not elements:
            QMessageBox.warning(self, "Invalid Composition",
                                "Please enter a valid composition (e.g., Al:1,C:5,H:4,O:2)")
            return

        self.estimate_density_button.set_working(True, "Estimating...")

        try:
            # Calculate molecular weight
            total_weight = 0
            heavy_element_fraction = 0

            for element, ratio in elements.items():
                if element not in self.atomic_weights:
                    QMessageBox.warning(self, "Unknown Element",
                                        f"Element '{element}' not supported.\n"
                                        f"Supported: {', '.join(self.atomic_weights.keys())}")
                    return

                weight_contrib = self.atomic_weights[element] * ratio
                total_weight += weight_contrib

                # Track heavy elements (atomic weight > 50)
                if self.atomic_weights[element] > 50:
                    heavy_element_fraction += weight_contrib

            heavy_element_fraction /= total_weight

            # Simplified density estimation using empirical rules
            if heavy_element_fraction > 0.5:
                if 'Bi' in elements:
                    estimated_density = 2.5 + heavy_element_fraction * 5
                elif any(elem in elements for elem in ['W', 'Au', 'Hf']):
                    estimated_density = 3.0 + heavy_element_fraction * 10
                else:
                    estimated_density = 2.0 + heavy_element_fraction * 3
            else:
                if any(elem in elements for elem in ['Al', 'Si', 'Ti']):
                    estimated_density = 1.2 + heavy_element_fraction * 2
                else:
                    estimated_density = 1.0 + heavy_element_fraction

            # Show results with option to use
            result_msg = f"Estimated Density: {estimated_density:.2f} g/cm³\n"
            result_msg += f"Molecular Weight: {total_weight:.1f} g/mol\n"
            result_msg += f"Heavy Element Fraction: {heavy_element_fraction*100:.1f}%\n\n"
            result_msg += "Apply this density?"

            reply = QMessageBox.question(self, "Density Estimation", result_msg,
                                         QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.density_spin.setValue(estimated_density)

        except Exception as e:
            QMessageBox.critical(self, "Estimation Error", f"Error estimating density: {str(e)}")
        finally:
            self.estimate_density_button.set_working(False)

    def add_element_to_composition(self):
        """Add selected element to composition"""
        element = self.element_combo.currentText()
        ratio = self.ratio_spin.value()

        current = self.composition_edit.text().strip()
        if current:
            new_composition = f"{current},{element}:{ratio}"
        else:
            new_composition = f"{element}:{ratio}"

        self.composition_edit.setText(new_composition)

    def validate_composition(self):
        """Validate current composition"""
        composition = self.composition_edit.text()
        elements = self.parse_composition(composition)

        self.validate_composition_button.set_working(True, "Validating...")

        try:
            if not elements:
                QMessageBox.warning(self, "Validation", "❌ Invalid composition format")
                return

            # Check for unknown elements
            unknown = [elem for elem in elements.keys() if elem not in self.atomic_weights]

            if unknown:
                supported = ', '.join(self.atomic_weights.keys())
                QMessageBox.warning(self, "Validation",
                                    f"❌ Unknown elements: {', '.join(unknown)}\n\n"
                                    f"Supported elements:\n{supported}")
            else:
                total_atoms = sum(elements.values())
                molecular_weight = sum(self.atomic_weights[elem] * ratio
                                       for elem, ratio in elements.items())

                QMessageBox.information(self, "Validation",
                                        f"✅ Valid composition!\n\n"
                                        f"Elements: {len(elements)}\n"
                                        f"Total atoms: {total_atoms:.2f}\n"
                                        f"Molecular weight: {molecular_weight:.1f} g/mol")
        finally:
            self.validate_composition_button.set_working(False)

    def clear_composition(self):
        """Clear composition field"""
        self.composition_edit.clear()

    def on_composition_changed(self):
        """Handle composition text changes"""
        composition = self.composition_edit.text()
        elements = self.parse_composition(composition)

        if elements:
            # Quick analysis for display
            total_atoms = sum(elements.values())
            total_weight = sum(self.atomic_weights.get(elem, 0) * ratio
                               for elem, ratio in elements.items())

            analysis_text = f"Formula: {composition} | "
            analysis_text += f"MW: {total_weight:.1f} g/mol | "
            analysis_text += f"Atoms: {total_atoms:.1f}"

            # Identify material type
            metals = ['Al', 'Ti', 'Zr', 'Hf', 'Bi', 'W', 'Au']
            has_metals = any(elem in metals for elem in elements.keys())
            has_carbon = 'C' in elements

            if has_metals and has_carbon:
                material_type = "Metal-Organic"
            elif has_carbon:
                material_type = "Organic"
            else:
                material_type = "Inorganic"

            analysis_text += f" | Type: {material_type}"
            self.analysis_text.setText(analysis_text)
        else:
            self.analysis_text.setText("")

    def on_material_changed(self):
        """Handle material selection change"""
        material = self.material_combo.currentText()
        if material in self.material_presets:
            composition, density = self.material_presets[material]
            self.composition_edit.setText(composition)
            self.density_spin.setValue(density)

            # Enable/disable composition editing
            self.composition_edit.setReadOnly(material != "Custom")

    # Continuing with the remaining methods...
    # [The methods would continue here, including the BEAMER conversion methods,
    #  simulation methods, file handling, etc. Due to length limits, I'll continue
    #  in the next part]

    # ===================================================================
    # CONSOLIDATED BEAMER CONVERSION METHODS (Main Window)
    # ===================================================================

    def convert_psf_to_beamer_main(self):
        """Main window BEAMER conversion - consolidated approach"""
        # Check if we have recent simulation data
        recent_files = self.file_manager.get_recent_simulation_files()
        psf_files = [f for f in recent_files if 'psf' in f.name.lower() and f.suffix == '.csv']

        if psf_files:
            # Ask user to choose recent file or browse
            reply = QMessageBox.question(self, "Convert to BEAMER",
                                         f"Convert the most recent PSF simulation to BEAMER format?\n\n"
                                         f"File: {psf_files[0].name}\n\n"
                                         f"Choose 'Yes' for recent file, 'No' to browse, 'Cancel' to abort.",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

            if reply == QMessageBox.Yes:
                self._do_beamer_conversion_main(str(psf_files[0]))
            elif reply == QMessageBox.No:
                self._browse_and_convert_beamer()
        else:
            # No recent files, ask user to browse
            self._browse_and_convert_beamer()

    def _browse_and_convert_beamer(self):
        """Browse for PSF file and convert to BEAMER"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PSF Data", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )
        if file_path:
            self._do_beamer_conversion_main(file_path)

    def _do_beamer_conversion_main(self, csv_file):
        """Perform BEAMER conversion with progress indication"""
        # Show progress in status bar
        self.file_status_label.setText("🔄 Converting to BEAMER...")
        self.file_status_label.setVisible(True)

        try:
            # Load CSV data using file manager
            df, message = self.file_manager.load_csv_with_validation(
                csv_file,
                progress_callback=lambda msg: self.file_status_label.setText(f"🔄 {msg}")
            )

            if df is None:
                QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                return

            # Get beam energy from current settings
            beam_energy = self.energy_spin.value()

            # Ask about smoothing
            smooth_reply = QMessageBox.question(self, "Smoothing Options",
                                                "Apply Savitzky-Golay smoothing to reduce noise in tail region?\n\n"
                                                "Recommended for noisy simulations with statistical fluctuations.",
                                                QMessageBox.Yes | QMessageBox.No)
            apply_smoothing = (smooth_reply == QMessageBox.Yes)

            # Update status
            self.file_status_label.setText("🔄 Processing PSF data...")

            # Convert using the plot widget's consolidated method
            result = self.plot_widget._convert_csv_to_beamer_consolidated(
                df, beam_energy, apply_smoothing
            )

            if result:
                output_radius, output_psf, alpha, beta = result

                # Ask for save location
                default_name = Path(csv_file).stem + "_beamer.txt"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save BEAMER Format", default_name,
                    "Text files (*.txt);;All files (*.*)"
                )

                if file_path:
                    # Update status
                    self.file_status_label.setText("🔄 Saving BEAMER file...")

                    # Write BEAMER format using plot widget method
                    success, save_message = self.plot_widget._write_beamer_file(
                        file_path, output_radius, output_psf, csv_file, beam_energy
                    )

                    if success:
                        # Show success with comprehensive information
                        success_msg = QMessageBox(self)
                        success_msg.setWindowTitle("BEAMER Conversion Complete")
                        success_msg.setText(f"PSF successfully converted to BEAMER format!")
                        success_msg.setInformativeText(
                            f"File: {Path(file_path).name}\n\n"
                            f"Energy split (not the Gaussian α/β ranges):\n"
                            f"forward fraction (r < 1 μm): {alpha:.3f}\n"
                            f"backscatter fraction (r > 1 μm): {beta:.3f}\n\n"
                            f"Data points: {len(output_radius)}\n"
                            f"Radius range: {output_radius[0]:.3f} - {output_radius[-1]:.3f} μm"
                        )
                        success_msg.setStandardButtons(QMessageBox.Ok)
                        preview_button = success_msg.addButton("Preview Plot", QMessageBox.ActionRole)
                        success_msg.exec()

                        if success_msg.clickedButton() == preview_button:
                            # Switch to 1D plot tab and show BEAMER format
                            self.tab_widget.setCurrentIndex(4)  # 1D visualization
                            self.plot_widget.plot_beamer_format(output_radius, output_psf)

                        # Update status
                        self.status_label.setText(f"BEAMER conversion completed: {Path(file_path).name}")
                    else:
                        QMessageBox.critical(self, "Save Error", f"Failed to save BEAMER file: {save_message}")
            else:
                QMessageBox.critical(self, "Conversion Error", "Failed to convert PSF data to BEAMER format")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"BEAMER conversion failed: {str(e)}")
        finally:
            self.file_status_label.setVisible(False)

    def batch_convert_beamer_main(self):
        """Batch convert multiple PSF files to BEAMER format"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PSF Files for Batch Conversion", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_paths:
            # Ask for output directory
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", str(self.file_manager.working_dir)
            )

            if output_dir:
                # Show progress bar for batch operation
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, len(file_paths))
                self.progress_bar.setValue(0)

                success_count = 0
                beam_energy = self.energy_spin.value()

                for i, file_path in enumerate(file_paths):
                    self.progress_bar.setValue(i)
                    self.file_status_label.setText(f"🔄 Converting {Path(file_path).name}...")
                    self.file_status_label.setVisible(True)

                    # Allow GUI to update
                    QApplication.processEvents()

                    try:
                        df, message = self.file_manager.load_csv_with_validation(file_path)

                        if df is not None:
                            result = self.plot_widget._convert_csv_to_beamer_consolidated(
                                df, beam_energy, True  # Apply smoothing by default for batch
                            )

                            if result:
                                output_radius, output_psf, alpha, beta = result

                                # Generate output filename
                                output_name = Path(file_path).stem + "_beamer.txt"
                                output_path = Path(output_dir) / output_name

                                # Write file
                                success, _ = self.plot_widget._write_beamer_file(
                                    str(output_path), output_radius, output_psf,
                                    file_path, beam_energy
                                )

                                if success:
                                    success_count += 1

                    except Exception as e:
                        self.log_output(f"Error converting {file_path}: {str(e)}")

                # Complete batch operation
                self.progress_bar.setValue(len(file_paths))
                self.progress_bar.setVisible(False)
                self.file_status_label.setVisible(False)

                QMessageBox.information(self, "Batch Conversion Complete",
                                        f"Successfully converted {success_count}/{len(file_paths)} files to BEAMER format.\n\n"
                                        f"Output directory: {output_dir}")

    def validate_psf_data_main(self):
        """Main window PSF validation"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PSF Data to Validate", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            self.file_status_label.setText("🔄 Validating PSF data...")
            self.file_status_label.setVisible(True)

            try:
                # Load and validate using file manager
                df, message = self.file_manager.load_csv_with_validation(file_path)

                if df is None:
                    QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                    return

                # Use plot widget's comprehensive validation
                report = self.plot_widget._validate_psf_comprehensive(df, Path(file_path).name)

                # Show validation report
                dialog = QMessageBox(self)
                dialog.setWindowTitle("PSF Validation Report")
                dialog.setText(report)
                dialog.setIcon(QMessageBox.Information)
                dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Save)
                dialog.setDetailedText(
                    "Comprehensive validation includes:\n"
                    "• Data integrity checks\n"
                    "• Monotonicity analysis\n"
                    "• Statistical quality assessment\n"
                    "• Physical parameter validation\n"
                    "• Energy conservation check"
                )

                result = dialog.exec()

                if result == QMessageBox.Save:
                    # Save validation report
                    save_path, _ = QFileDialog.getSaveFileName(
                        self, "Save Validation Report",
                        Path(file_path).stem + "_validation.txt",
                        "Text files (*.txt);;All files (*.*)"
                    )

                    if save_path:
                        with open(save_path, 'w') as f:
                            f.write(report)
                        QMessageBox.information(self, "Success", f"Validation report saved to {save_path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"PSF validation failed: {str(e)}")
            finally:
                self.file_status_label.setVisible(False)

    def compare_beamer_files_main(self):
        """Compare multiple BEAMER format files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select BEAMER Files to Compare", "",
            "Text files (*.txt);;Data files (*.dat);;All files (*.*)"
        )

        if len(file_paths) >= 2:
            # Switch to 1D plot tab for comparison
            self.tab_widget.setCurrentIndex(4)

            # Clear existing plots
            self.plot_widget.figure.clear()
            ax = self.plot_widget.figure.add_subplot(111)

            colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

            # Collect all data for dynamic axis calculation
            all_radii = []
            all_psf = []

            # Load and plot each BEAMER file
            for i, file_path in enumerate(file_paths):
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
                        color = colors[i % len(colors)]
                        ax.loglog(radius, psf, linewidth=2, color=color,
                                  label=Path(file_path).stem)

                        # Collect for axis limit calculation
                        all_radii.extend(radius)
                        all_psf.extend(psf)

                except Exception as e:
                    self.log_output(f"Error loading {file_path}: {str(e)}")

            # Format plot in BEAMER style with dynamic limits
            ax.set_xlabel('radius, μm')
            ax.set_ylabel('relative energy deposition')
            ax.set_title('BEAMER PSF Comparison')

            # Calculate optimal limits from all loaded data
            if all_radii and all_psf:
                x_min, x_max, y_min, y_max = self.plot_widget._calculate_optimal_axis_limits(
                    all_radii, all_psf
                )
                ax.set_xlim(x_min, x_max)
                ax.set_ylim(y_min, y_max)
            else:
                # Fallback to defaults if no data
                ax.set_xlim(0.01, 100)
                ax.set_ylim(1e-10, 2)
            ax.grid(True, which="both", ls="-", alpha=0.2)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            self.plot_widget.figure.tight_layout()
            self.plot_widget.canvas.draw()

            QMessageBox.information(self, "Comparison Complete",
                                    f"Loaded and compared {len(file_paths)} BEAMER files.\n\n"
                                    "Check the 1D Visualization tab for the comparison plot.")
        else:
            QMessageBox.warning(self, "Insufficient Files",
                                "Please select at least 2 BEAMER files for comparison.")

    # ===================================================================
    # ENHANCED UTILITY METHODS
    # ===================================================================

    def open_psf_comparison(self):
        """Open PSF comparison tool"""
        # Switch to 1D visualization tab which has comparison features
        self.tab_widget.setCurrentIndex(4)
        QMessageBox.information(self, "PSF Comparison Tool",
                                "Use the '1D PSF Visualization' tab for PSF comparison:\n\n"
                                "1. Load initial PSF with 'Load PSF Data'\n"
                                "2. Add more datasets with 'Add for Comparison'\n"
                                "3. Use 'Analyze Comparison' for detailed analysis\n"
                                "4. Switch plot types to see different views")

    def show_recent_files(self):
        """Show recent simulation files"""
        recent_files = self.file_manager.get_recent_simulation_files()

        if recent_files:
            file_list = "\n".join([f"• {f.name} ({f.stat().st_size // 1024} KB)"
                                   for f in recent_files[:10]])
            QMessageBox.information(self, "Recent Simulation Files",
                                    f"Recent files in working directory:\n\n{file_list}\n\n"
                                    f"Working directory: {self.file_manager.working_dir}")
        else:
            QMessageBox.information(self, "No Recent Files",
                                    f"No recent simulation files found.\n\n"
                                    f"Working directory: {self.file_manager.working_dir}")

    def filter_log_messages(self):
        """Filter log messages based on selection"""
        # This would filter the output text based on the combo selection
        # Implementation would depend on how we want to store and filter messages
        filter_type = self.filter_combo.currentText()
        self.status_label.setText(f"Log filter: {filter_type}")

    # ===================================================================
    # SIMULATION AND FILE MANAGEMENT
    # ===================================================================

    def generate_output_filename(self, base_name="ebl", extension=".csv", include_timestamp=False, run_number=None):
        """Generate dynamic filename based on simulation parameters"""
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

    def generate_macro(self):
        """Generate Geant4 macro file with optimized settings"""
        try:
            # Ensure the working directory exists
            Path(self.working_dir).mkdir(parents=True, exist_ok=True)

            # Show progress
            self.generate_button.set_working(True, "Generating...")

            # Generate base filename pattern
            base_pattern = self.generate_output_filename(extension="")

            # Find next run number if auto-increment is enabled
            run_number = None
            if self.auto_increment_check.isChecked():
                run_number = self.find_next_run_number(base_pattern)

            # Add timestamp if requested
            use_timestamp = self.timestamp_check.isChecked()

            # Generate output filenames
            if hasattr(self, 'pattern_mode_check') and self.pattern_mode_check.isChecked():
                # Pattern mode uses different output files
                dose_filename = self.generate_output_filename("pattern_dose", ".csv",
                                                             include_timestamp=use_timestamp,
                                                             run_number=run_number)
                dose2d_filename = self.generate_output_filename("pattern_dose_2d", ".csv",
                                                               include_timestamp=use_timestamp,
                                                               run_number=run_number)
                summary_filename = self.generate_output_filename("pattern_summary", ".txt",
                                                                include_timestamp=use_timestamp,
                                                                run_number=run_number)
                # No BEAMER format for pattern mode
                psf_filename = dose_filename  # For compatibility
                psf2d_filename = dose2d_filename
                beamer_filename = ""
            else:
                # PSF mode filenames
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
            
            # Calculate number of events
            if hasattr(self, 'pattern_mode_check') and self.pattern_mode_check.isChecked():
                # For pattern mode, calculate total events needed
                pattern_size = self.pattern_size_spin.value()  # nm
                shot_pitch = self.shot_pitch_spin.value()  # nm
                
                # Number of points in pattern
                points_per_side = int(pattern_size / shot_pitch)
                total_points = points_per_side * points_per_side
                
                # Get electrons per point from dwell time display
                if hasattr(self, 'electrons_per_point_label'):
                    # Extract number from label like "Electrons/point: 1234"
                    epd_text = self.electrons_per_point_label.text()
                    if ":" in epd_text:
                        electrons_per_point = int(epd_text.split(":")[1].strip())
                    else:
                        electrons_per_point = 1000  # Default
                else:
                    electrons_per_point = 1000  # Default
                
                num_events = total_points * electrons_per_point
                self.log_output(f"Pattern mode: {total_points} points × {electrons_per_point} e⁻/point = {num_events:,} events")
            else:
                num_events = self.events_spin.value()

            # Remembered so run_simulation can size the progress bar and tell
            # the worker the exact event count (pattern mode != events_spin)
            self.current_num_events = num_events

            with open(macro_path, 'w') as f:
                f.write("# EBL Simulation Macro - Generated by Enhanced GUI v3.1\n")
                f.write(f"# {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Events: {num_events:,}\n\n")

                # Add output filename commands
                f.write("# Output file configuration\n")
                f.write(f"/ebl/output/setDirectory {self.working_dir}\n")
                f.write(f"/ebl/output/setPSFFile {psf_filename}\n")
                f.write(f"/ebl/output/setPSF2DFile {psf2d_filename}\n")
                f.write(f"/ebl/output/setSummaryFile {summary_filename}\n")
                # Only write BEAMER file command if filename is not empty
                if beamer_filename:
                    f.write(f"/ebl/output/setBeamerFile {beamer_filename}\n")
                f.write("\n")

                # Optimized verbosity for large simulations
                if num_events <= 10000:
                    verbose_level = min(self.verbose_spin.value(), 2)
                elif num_events <= 100000:
                    verbose_level = min(self.verbose_spin.value(), 1)
                else:
                    verbose_level = 0

                f.write(f"/run/verbose {verbose_level}\n")
                f.write(f"/event/verbose {max(0, verbose_level-1)}\n")
                f.write(f"/tracking/verbose 0\n\n")

                # Performance optimizations for large simulations
                if num_events > 100000:
                    f.write("# Performance optimizations for large simulation\n")
                    f.write("/control/cout/ignoreThreadsExcept 0\n")
                    f.write("/run/printProgress 0\n")
                    f.write("# Using custom progress reporting for better GUI integration\n\n")

                # Random seed handling
                if self.seed_spin.value() == -1:
                    random_seed = random.randint(1, 2147483647)
                    f.write(f"/random/setSeeds {random_seed} {random_seed+1}\n")
                    f.write(f"# Auto-generated random seed: {random_seed}\n\n")
                    self.last_used_seed = random_seed
                elif self.seed_spin.value() > 0:
                    f.write(f"/random/setSeeds {self.seed_spin.value()} {self.seed_spin.value()+1}\n\n")

                # Material settings BEFORE initialize (avoids double geometry build)
                # Setting material before /run/initialize means geometry is built once
                # with the correct composition, rather than building with default then rebuilding
                f.write("# Material settings (before init for efficiency)\n")
                f.write(f'/det/setResistComposition "{self.composition_edit.text()}"\n')
                f.write(f"/det/setResistThickness {self.thickness_spin.value()} nm\n")
                f.write(f"/det/setResistDensity {self.density_spin.value()} g/cm3\n\n")

                # Initialize (geometry built once with correct material)
                f.write("# Initialize\n")
                f.write("/run/initialize\n\n")

                # Physics processes
                f.write("# Physics processes\n")
                f.write(f"/process/em/fluo {1 if self.fluorescence_check.isChecked() else 0}\n")
                f.write(f"/process/em/auger {1 if self.auger_check.isChecked() else 0}\n\n")

                # Check if pattern mode is enabled
                if hasattr(self, 'pattern_mode_check') and self.pattern_mode_check.isChecked():
                    # Pattern mode configuration
                    f.write("# Pattern exposure mode\n")
                    f.write("/pattern/enable true\n")
                    
                    # Pattern type
                    pattern_type = self.pattern_type_combo.currentText().lower().replace(" ", "_")
                    f.write(f"/pattern/type {pattern_type}\n")
                    
                    # JEOL mode
                    jeol_mode = "mode3" if self.mode3_radio.isChecked() else "mode6"
                    f.write(f"/pattern/jeolMode {jeol_mode}\n")
                    
                    # Pattern parameters
                    f.write(f"/pattern/shotPitch {self.shot_pitch_spin.value()}\n")
                    f.write(f"/pattern/size {self.pattern_size_spin.value()} nm\n")
                    f.write(f"/pattern/center {self.pattern_x_spin.value()} {self.pattern_y_spin.value()} 0 nm\n")
                    
                    # Extract beam current value from combo box (e.g., "2 nA" -> 2.0)
                    beam_current_text = self.beam_current_combo.currentText()
                    beam_current = float(beam_current_text.split()[0])
                    f.write(f"/pattern/beamCurrent {beam_current} nA\n")
                    
                    f.write(f"/pattern/dose {self.dose_spin.value()}\n")
                    f.write("/pattern/generate\n\n")
                    
                    # Initialize dose grid based on pattern size and resolution
                    pattern_size = self.pattern_size_spin.value()
                    grid_nx = self.grid_nx_spin.value()
                    grid_ny = self.grid_ny_spin.value()
                    grid_nz = self.grid_nz_spin.value()
                    
                    # Grid bounds: pattern size + margin for scattering
                    margin = pattern_size * 0.5  # 50% margin
                    x_min = self.pattern_x_spin.value() - pattern_size/2 - margin
                    x_max = self.pattern_x_spin.value() + pattern_size/2 + margin
                    y_min = self.pattern_y_spin.value() - pattern_size/2 - margin
                    y_max = self.pattern_y_spin.value() + pattern_size/2 + margin
                    z_min = 0
                    z_max = self.thickness_spin.value()  # Resist thickness
                    
                    f.write("# Dose grid initialization\n")
                    f.write(f"/data/initDoseGrid {grid_nx} {grid_ny} {grid_nz} "
                           f"{x_min} {x_max} {y_min} {y_max} {z_min} {z_max} nm\n\n")
                
                # Beam configuration
                f.write("# Beam configuration\n")
                f.write("/gun/particle e-\n")
                f.write(f"/gun/energy {self.energy_spin.value()} keV\n")

                # For pattern mode, position is set by pattern generator
                # Note: Z position is now dynamically calculated (1nm above resist surface)
                # Only write X,Y position; let C++ handle Z for optimal positioning
                if not (hasattr(self, 'pattern_mode_check') and self.pattern_mode_check.isChecked()):
                    # Only set position if X or Y is non-zero (centered beam is default)
                    if self.pos_x_spin.value() != 0.0 or self.pos_y_spin.value() != 0.0:
                        f.write(f"/gun/position {self.pos_x_spin.value()} {self.pos_y_spin.value()} 0 nm\n")

                # Normalize direction
                dx, dy, dz = self.dir_x_spin.value(), self.dir_y_spin.value(), self.dir_z_spin.value()
                length = (dx*dx + dy*dy + dz*dz)**0.5
                if length > 0:
                    dx, dy, dz = dx/length, dy/length, dz/length
                else:
                    dx, dy, dz = 0, 0, -1

                f.write(f"/gun/direction {dx} {dy} {dz}\n")
                # Point source (0nm) is default for PSF; BEAMER handles beam blur separately
                f.write(f"/gun/beamSize {self.beam_size_spin.value()} nm\n\n")

                # Visualization (only for small simulations)
                if self.visualization_check.isChecked() and num_events <= 1000:
                    f.write("# Visualization\n")
                    f.write("/vis/open OGL\n")
                    f.write("/vis/drawVolume\n")
                    f.write("/vis/scene/add/trajectories smooth\n\n")
                elif self.visualization_check.isChecked():
                    f.write("# Visualization disabled for large simulation\n\n")

                # Run simulation
                f.write("# Run simulation\n")
                f.write(f"/run/beamOn {num_events}\n")

            self.log_output(f"Enhanced macro generated: {macro_path}")
            self.log_output(f"Target events: {num_events:,}")
            if num_events > 100000:
                self.log_output("Large simulation detected - using optimized settings")

            self.status_label.setText("Macro generated successfully")
            return str(macro_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate macro: {str(e)}")
            return None
        finally:
            self.generate_button.set_working(False)

    def run_simulation(self):
        """Start simulation with enhanced progress tracking and comprehensive validation"""
        if self.simulation_running:
            QMessageBox.information(self, "Info", "Simulation is already running")
            return

        # Comprehensive validation before simulation
        beam_params = {
            'energy': self.energy_spin.value(),
            'beam_size': self.beam_size_spin.value(),
            'pos_z': self.pos_z_spin.value(),
            'dir_z': self.dir_z_spin.value()
        }

        material_params = {
            'composition': self.composition_edit.text(),
            'thickness': self.thickness_spin.value(),
            'density': self.density_spin.value()
        }

        sim_params = {
            'events': self.events_spin.value(),
            'seed': self.seed_spin.value()
        }

        file_params = {
            'executable_path': self.executable_path,
            'working_dir': self.working_dir,
            'geant4_path': self.geant4_path
        }

        is_valid, validation_errors = SimulationValidator.validate_all(
            beam_params, material_params, sim_params, file_params
        )

        if validation_errors:
            # Show validation report
            report = SimulationValidator.format_validation_report(validation_errors)

            if not is_valid:
                # Has errors - cannot run
                QMessageBox.critical(
                    self,
                    "Validation Failed",
                    f"Cannot run simulation due to validation errors:\n\n{report}"
                )
                return
            else:
                # Only warnings - ask user
                reply = QMessageBox.question(
                    self,
                    "Validation Warnings",
                    f"{report}\n\nDo you want to proceed anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

        # Validate inputs (additional large simulation warning)
        if self.events_spin.value() > 1000000:
            reply = QMessageBox.question(
                self, "Large Simulation Warning",
                f"Running {self.events_spin.value():,} events may take a very long time.\n\n"
                f"Large simulations (>1M events) use optimized settings:\n"
                f"• Reduced console output\n"
                f"• Custom progress reporting\n"
                f"• Performance optimizations\n\n"
                f"Continue with simulation?",
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
                                     f"Build it from the project root:\n"
                                     f"  mkdir -p build && cd build\n"
                                     f"  cmake .. -DCMAKE_BUILD_TYPE=Release\n"
                                     f"  make -j8\n\n"
                                     f"Or select an existing binary via File > Select Executable")
                return

        # Setup simulation UI state
        self.clear_log()
        self.simulation_running = True
        self.run_button.set_working(True, "Running...")
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        total_events = getattr(self, 'current_num_events', None) or self.events_spin.value()
        self.progress_bar.setRange(0, total_events)
        self.progress_bar.setValue(0)

        # Switch to output tab
        self.tab_widget.setCurrentIndex(3)

        # Create worker thread
        self.simulation_thread = QThread()
        self.simulation_worker = SimulationWorker(self.executable_path, macro_path, self.working_dir,
                                                  self.geant4_path, expected_events=total_events)
        self.simulation_worker.moveToThread(self.simulation_thread)

        # Connect signals with UniqueConnection to prevent duplicates
        self.simulation_worker.output.connect(self.log_output, Qt.UniqueConnection)
        self.simulation_worker.progress.connect(self.update_progress, Qt.UniqueConnection)
        self.simulation_worker.finished.connect(self.simulation_finished, Qt.UniqueConnection)
        self.simulation_thread.started.connect(self.simulation_worker.run_simulation, Qt.UniqueConnection)

        # Start thread
        self.simulation_thread.start()
        self.log_output("Enhanced simulation started...")
        self.status_label.setText("Simulation running...")

    def stop_simulation(self):
        """Stop simulation"""
        if self.simulation_worker:
            self.simulation_worker.stop()
            self.log_output("Stopping simulation...")

    def simulation_finished(self, success, message):
        """Handle simulation completion with enhanced file loading and proper cleanup"""
        self.simulation_running = False
        self.run_button.set_working(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)

        self.log_output(message)
        self.status_label.setText(message)

        # Disconnect signals to prevent memory leaks
        if self.simulation_worker:
            try:
                self.simulation_worker.output.disconnect(self.log_output)
                self.simulation_worker.progress.disconnect(self.update_progress)
                self.simulation_worker.finished.disconnect(self.simulation_finished)
            except (TypeError, RuntimeError):
                # Signals may already be disconnected
                pass

        if self.simulation_thread:
            try:
                self.simulation_thread.started.disconnect(self.simulation_worker.run_simulation)
            except (TypeError, RuntimeError):
                pass

            self.simulation_thread.quit()
            self.simulation_thread.wait()

        if success:
            # Enhanced success handling with better file detection
            available_files = []

            empty_files = []
            if hasattr(self, 'current_output_files'):
                # Check generated files (0-byte files count as failures, not results)
                for file_type, file_path in self.current_output_files.items():
                    if Path(file_path).exists():
                        file_size = Path(file_path).stat().st_size
                        if file_size == 0:
                            empty_files.append(Path(file_path).name)
                        else:
                            available_files.append(f"{file_type.upper()}: {Path(file_path).name} ({file_size//1024} KB)")

            if empty_files:
                self.log_output(f"[WARNING] Empty output files: {', '.join(empty_files)}")

            if available_files:
                reply = QMessageBox.question(
                    self, "Simulation Complete!",
                    f"Simulation completed successfully!\n\n"
                    f"Output directory:\n{self.working_dir}\n\n"
                    f"Generated files:\n• " + "\n• ".join(available_files) +
                    (f"\n\nWarning - empty files: {', '.join(empty_files)}" if empty_files else "") +
                    f"\n\nWould you like to automatically load and visualize the results?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self._auto_load_simulation_results()
            else:
                QMessageBox.information(self, "Simulation Complete",
                                        f"Simulation completed, but no usable output files were detected in:\n"
                                        f"{self.working_dir}\n\n"
                                        "Check the Output Log tab for errors or warnings.")
        else:
            QMessageBox.warning(self, "Simulation Failed",
                                f"Simulation did not complete successfully.\n\n{message}")

    def _auto_load_simulation_results(self):
        """Automatically load simulation results with enhanced error handling"""
        try:
            if hasattr(self, 'current_output_files'):
                psf_file = self.current_output_files.get('psf')
                psf2d_file = self.current_output_files.get('psf2d')
                summary_file = self.current_output_files.get('summary')

                # Load 1D PSF if available
                if psf_file and Path(psf_file).exists():
                    self.tab_widget.setCurrentIndex(4)  # 1D visualization tab
                    QTimer.singleShot(500, lambda: self.auto_load_1d(psf_file))

                # Load 2D data if available
                if psf2d_file and Path(psf2d_file).exists():
                    QTimer.singleShot(1000, lambda: self.auto_load_2d(psf2d_file))

                # Load summary if available
                if summary_file and Path(summary_file).exists():
                    QTimer.singleShot(1500, lambda: self.auto_load_summary(summary_file))

        except Exception as e:
            self.log_output(f"Error auto-loading results: {str(e)}")

    def auto_load_1d(self, file_path):
        """Auto-load 1D PSF data with error handling"""
        try:
            df, message = self.file_manager.load_csv_with_validation(file_path)

            if df is not None:
                # Extract PSF data
                radii, energies = self.plot_widget._extract_psf_from_df(df)

                if radii and energies:
                    # Clear existing data and load new
                    self.plot_widget.datasets = []
                    self.plot_widget.current_csv_path = file_path

                    dataset_info = {
                        'radii': radii,
                        'energies': energies,
                        'label': f"PSF - {Path(file_path).stem}",
                        'file_path': file_path,
                        'style': {'color': 'blue', 'linewidth': 2}
                    }
                    self.plot_widget.datasets.append(dataset_info)

                    # Update UI and plot
                    self.plot_widget.beamer_button.set_status(True)
                    self.plot_widget.validate_button.set_status(True)
                    self.plot_widget.save_button.set_status(True)
                    self.plot_widget.compare_button.set_status(True)
                    self.plot_widget.clear_button.set_status(True)

                    self.plot_widget.plot_all_datasets()
                    self.plot_widget.update_comparison_list()

                    self.status_label.setText("1D PSF data loaded successfully")
                else:
                    self.log_output(f"[WARNING] No PSF data rows found in {Path(file_path).name}")
                    QMessageBox.warning(self, "Empty PSF Data",
                                        f"The PSF file contains no data rows:\n{file_path}\n\n"
                                        "The simulation may have recorded no energy deposits. "
                                        "Check the Output Log tab.")
            else:
                self.log_output(f"[WARNING] Could not load PSF CSV: {message}")
                QMessageBox.warning(self, "PSF Load Failed",
                                    f"Could not load PSF data:\n{file_path}\n\n{message}")

        except Exception as e:
            self.log_output(f"Error auto-loading 1D data: {str(e)}")

    def auto_load_2d(self, file_path):
        """Auto-load 2D data with enhanced error handling and debugging"""
        try:
            self.tab_widget.setCurrentIndex(5)  # 2D visualization tab

            # Check if file exists and has content
            if not Path(file_path).exists():
                self.log_output(f"❌ 2D file not found: {file_path}")
                return

            file_size = Path(file_path).stat().st_size
            self.log_output(f"📊 Loading 2D data from: {Path(file_path).name} ({file_size} bytes)")

            if file_size < 100:  # Very small file, likely empty
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if "No 2D data collected" in content:
                        self.log_output("⚠️ No 2D data was collected during simulation")
                        return

            # Load CSV with explicit index column
            df = pd.read_csv(file_path, index_col=0)

            if df.empty:
                self.log_output("❌ 2D CSV file is empty")
                return

            self.log_output(f"✅ 2D data shape: {df.shape[0]} depths × {df.shape[1]} radii")

            # Extract data
            depths = df.index.values.astype(float)  # Depth values (nm)
            radii = df.columns.astype(float).values  # Radius values (nm)
            data = df.values.astype(float)  # Energy data (eV)

            # Check for valid data
            non_zero_count = np.count_nonzero(data)
            total_energy = np.sum(data)

            self.log_output(f"📈 2D data stats: {non_zero_count} non-zero bins, total: {total_energy:.2e} eV")

            if non_zero_count == 0:
                self.log_output("⚠️ 2D data contains no energy deposits")
                return

            # Store the data in the 2D plot widget
            self.plot_2d_widget.current_data = {
                'depths': depths,
                'radii': radii,
                'energy': data,
                'filename': Path(file_path).stem
            }

            # Update UI controls
            self.plot_2d_widget.depth_slider.setMaximum(len(depths) - 1)
            self.plot_2d_widget.depth_slider.setValue(len(depths) // 2)  # Start in middle
            self.plot_2d_widget.save_plot_button.set_status(True)
            self.plot_2d_widget.export_button.set_status(True)

            # Plot the data
            self.plot_2d_widget.plot_2d_data()

            self.status_label.setText("2D data loaded successfully")
            self.log_output("✅ 2D visualization ready - check the 2D Visualization tab")

        except Exception as e:
            error_msg = f"❌ Error auto-loading 2D data: {str(e)}"
            self.log_output(error_msg)

            # Try to provide more specific error information
            try:
                with open(file_path, 'r') as f:
                    first_lines = [f.readline().strip() for _ in range(3)]
                    self.log_output(f"📄 File preview: {first_lines}")
            except:
                pass

    def auto_load_summary(self, file_path):
        """Auto-load simulation summary"""
        try:
            with open(file_path, 'r') as f:
                summary_text = f.read()

            # Show summary in output log (since we removed analysis tab)
            self.log_output("=== SIMULATION SUMMARY ===")
            for line in summary_text.split('\n'):
                if line.strip():
                    self.log_output(line)
            self.log_output("=== END SUMMARY ===")

            self.status_label.setText("Summary loaded in output log")

        except Exception as e:
            self.log_output(f"Error auto-loading summary: {str(e)}")

    def update_progress(self, event_num):
        """Update progress bar and status"""
        self.progress_bar.setValue(event_num)
        progress = (event_num / self.events_spin.value()) * 100
        self.status_label.setText(f"Simulation: {event_num:,}/{self.events_spin.value():,} ({progress:.1f}%)")

    def log_output(self, message):
        """Add message to output log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.output_text.appendPlainText(f"[{timestamp}] {message}")

        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

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
                success, message = self.file_manager.save_with_backup(
                    self.output_text.toPlainText(), file_path, backup=False
                )

                if success:
                    QMessageBox.information(self, "Success", f"Log saved to {file_path}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to save log: {message}")
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
                    with open(macro_path, 'r') as src:
                        content = src.read()

                    success, message = self.file_manager.save_with_backup(content, file_path)

                    if success:
                        QMessageBox.information(self, "Success", f"Macro saved to {file_path}")
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to save macro: {message}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save macro: {str(e)}")

    def select_executable(self):
        """Select executable file"""
        import platform
        if platform.system() == "Windows":
            file_filter = "Executable files (*.exe);;All files (*.*)"
        else:
            file_filter = "All files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select EBL Executable",
            str(Path(self.executable_path).parent) if self.executable_path else "",
            file_filter
        )

        if file_path:
            self.executable_path = file_path
            # working_dir (output location) intentionally unchanged: outputs
            # stay in the repo's output/ dir, not the binary's directory
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
                    self.beam_size_spin.setValue(config['beam'].get('size', 0.0))  # Point source default
                    self.pos_x_spin.setValue(config['beam'].get('pos_x', 0.0))
                    self.pos_y_spin.setValue(config['beam'].get('pos_y', 0.0))
                    # Note: Z position is now dynamic (1nm above resist), this is just for override
                    self.pos_z_spin.setValue(config['beam'].get('pos_z', 0.0))
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
                success, message = self.file_manager.save_with_backup(
                    json.dumps(config, indent=2), file_path
                )

                if success:
                    QMessageBox.information(self, "Success", f"Configuration saved to {file_path}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to save configuration: {message}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

    def show_about(self):
        """Enhanced about dialog"""
        QMessageBox.about(self, "About EBL Simulation GUI",
                          """<h3>EBL Simulation GUI v3.1 Enhanced Edition</h3>
                  <p>A comprehensive GUI for Geant4-based electron beam lithography simulations with advanced analysis tools.</p>
                  
                  <p><b>✨ New in v3.1 Enhanced:</b></p>
                  <ul>
                    <li>🔧 Consolidated BEAMER PSF format conversion</li>
                    <li>📊 Advanced PSF comparison and analysis tools</li>
                    <li>🎯 Enhanced PSF validation with comprehensive checks</li>
                    <li>🔄 Unified file management system</li>
                    <li>⚡ Optimized performance for large simulations (>1M events)</li>
                    <li>🎨 Improved UI with status-aware buttons and progress indicators</li>
                    <li>🐛 Fixed 2D contour plotting issues</li>
                    <li>🧹 Removed placeholder functionality for cleaner interface</li>
                  </ul>
                  
                  <p><b>🔬 Core Features:</b></p>
                  <ul>
                    <li>2D depth-radius energy deposition visualization</li>
                    <li>XPS-validated material compositions (Alucone, Biscone)</li>
                    <li>Real-time simulation monitoring with adaptive progress tracking</li>
                    <li>Multi-format data export (BEAMER, NumPy, MATLAB)</li>
                    <li>Comprehensive proximity effect parameter calculation</li>
                    <li>Batch processing capabilities</li>
                    <li>Smart material property estimation</li>
                  </ul>
                  
                  <p><b>🔬 Research Applications:</b></p>
                  <ul>
                    <li>Electron beam lithography process optimization</li>
                    <li>Proximity effect correction for commercial EBL tools</li>
                    <li>Novel resist material characterization</li>
                    <li>Multi-layer resist stack analysis</li>
                  </ul>
                  
                  <p><i>Based on experimental data from TMA + 2-butyne-1,4-diol MLD process.<br>
                  Developed for advanced EBL research and industrial applications.</i></p>
                  
                  <p><b>Support:</b> Check the Help menu for BEAMER format guide and usage tips.</p>
                  """)

    def show_shortcuts_help(self):
        """Show keyboard shortcuts help dialog"""
        shortcuts_text = """
<h3>⌨️  Keyboard Shortcuts</h3>

<h4>File Operations:</h4>
<table cellpadding="5">
<tr><td><b>Ctrl+O</b></td><td>Load Configuration</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save Configuration</td></tr>
<tr><td><b>Ctrl+M</b></td><td>Save Macro</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Select Executable</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Exit Application</td></tr>
</table>

<h4>Simulation:</h4>
<table cellpadding="5">
<tr><td><b>Ctrl+R</b></td><td>Run Simulation</td></tr>
<tr><td><b>Ctrl+G</b></td><td>Generate Macro</td></tr>
<tr><td><b>Esc</b></td><td>Stop Simulation</td></tr>
</table>

<h4>Tools:</h4>
<table cellpadding="5">
<tr><td><b>Ctrl+,</b></td><td>Settings</td></tr>
<tr><td><b>Ctrl+P</b></td><td>PSF Comparison Tool</td></tr>
<tr><td><b>Ctrl+H</b></td><td>Recent Simulation Files</td></tr>
</table>

<h4>Navigation:</h4>
<table cellpadding="5">
<tr><td><b>Ctrl+1-9</b></td><td>Switch to Tab 1-9</td></tr>
<tr><td><b>Ctrl+Tab</b></td><td>Next Tab</td></tr>
<tr><td><b>Ctrl+Shift+Tab</b></td><td>Previous Tab</td></tr>
</table>

<h4>Help:</h4>
<table cellpadding="5">
<tr><td><b>F1</b></td><td>Show This Help</td></tr>
</table>

<p><i>Tip: Menu items show their shortcuts next to the command.</i></p>
        """

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.setText(shortcuts_text)
        dialog.setIcon(QMessageBox.Information)
        dialog.exec()

    def show_beamer_help(self):
        """Enhanced BEAMER format help dialog"""
        help_text = """
<h3>🎯 BEAMER PSF Format Guide</h3>

<h4>📋 Format Requirements:</h4>
<ul>
<li><b>Normalization:</b> Maximum value = 1.0 (peak normalized, not area)</li>
<li><b>Units:</b> Radius in micrometers (μm), PSF dimensionless</li>
<li><b>Range:</b> Typically 0.01 to 100 μm (covers 99%+ of scattered electrons)</li>
<li><b>Spacing:</b> Logarithmic or dense linear spacing recommended</li>
<li><b>Format:</b> ASCII text, two columns: radius PSF_value</li>
</ul>

<h4>📄 File Structure:</h4>
<pre>
# Electron beam PSF for BEAMER proximity correction
# Generated from Geant4 simulation by EBL GUI
# Source: ebl_psf_E100keV_beam2.0nm_resist30nm.csv
# Beam energy: 100 keV
# Format: radius(um) relative_energy_deposition
#
0.01000    0.98765
0.01500    0.95432
0.02234    0.89123
...
100.000    1.234e-9
</pre>

<h4>⚖️ Proximity Effect Parameters:</h4>
<ul>
<li><b>α (alpha):</b> Forward scatter fraction (r < 1 μm)<br>
    <i>Typical values: 0.6-0.8 for thin resists</i></li>
<li><b>β (beta):</b> Backscatter fraction (r > 1 μm)<br>
    <i>β = 1 - α, represents long-range scattering</i></li>
<li><b>η (eta):</b> Characteristic backscatter range [μm]<br>
    <i>Automatically calculated from PSF tail analysis</i></li>
</ul>

<h4>✅ Quality Assurance:</h4>
<ul>
<li><b>Smoothness:</b> Use Savitzky-Golay filtering for noisy tail regions</li>
<li><b>Continuity:</b> No sudden jumps or artificial cutoffs</li>
<li><b>Monotonicity:</b> Generally decreasing after initial peak</li>
<li><b>Coverage:</b> Extends to capture 99%+ of deposited energy</li>
<li><b>Validation:</b> R50 and R90 values should be physically reasonable</li>
</ul>

<h4>🔧 Conversion Process:</h4>
<ol>
<li><b>Load PSF data:</b> From Geant4 simulation (CSV format)</li>
<li><b>Normalize:</b> Peak value set to 1.0</li>
<li><b>Filter (optional):</b> Apply smoothing to reduce statistical noise</li>
<li><b>Extrapolate:</b> Extend tail to 100 μm using exponential fit</li>
<li><b>Validate:</b> Check physical parameters and data quality</li>
<li><b>Export:</b> Save in BEAMER-compatible ASCII format</li>
</ol>

<h4>🚨 Common Issues & Solutions:</h4>
<ul>
<li><b>Noisy tail region:</b> ✅ Enable smoothing during conversion</li>
<li><b>Truncated data:</b> ✅ Automatic extrapolation applied</li>
<li><b>Wrong normalization:</b> ✅ Ensure max = 1.0, not integral = 1.0</li>
<li><b>Missing near-field:</b> ✅ Auto-adds point at 0.01 μm if needed</li>
<li><b>Discontinuities:</b> ✅ Use validation tool to check data quality</li>
</ul>

<h4>📊 Using in BEAMER:</h4>
<ol>
<li>Import PSF file using BEAMER's proximity correction setup</li>
<li>Verify parameters (α, β, η) match simulation results</li>
<li>Test on calibration patterns before production use</li>
<li>Consider material-specific and energy-dependent effects</li>
</ol>

<p><i>💡 <b>Pro Tip:</b> Compare multiple PSF files using the comparison tool to 
study parameter dependencies (energy, material, thickness).</i></p>
"""

        dialog = QMessageBox(self)
        dialog.setWindowTitle("BEAMER Format Help")
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(help_text)
        dialog.setIcon(QMessageBox.Information)
        dialog.exec()

    def load_settings(self):
        """Load application settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        exe_path = self.settings.value("executable_path")
        if exe_path and Path(exe_path).exists():
            self.executable_path = exe_path
            # working_dir (output location) intentionally left at output/

    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("executable_path", self.executable_path)
        if self.geant4_path:
            self.settings.setValue("geant4_path", str(self.geant4_path))

    def _initialize_geant4_path(self):
        """Initialize Geant4 path from settings or auto-detect"""
        # Try to load from settings first
        saved_path = self.settings.value("geant4_path")
        if saved_path:
            path = Path(saved_path)
            detector = Geant4PathDetector()
            if detector.validate_geant4_path(path):
                self.geant4_path = path
                return

        # If no valid saved path, try auto-detection
        detector = Geant4PathDetector()
        detected_path = detector.detect_geant4_path()
        if detected_path:
            self.geant4_path = detected_path
            # Save for next time
            self.settings.setValue("geant4_path", str(detected_path))

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.geant4_path)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, settings):
        """Handle settings changes"""
        if 'geant4_path' in settings:
            self.geant4_path = settings['geant4_path']
            self.settings.setValue("geant4_path", str(self.geant4_path))
            self.statusBar().showMessage(f"Geant4 path updated: {self.geant4_path}", 3000)

    def closeEvent(self, event):
        """Handle window close event with proper thread cleanup"""
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

                # Wait for thread to finish properly
                if self.simulation_thread and self.simulation_thread.isRunning():
                    self.statusBar().showMessage("Waiting for simulation to stop...")

                    # Try graceful shutdown first
                    if not self.simulation_thread.wait(const.THREAD_WAIT_TIMEOUT):
                        # If still running, force termination
                        self.simulation_thread.terminate()
                        if not self.simulation_thread.wait(const.THREAD_TERMINATE_TIMEOUT):
                            self.statusBar().showMessage("Warning: Force-quitting simulation thread")

        event.accept()


def main():
    """Enhanced main function with better error handling"""
    # Fix for WSL2/X11 - Force Qt to use X11 instead of Wayland
    # Detect WSL2 and set appropriate Qt platform
    if platform.system() == 'Linux' and 'microsoft' in platform.uname().release.lower():
        os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("EBL Simulation GUI")
    app.setApplicationVersion("3.1 Enhanced")
    app.setOrganizationName("EBL Research")

    try:
        # Create and show the main window
        window = EBLMainWindow()
        window.show()

        # Log startup
        window.log_output("=== EBL Simulation GUI v3.1 Enhanced Started ===")
        window.log_output("Features: Consolidated BEAMER conversion, PSF comparison, Enhanced UI")

        sys.exit(app.exec())

    except Exception as e:
        QMessageBox.critical(None, "Startup Error",
                             f"Failed to start application:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()