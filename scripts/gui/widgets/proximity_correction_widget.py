"""
Proximity Effect Correction Widget
Models dose correction strategies to compensate for proximity effects
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
                              QTableWidget, QTableWidgetItem, QGroupBox,
                              QCheckBox, QMessageBox, QHeaderView, QTextEdit,
                              QSlider, QRadioButton, QButtonGroup, QTabWidget,
                              QFileDialog, QProgressBar)
from PySide6.QtCore import Qt, Signal, QThread, pyqtSignal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle, Circle
import numpy as np
import pandas as pd
from pathlib import Path
import json
from datetime import datetime


class ProximityCorrectionWidget(QWidget):
    """Widget for proximity effect correction modeling and simulation"""
    
    # Signals
    correction_applied = Signal(dict)  # Emits corrected pattern data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.patterns = []
        self.correction_model = None
        self.corrected_doses = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different correction approaches
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Add tabs
        self.setup_dose_modulation_tab()
        self.setup_shape_correction_tab()
        self.setup_analysis_tab()
        self.setup_simulation_tab()
        
    def setup_dose_modulation_tab(self):
        """Setup dose modulation correction tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Pattern loading section
        pattern_group = QGroupBox("Pattern Configuration")
        pattern_layout = QVBoxLayout()
        
        # File loading
        file_layout = QHBoxLayout()
        self.pattern_file_label = QLabel("No pattern file loaded")
        self.load_pattern_button = QPushButton("Load Pattern File")
        self.load_pattern_button.clicked.connect(self.load_pattern_file)
        file_layout.addWidget(self.pattern_file_label)
        file_layout.addWidget(self.load_pattern_button)
        pattern_layout.addLayout(file_layout)
        
        # Manual pattern definition
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Or define patterns manually:"))
        
        self.add_rect_button = QPushButton("Add Rectangle")
        self.add_rect_button.clicked.connect(self.add_rectangle_pattern)
        manual_layout.addWidget(self.add_rect_button)
        
        self.add_line_button = QPushButton("Add Line")
        self.add_line_button.clicked.connect(self.add_line_pattern)
        manual_layout.addWidget(self.add_line_button)
        
        self.clear_patterns_button = QPushButton("Clear All")
        self.clear_patterns_button.clicked.connect(self.clear_patterns)
        manual_layout.addWidget(self.clear_patterns_button)
        
        manual_layout.addStretch()
        pattern_layout.addLayout(manual_layout)
        
        # Pattern table
        self.pattern_table = QTableWidget()
        self.pattern_table.setColumnCount(6)
        self.pattern_table.setHorizontalHeaderLabels([
            "Type", "Size/Length", "Width", "Center X", "Center Y", "Action"
        ])
        pattern_layout.addWidget(self.pattern_table)
        
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)
        
        # Correction parameters
        correction_group = QGroupBox("Proximity Correction Parameters")
        correction_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Correction Model:"))
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "Gaussian Dual Beam (α/β)",
            "Exponential Decay",
            "Polynomial Fit",
            "Look-up Table",
            "Custom Function"
        ])
        self.model_combo.currentTextChanged.connect(self.update_model_parameters)
        model_layout.addWidget(self.model_combo)
        
        model_layout.addWidget(QLabel("Resist Type:"))
        self.resist_combo = QComboBox()
        self.resist_combo.addItems([
            "PMMA (positive)",
            "HSQ (negative)", 
            "ZEP (positive)",
            "ma-N (negative)",
            "Custom"
        ])
        self.resist_combo.currentTextChanged.connect(self.update_resist_parameters)
        model_layout.addWidget(self.resist_combo)
        
        model_layout.addStretch()
        correction_layout.addLayout(model_layout)
        
        # Model parameters
        param_layout = QHBoxLayout()
        
        # Forward scattering
        param_layout.addWidget(QLabel("Forward α:"))
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.001, 1.0)
        self.alpha_spin.setValue(0.1)
        self.alpha_spin.setDecimals(3)
        self.alpha_spin.setToolTip("Forward scattering range (µm)")
        param_layout.addWidget(self.alpha_spin)
        
        # Backscattering 
        param_layout.addWidget(QLabel("Backscatter β:"))
        self.beta_spin = QDoubleSpinBox()
        self.beta_spin.setRange(0.1, 50.0)
        self.beta_spin.setValue(5.0)
        self.beta_spin.setDecimals(1)
        self.beta_spin.setToolTip("Backscattering range (µm)")
        param_layout.addWidget(self.beta_spin)
        
        # Backscatter ratio
        param_layout.addWidget(QLabel("η ratio:"))
        self.eta_spin = QDoubleSpinBox()
        self.eta_spin.setRange(0.0, 2.0)
        self.eta_spin.setValue(0.5)
        self.eta_spin.setDecimals(2)
        self.eta_spin.setToolTip("Backscatter to forward scattering ratio")
        param_layout.addWidget(self.eta_spin)
        
        param_layout.addStretch()
        correction_layout.addLayout(param_layout)
        
        # Dose parameters
        dose_layout = QHBoxLayout()
        
        dose_layout.addWidget(QLabel("Base Dose:"))
        self.base_dose_spin = QSpinBox()
        self.base_dose_spin.setRange(100, 50000)
        self.base_dose_spin.setValue(3000)
        self.base_dose_spin.setSuffix(" µC/cm²")
        dose_layout.addWidget(self.base_dose_spin)
        
        dose_layout.addWidget(QLabel("Max Correction:"))
        self.max_correction_spin = QDoubleSpinBox()
        self.max_correction_spin.setRange(0.1, 10.0)
        self.max_correction_spin.setValue(3.0)
        self.max_correction_spin.setDecimals(1)
        self.max_correction_spin.setToolTip("Maximum dose correction factor")
        dose_layout.addWidget(self.max_correction_spin)
        
        dose_layout.addWidget(QLabel("Threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(100, 20000)
        self.threshold_spin.setValue(2500)
        self.threshold_spin.setSuffix(" µC/cm²")
        self.threshold_spin.setToolTip("Target development threshold")
        dose_layout.addWidget(self.threshold_spin)
        
        dose_layout.addStretch()
        correction_layout.addLayout(dose_layout)
        
        correction_group.setLayout(correction_layout)
        layout.addWidget(correction_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.calculate_correction_button = QPushButton("Calculate Dose Corrections")
        self.calculate_correction_button.clicked.connect(self.calculate_dose_corrections)
        self.calculate_correction_button.setStyleSheet("QPushButton { font-weight: bold; }")
        button_layout.addWidget(self.calculate_correction_button)
        
        self.preview_button = QPushButton("Preview Correction")
        self.preview_button.clicked.connect(self.preview_corrections)
        button_layout.addWidget(self.preview_button)
        
        self.export_button = QPushButton("Export Corrected Pattern")
        self.export_button.clicked.connect(self.export_corrected_pattern)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(100)
        self.results_text.setPlaceholderText("Correction results will appear here...")
        layout.addWidget(self.results_text)
        
        self.tab_widget.addTab(tab, "Dose Modulation")
        
    def setup_shape_correction_tab(self):
        """Setup shape-based correction tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Shape correction methods
        method_group = QGroupBox("Shape Correction Methods")
        method_layout = QVBoxLayout()
        
        # Method selection
        self.shape_method_group = QButtonGroup()
        
        self.bias_radio = QRadioButton("Size Biasing")
        self.bias_radio.setChecked(True)
        self.bias_radio.setToolTip("Adjust pattern sizes to compensate for broadening")
        self.shape_method_group.addButton(self.bias_radio, 0)
        method_layout.addWidget(self.bias_radio)
        
        self.serif_radio = QRadioButton("Serif Addition")
        self.serif_radio.setToolTip("Add serif structures to maintain sharp corners")
        self.shape_method_group.addButton(self.serif_radio, 1)
        method_layout.addWidget(self.serif_radio)
        
        self.ghost_radio = QRadioButton("Ghost Features")
        self.ghost_radio.setToolTip("Add sub-resolution features for local dose control")
        self.shape_method_group.addButton(self.ghost_radio, 2)
        method_layout.addWidget(self.ghost_radio)
        
        # Parameters for each method
        self.shape_params_widget = QWidget()
        shape_params_layout = QVBoxLayout(self.shape_params_widget)
        
        # Size biasing parameters
        bias_layout = QHBoxLayout()
        bias_layout.addWidget(QLabel("Bias Amount:"))
        self.bias_amount_spin = QDoubleSpinBox()
        self.bias_amount_spin.setRange(-50.0, 50.0)
        self.bias_amount_spin.setValue(-5.0)
        self.bias_amount_spin.setSuffix(" nm")
        self.bias_amount_spin.setToolTip("Negative values shrink patterns")
        bias_layout.addWidget(self.bias_amount_spin)
        
        bias_layout.addWidget(QLabel("Proximity Factor:"))
        self.proximity_factor_spin = QDoubleSpinBox()
        self.proximity_factor_spin.setRange(0.0, 2.0)
        self.proximity_factor_spin.setValue(0.8)
        self.proximity_factor_spin.setDecimals(2)
        bias_layout.addWidget(self.proximity_factor_spin)
        
        bias_layout.addStretch()
        shape_params_layout.addLayout(bias_layout)
        
        method_layout.addWidget(self.shape_params_widget)
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # Pattern preview
        preview_group = QGroupBox("Shape Correction Preview")
        preview_layout = QVBoxLayout()
        
        # Matplotlib figure for shape preview
        self.shape_figure = Figure(figsize=(10, 6))
        self.shape_canvas = FigureCanvas(self.shape_figure)
        preview_layout.addWidget(self.shape_canvas)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, 1)
        
        # Control buttons
        shape_button_layout = QHBoxLayout()
        
        self.apply_shape_correction_button = QPushButton("Apply Shape Corrections")
        self.apply_shape_correction_button.clicked.connect(self.apply_shape_corrections)
        shape_button_layout.addWidget(self.apply_shape_correction_button)
        
        self.reset_shapes_button = QPushButton("Reset to Original")
        self.reset_shapes_button.clicked.connect(self.reset_shapes)
        shape_button_layout.addWidget(self.reset_shapes_button)
        
        shape_button_layout.addStretch()
        layout.addLayout(shape_button_layout)
        
        self.tab_widget.addTab(tab, "Shape Correction")
        
    def setup_analysis_tab(self):
        """Setup correction analysis and comparison tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Analysis controls
        analysis_group = QGroupBox("Correction Analysis")
        analysis_layout = QHBoxLayout()
        
        analysis_layout.addWidget(QLabel("Analysis Type:"))
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "Before/After Comparison",
            "Dose Uniformity",
            "Critical Dimension Control",
            "Proximity Error Map",
            "Process Window Analysis"
        ])
        analysis_layout.addWidget(self.analysis_combo)
        
        self.run_analysis_button = QPushButton("Run Analysis")
        self.run_analysis_button.clicked.connect(self.run_correction_analysis)
        analysis_layout.addWidget(self.run_analysis_button)
        
        analysis_layout.addStretch()
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        # Analysis results
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        # Matplotlib figure for analysis plots
        self.analysis_figure = Figure(figsize=(12, 8))
        self.analysis_canvas = FigureCanvas(self.analysis_figure)
        results_layout.addWidget(self.analysis_canvas)
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(120)
        results_layout.addWidget(self.stats_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group, 1)
        
        self.tab_widget.addTab(tab, "Analysis")
        
    def setup_simulation_tab(self):
        """Setup simulation with corrections tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Simulation setup
        sim_group = QGroupBox("Simulation with Corrections")
        sim_layout = QVBoxLayout()
        
        # Simulation parameters
        param_layout = QHBoxLayout()
        
        param_layout.addWidget(QLabel("Grid Resolution:"))
        self.grid_resolution_spin = QSpinBox()
        self.grid_resolution_spin.setRange(50, 1000)
        self.grid_resolution_spin.setValue(200)
        self.grid_resolution_spin.setToolTip("Grid points per dimension")
        param_layout.addWidget(self.grid_resolution_spin)
        
        param_layout.addWidget(QLabel("Field Size:"))
        self.field_size_spin = QSpinBox()
        self.field_size_spin.setRange(500, 10000)
        self.field_size_spin.setValue(2000)
        self.field_size_spin.setSuffix(" nm")
        param_layout.addWidget(self.field_size_spin)
        
        param_layout.addWidget(QLabel("Z Layers:"))
        self.z_layers_spin = QSpinBox()
        self.z_layers_spin.setRange(1, 50)
        self.z_layers_spin.setValue(10)
        param_layout.addWidget(self.z_layers_spin)
        
        param_layout.addStretch()
        sim_layout.addLayout(param_layout)
        
        # Output options
        output_layout = QHBoxLayout()
        
        self.generate_original_check = QCheckBox("Generate Original (Uncorrected)")
        self.generate_original_check.setChecked(True)
        output_layout.addWidget(self.generate_original_check)
        
        self.generate_corrected_check = QCheckBox("Generate Corrected")
        self.generate_corrected_check.setChecked(True)
        output_layout.addWidget(self.generate_corrected_check)
        
        self.generate_difference_check = QCheckBox("Generate Difference Map")
        self.generate_difference_check.setChecked(True)
        output_layout.addWidget(self.generate_difference_check)
        
        output_layout.addStretch()
        sim_layout.addLayout(output_layout)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # Progress and status
        progress_group = QGroupBox("Simulation Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to simulate")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Control buttons
        sim_button_layout = QHBoxLayout()
        
        self.run_simulation_button = QPushButton("Run Proximity Correction Simulation")
        self.run_simulation_button.clicked.connect(self.run_correction_simulation)
        self.run_simulation_button.setStyleSheet("QPushButton { font-weight: bold; background-color: #4CAF50; }")
        sim_button_layout.addWidget(self.run_simulation_button)
        
        self.stop_simulation_button = QPushButton("Stop")
        self.stop_simulation_button.setEnabled(False)
        sim_button_layout.addWidget(self.stop_simulation_button)
        
        sim_button_layout.addStretch()
        layout.addLayout(sim_button_layout)
        
        # Results visualization
        vis_group = QGroupBox("Simulation Results")
        vis_layout = QVBoxLayout()
        
        # View controls
        view_layout = QHBoxLayout()
        view_layout.addWidget(QLabel("View:"))
        
        self.view_combo = QComboBox()
        self.view_combo.addItems([
            "Original Pattern",
            "Corrected Pattern", 
            "Side-by-Side Comparison",
            "Difference Map",
            "Line Profiles"
        ])
        self.view_combo.currentTextChanged.connect(self.update_simulation_view)
        view_layout.addWidget(self.view_combo)
        
        view_layout.addStretch()
        vis_layout.addLayout(view_layout)
        
        # Matplotlib figure for simulation results
        self.sim_figure = Figure(figsize=(12, 8))
        self.sim_canvas = FigureCanvas(self.sim_figure)
        vis_layout.addWidget(self.sim_canvas)
        
        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group, 1)
        
        self.tab_widget.addTab(tab, "Simulation")
        
    def load_pattern_file(self):
        """Load pattern file (GDS, DXF, or JSON)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Pattern File",
            "",
            "Pattern Files (*.gds *.dxf *.json);;All Files (*)"
        )
        
        if file_path:
            try:
                # For now, assume JSON format with pattern definitions
                with open(file_path, 'r') as f:
                    pattern_data = json.load(f)
                
                self.patterns = pattern_data.get('patterns', [])
                self.pattern_file_label.setText(Path(file_path).name)
                self.update_pattern_table()
                self.results_text.append(f"Loaded {len(self.patterns)} patterns from {Path(file_path).name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load pattern file:\n{str(e)}")
                
    def add_rectangle_pattern(self):
        """Add a rectangular pattern"""
        pattern = {
            'type': 'rectangle',
            'width': 100,  # nm
            'height': 100,  # nm
            'center': [0, 0],  # nm
            'dose_factor': 1.0
        }
        self.patterns.append(pattern)
        self.update_pattern_table()
        
    def add_line_pattern(self):
        """Add a line pattern"""
        pattern = {
            'type': 'line',
            'length': 500,  # nm
            'width': 20,    # nm
            'center': [0, 0],  # nm
            'dose_factor': 1.0
        }
        self.patterns.append(pattern)
        self.update_pattern_table()
        
    def clear_patterns(self):
        """Clear all patterns"""
        self.patterns.clear()
        self.corrected_doses.clear()
        self.update_pattern_table()
        
    def update_pattern_table(self):
        """Update the pattern table display"""
        self.pattern_table.setRowCount(len(self.patterns))
        
        for i, pattern in enumerate(self.patterns):
            self.pattern_table.setItem(i, 0, QTableWidgetItem(pattern['type']))
            
            if pattern['type'] == 'rectangle':
                size_str = f"{pattern['width']}×{pattern['height']}"
                width_str = "-"
            else:  # line
                size_str = str(pattern['length'])
                width_str = str(pattern['width'])
                
            self.pattern_table.setItem(i, 1, QTableWidgetItem(size_str))
            self.pattern_table.setItem(i, 2, QTableWidgetItem(width_str))
            self.pattern_table.setItem(i, 3, QTableWidgetItem(str(pattern['center'][0])))
            self.pattern_table.setItem(i, 4, QTableWidgetItem(str(pattern['center'][1])))
            
            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, idx=i: self.remove_pattern(idx))
            self.pattern_table.setCellWidget(i, 5, remove_btn)
            
    def remove_pattern(self, index):
        """Remove a pattern from the list"""
        if 0 <= index < len(self.patterns):
            self.patterns.pop(index)
            if index in self.corrected_doses:
                del self.corrected_doses[index]
            self.update_pattern_table()
            
    def update_model_parameters(self, model_name):
        """Update model parameters based on selection"""
        # Set typical values for different models
        if model_name == "Gaussian Dual Beam (α/β)":
            self.alpha_spin.setValue(0.01)  # 10 nm
            self.beta_spin.setValue(2.0)    # 2 µm
            self.eta_spin.setValue(0.5)
        elif model_name == "Exponential Decay":
            self.alpha_spin.setValue(0.02) 
            self.beta_spin.setValue(3.0)
            self.eta_spin.setValue(0.6)
            
    def update_resist_parameters(self, resist_type):
        """Update parameters based on resist type"""
        resist_params = {
            "PMMA (positive)": {"threshold": 2500, "base_dose": 3000},
            "HSQ (negative)": {"threshold": 1500, "base_dose": 2000},
            "ZEP (positive)": {"threshold": 1800, "base_dose": 2500},
            "ma-N (negative)": {"threshold": 1200, "base_dose": 1800}
        }
        
        if resist_type in resist_params:
            params = resist_params[resist_type]
            self.threshold_spin.setValue(params["threshold"])
            self.base_dose_spin.setValue(params["base_dose"])
            
    def calculate_dose_corrections(self):
        """Calculate dose corrections for all patterns"""
        if not self.patterns:
            QMessageBox.warning(self, "No Patterns", "Add patterns first")
            return
            
        self.results_text.clear()
        self.results_text.append("Calculating proximity effect corrections...")
        
        # Get correction parameters
        alpha = self.alpha_spin.value()  # µm
        beta = self.beta_spin.value()    # µm  
        eta = self.eta_spin.value()
        base_dose = self.base_dose_spin.value()
        threshold = self.threshold_spin.value()
        
        # Calculate correction for each pattern
        self.corrected_doses = {}
        
        for i, pattern in enumerate(self.patterns):
            # Simplified proximity correction calculation
            # In practice, this would involve convolution with PSF
            
            # Estimate local dose from other patterns
            proximity_dose = 0
            center = np.array(pattern['center'])
            
            for j, other_pattern in enumerate(self.patterns):
                if i == j:
                    continue
                    
                other_center = np.array(other_pattern['center'])
                distance = np.linalg.norm(center - other_center) / 1000  # convert to µm
                
                # Simple exponential backscatter model
                if distance > 0:
                    backscatter_contrib = eta * base_dose * np.exp(-distance / beta)
                    proximity_dose += backscatter_contrib
                    
            # Calculate required dose correction
            total_background = proximity_dose
            required_primary = threshold - total_background
            
            if required_primary > 0:
                dose_factor = required_primary / base_dose
                dose_factor = min(dose_factor, self.max_correction_spin.value())
                dose_factor = max(dose_factor, 1.0 / self.max_correction_spin.value())
            else:
                dose_factor = 1.0 / self.max_correction_spin.value()  # Minimum dose
                
            self.corrected_doses[i] = {
                'dose_factor': dose_factor,
                'corrected_dose': base_dose * dose_factor,
                'proximity_dose': proximity_dose,
                'total_dose': base_dose * dose_factor + proximity_dose
            }
            
            self.results_text.append(
                f"Pattern {i+1}: Factor={dose_factor:.2f}, "
                f"Dose={base_dose * dose_factor:.0f} µC/cm², "
                f"Proximity={proximity_dose:.0f} µC/cm²"
            )
            
        self.results_text.append("\nDose correction calculation complete.")
        
    def preview_corrections(self):
        """Preview the dose corrections visually"""
        if not self.corrected_doses:
            self.calculate_dose_corrections()
            
        # Create visualization in the analysis tab
        self.tab_widget.setCurrentIndex(2)  # Switch to analysis tab
        self.analysis_combo.setCurrentText("Before/After Comparison")
        self.run_correction_analysis()
        
    def export_corrected_pattern(self):
        """Export corrected pattern with dose modifications"""
        if not self.corrected_doses:
            QMessageBox.warning(self, "No Corrections", "Calculate corrections first")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Corrected Pattern",
            "corrected_pattern.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Prepare export data
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'correction_parameters': {
                        'model': self.model_combo.currentText(),
                        'alpha': self.alpha_spin.value(),
                        'beta': self.beta_spin.value(),
                        'eta': self.eta_spin.value(),
                        'base_dose': self.base_dose_spin.value(),
                        'threshold': self.threshold_spin.value()
                    },
                    'patterns': []
                }
                
                for i, pattern in enumerate(self.patterns):
                    corrected_pattern = pattern.copy()
                    if i in self.corrected_doses:
                        corrected_pattern.update(self.corrected_doses[i])
                    export_data['patterns'].append(corrected_pattern)
                    
                if file_path.endswith('.json'):
                    with open(file_path, 'w') as f:
                        json.dump(export_data, f, indent=2)
                else:  # CSV
                    # Create CSV with pattern data
                    df_data = []
                    for i, pattern in enumerate(self.patterns):
                        row = {
                            'pattern_id': i,
                            'type': pattern['type'],
                            'center_x': pattern['center'][0],
                            'center_y': pattern['center'][1],
                        }
                        if pattern['type'] == 'rectangle':
                            row['width'] = pattern['width']
                            row['height'] = pattern['height']
                        else:
                            row['length'] = pattern['length']
                            row['width'] = pattern['width']
                            
                        if i in self.corrected_doses:
                            row.update(self.corrected_doses[i])
                            
                        df_data.append(row)
                        
                    df = pd.DataFrame(df_data)
                    df.to_csv(file_path, index=False)
                    
                QMessageBox.information(self, "Exported", f"Corrected patterns saved to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")
                
    def apply_shape_corrections(self):
        """Apply shape-based corrections"""
        if not self.patterns:
            QMessageBox.warning(self, "No Patterns", "Add patterns first")
            return
            
        method_id = self.shape_method_group.checkedId()
        
        if method_id == 0:  # Size biasing
            bias = self.bias_amount_spin.value()  # nm
            proximity_factor = self.proximity_factor_spin.value()
            
            for pattern in self.patterns:
                if pattern['type'] == 'rectangle':
                    pattern['width'] += bias * proximity_factor
                    pattern['height'] += bias * proximity_factor
                    # Ensure minimum size
                    pattern['width'] = max(10, pattern['width'])
                    pattern['height'] = max(10, pattern['height'])
                elif pattern['type'] == 'line':
                    pattern['width'] += bias * proximity_factor
                    pattern['width'] = max(5, pattern['width'])
                    
        self.update_pattern_table()
        self.update_shape_preview()
        
    def reset_shapes(self):
        """Reset shapes to original"""
        # This would restore from a backup of original patterns
        # For now, just update the preview
        self.update_shape_preview()
        
    def update_shape_preview(self):
        """Update the shape correction preview"""
        if not self.patterns:
            return
            
        self.shape_figure.clear()
        ax = self.shape_figure.add_subplot(111)
        
        # Plot original and corrected shapes
        for i, pattern in enumerate(self.patterns):
            center = pattern['center']
            
            if pattern['type'] == 'rectangle':
                w, h = pattern['width'], pattern['height']
                rect = Rectangle((center[0] - w/2, center[1] - h/2), w, h,
                               fill=False, edgecolor='blue', linewidth=2,
                               label='Corrected' if i == 0 else "")
                ax.add_patch(rect)
                
                # Show original (assuming 5nm bias removed)
                orig_w, orig_h = w + 5, h + 5
                orig_rect = Rectangle((center[0] - orig_w/2, center[1] - orig_h/2), 
                                    orig_w, orig_h, fill=False, edgecolor='red', 
                                    linewidth=1, linestyle='--',
                                    label='Original' if i == 0 else "")
                ax.add_patch(orig_rect)
                
            elif pattern['type'] == 'line':
                length, width = pattern['length'], pattern['width']
                # Draw as rectangle for visualization
                rect = Rectangle((center[0] - length/2, center[1] - width/2), 
                               length, width, fill=False, edgecolor='blue', 
                               linewidth=2)
                ax.add_patch(rect)
                
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_title('Shape Correction Preview')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        # Auto-scale to show all patterns
        if self.patterns:
            all_x = [p['center'][0] for p in self.patterns]
            all_y = [p['center'][1] for p in self.patterns]
            margin = 200
            ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
            ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
            
        self.shape_canvas.draw()
        
    def run_correction_analysis(self):
        """Run correction analysis and display results"""
        analysis_type = self.analysis_combo.currentText()
        
        if not self.corrected_doses and analysis_type != "Process Window Analysis":
            QMessageBox.warning(self, "No Corrections", "Calculate corrections first")
            return
            
        self.analysis_figure.clear()
        
        if analysis_type == "Before/After Comparison":
            self.plot_before_after_comparison()
        elif analysis_type == "Dose Uniformity":
            self.plot_dose_uniformity()
        elif analysis_type == "Critical Dimension Control":
            self.plot_cd_control()
        elif analysis_type == "Proximity Error Map":
            self.plot_proximity_error_map()
        elif analysis_type == "Process Window Analysis":
            self.plot_process_window()
            
        self.analysis_canvas.draw()
        
    def plot_before_after_comparison(self):
        """Plot before/after dose comparison"""
        if not self.corrected_doses:
            return
            
        ax1 = self.analysis_figure.add_subplot(121)
        ax2 = self.analysis_figure.add_subplot(122)
        
        base_dose = self.base_dose_spin.value()
        
        # Before correction
        pattern_ids = list(range(len(self.patterns)))
        original_doses = [base_dose] * len(self.patterns)
        
        ax1.bar(pattern_ids, original_doses, color='red', alpha=0.7)
        ax1.set_xlabel('Pattern ID')
        ax1.set_ylabel('Dose [µC/cm²]')
        ax1.set_title('Before Correction (Uniform Dose)')
        ax1.grid(True, alpha=0.3)
        
        # After correction
        corrected_dose_values = []
        total_dose_values = []
        
        for i in pattern_ids:
            if i in self.corrected_doses:
                corrected_dose_values.append(self.corrected_doses[i]['corrected_dose'])
                total_dose_values.append(self.corrected_doses[i]['total_dose'])
            else:
                corrected_dose_values.append(base_dose)
                total_dose_values.append(base_dose)
                
        ax2.bar(pattern_ids, corrected_dose_values, color='blue', alpha=0.7, 
               label='Primary Dose')
        ax2.bar(pattern_ids, [td - cd for td, cd in zip(total_dose_values, corrected_dose_values)],
               bottom=corrected_dose_values, color='orange', alpha=0.7, 
               label='Proximity Dose')
        
        threshold = self.threshold_spin.value()
        ax2.axhline(y=threshold, color='green', linestyle='--', linewidth=2,
                   label=f'Target ({threshold} µC/cm²)')
        
        ax2.set_xlabel('Pattern ID')
        ax2.set_ylabel('Dose [µC/cm²]')
        ax2.set_title('After Correction')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        self.analysis_figure.tight_layout()
        
        # Update statistics
        dose_uniformity = np.std(total_dose_values) / np.mean(total_dose_values) * 100
        self.stats_text.clear()
        self.stats_text.append(f"Dose Uniformity (CV): {dose_uniformity:.1f}%")
        self.stats_text.append(f"Mean Total Dose: {np.mean(total_dose_values):.0f} µC/cm²")
        self.stats_text.append(f"Target Dose: {threshold} µC/cm²")
        self.stats_text.append(f"Dose Range: {min(total_dose_values):.0f} - {max(total_dose_values):.0f} µC/cm²")
        
    def plot_dose_uniformity(self):
        """Plot dose uniformity analysis"""
        # Implementation for dose uniformity visualization
        ax = self.analysis_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Dose Uniformity Analysis\n(Implementation in progress)', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        
    def plot_cd_control(self):
        """Plot critical dimension control analysis"""
        # Implementation for CD control visualization  
        ax = self.analysis_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Critical Dimension Control\n(Implementation in progress)', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        
    def plot_proximity_error_map(self):
        """Plot proximity error map"""
        # Implementation for proximity error visualization
        ax = self.analysis_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Proximity Error Map\n(Implementation in progress)', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        
    def plot_process_window(self):
        """Plot process window analysis"""
        # Implementation for process window analysis
        ax = self.analysis_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Process Window Analysis\n(Implementation in progress)', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        
    def run_correction_simulation(self):
        """Run simulation with proximity corrections"""
        if not self.patterns:
            QMessageBox.warning(self, "No Patterns", "Define patterns first")
            return
            
        self.status_label.setText("Running proximity correction simulation...")
        self.progress_bar.setValue(0)
        self.run_simulation_button.setEnabled(False)
        self.stop_simulation_button.setEnabled(True)
        
        # This would interface with your Geant4 simulation
        # For now, create a placeholder visualization
        
        self.sim_figure.clear()
        ax = self.sim_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Proximity Correction Simulation\n\n' +
               'This would generate corrected dose patterns\n' +
               'and run them through the Geant4 simulation\n' +
               'to verify correction effectiveness.',
               ha='center', va='center', transform=ax.transAxes, fontsize=12)
        
        self.sim_canvas.draw()
        
        # Reset UI
        self.progress_bar.setValue(100)
        self.status_label.setText("Simulation complete")
        self.run_simulation_button.setEnabled(True)
        self.stop_simulation_button.setEnabled(False)
        
    def update_simulation_view(self):
        """Update simulation results view"""
        view_type = self.view_combo.currentText()
        
        # This would update the visualization based on simulation results
        self.sim_figure.clear()
        ax = self.sim_figure.add_subplot(111)
        ax.text(0.5, 0.5, f'{view_type}\n(Simulation results would be displayed here)', 
               ha='center', va='center', transform=ax.transAxes, fontsize=12)
        self.sim_canvas.draw()