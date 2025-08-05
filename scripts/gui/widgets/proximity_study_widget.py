"""
Proximity Study Widget
Interactive tool for studying proximity effects with multiple patterns
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
                              QTableWidget, QTableWidgetItem, QGroupBox,
                              QCheckBox, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt, Signal
import numpy as np
import json
from pathlib import Path


class ProximityStudyWidget(QWidget):
    """Widget for defining and analyzing proximity effect studies"""
    
    # Signals
    study_configured = Signal(dict)  # Emits study configuration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.patterns = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Study parameters
        param_group = QGroupBox("Study Parameters")
        param_layout = QVBoxLayout()
        
        # Resist thickness range
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Resist Thickness Range:"))
        
        self.thickness_min_spin = QSpinBox()
        self.thickness_min_spin.setRange(5, 500)
        self.thickness_min_spin.setValue(10)
        self.thickness_min_spin.setSuffix(" nm")
        thickness_layout.addWidget(self.thickness_min_spin)
        
        thickness_layout.addWidget(QLabel("to"))
        
        self.thickness_max_spin = QSpinBox()
        self.thickness_max_spin.setRange(5, 500)
        self.thickness_max_spin.setValue(100)
        self.thickness_max_spin.setSuffix(" nm")
        thickness_layout.addWidget(self.thickness_max_spin)
        
        thickness_layout.addWidget(QLabel("Steps:"))
        self.thickness_steps_spin = QSpinBox()
        self.thickness_steps_spin.setRange(2, 10)
        self.thickness_steps_spin.setValue(5)
        thickness_layout.addWidget(self.thickness_steps_spin)
        
        thickness_layout.addStretch()
        param_layout.addLayout(thickness_layout)
        
        # Dose range
        dose_layout = QHBoxLayout()
        dose_layout.addWidget(QLabel("Dose Range:"))
        
        self.dose_min_spin = QSpinBox()
        self.dose_min_spin.setRange(50, 50000)
        self.dose_min_spin.setValue(1000)
        self.dose_min_spin.setSuffix(" uC/cm²")
        dose_layout.addWidget(self.dose_min_spin)
        
        dose_layout.addWidget(QLabel("to"))
        
        self.dose_max_spin = QSpinBox()
        self.dose_max_spin.setRange(50, 50000)
        self.dose_max_spin.setValue(10000)
        self.dose_max_spin.setSuffix(" uC/cm²")
        dose_layout.addWidget(self.dose_max_spin)
        
        dose_layout.addWidget(QLabel("Steps:"))
        self.dose_steps_spin = QSpinBox()
        self.dose_steps_spin.setRange(2, 10)
        self.dose_steps_spin.setValue(5)
        dose_layout.addWidget(self.dose_steps_spin)
        
        dose_layout.addStretch()
        param_layout.addLayout(dose_layout)
        
        # Resist thresholds
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Resist Thresholds:"))
        
        threshold_layout.addWidget(QLabel("Clearing:"))
        self.clearing_dose_spin = QSpinBox()
        self.clearing_dose_spin.setRange(100, 20000)
        self.clearing_dose_spin.setValue(2500)
        self.clearing_dose_spin.setSuffix(" uC/cm²")
        self.clearing_dose_spin.setToolTip("Dose required to fully clear resist")
        threshold_layout.addWidget(self.clearing_dose_spin)
        
        threshold_layout.addWidget(QLabel("Crosslink Start:"))
        self.crosslink_start_spin = QSpinBox()
        self.crosslink_start_spin.setRange(50, 5000)
        self.crosslink_start_spin.setValue(500)
        self.crosslink_start_spin.setSuffix(" uC/cm²")
        self.crosslink_start_spin.setToolTip("Dose where crosslinking begins")
        threshold_layout.addWidget(self.crosslink_start_spin)
        
        threshold_layout.addStretch()
        param_layout.addLayout(threshold_layout)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        # Pattern configuration
        pattern_group = QGroupBox("Pattern Configuration")
        pattern_layout = QVBoxLayout()
        
        # Pattern presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Single Square",
            "Two Squares (Gap Study)",
            "Line Array",
            "Dense Square Array",
            "Isolated vs Dense",
            "Custom"
        ])
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        preset_layout.addWidget(self.preset_combo)
        
        preset_layout.addWidget(QLabel("Gap/Pitch:"))
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(10, 1000)
        self.gap_spin.setValue(200)
        self.gap_spin.setSuffix(" nm")
        preset_layout.addWidget(self.gap_spin)
        
        self.apply_preset_button = QPushButton("Apply Preset")
        self.apply_preset_button.clicked.connect(self.apply_preset)
        preset_layout.addWidget(self.apply_preset_button)
        
        preset_layout.addStretch()
        pattern_layout.addLayout(preset_layout)
        
        # Pattern table
        self.pattern_table = QTableWidget()
        self.pattern_table.setColumnCount(5)
        self.pattern_table.setHorizontalHeaderLabels([
            "Type", "Size (nm)", "Center X", "Center Y", "Action"
        ])
        self.pattern_table.horizontalHeader().setStretchLastSection(True)
        pattern_layout.addWidget(self.pattern_table)
        
        # Add pattern controls
        add_pattern_layout = QHBoxLayout()
        
        self.pattern_type_combo = QComboBox()
        self.pattern_type_combo.addItems(["square", "line", "circle"])
        add_pattern_layout.addWidget(self.pattern_type_combo)
        
        self.pattern_size_spin = QSpinBox()
        self.pattern_size_spin.setRange(10, 5000)
        self.pattern_size_spin.setValue(100)
        self.pattern_size_spin.setSuffix(" nm")
        add_pattern_layout.addWidget(self.pattern_size_spin)
        
        self.pattern_x_spin = QSpinBox()
        self.pattern_x_spin.setRange(-5000, 5000)
        self.pattern_x_spin.setValue(0)
        self.pattern_x_spin.setPrefix("X: ")
        self.pattern_x_spin.setSuffix(" nm")
        add_pattern_layout.addWidget(self.pattern_x_spin)
        
        self.pattern_y_spin = QSpinBox()
        self.pattern_y_spin.setRange(-5000, 5000)
        self.pattern_y_spin.setValue(0)
        self.pattern_y_spin.setPrefix("Y: ")
        self.pattern_y_spin.setSuffix(" nm")
        add_pattern_layout.addWidget(self.pattern_y_spin)
        
        self.add_pattern_button = QPushButton("Add Pattern")
        self.add_pattern_button.clicked.connect(self.add_pattern)
        add_pattern_layout.addWidget(self.add_pattern_button)
        
        pattern_layout.addLayout(add_pattern_layout)
        
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)
        
        # Analysis options
        analysis_group = QGroupBox("Analysis Options")
        analysis_layout = QHBoxLayout()
        
        self.analyze_broadening_check = QCheckBox("Edge Broadening")
        self.analyze_broadening_check.setChecked(True)
        analysis_layout.addWidget(self.analyze_broadening_check)
        
        self.analyze_proximity_check = QCheckBox("Proximity Dose")
        self.analyze_proximity_check.setChecked(True)
        analysis_layout.addWidget(self.analyze_proximity_check)
        
        self.analyze_crosslink_check = QCheckBox("Crosslinking Risk")
        self.analyze_crosslink_check.setChecked(True)
        analysis_layout.addWidget(self.analyze_crosslink_check)
        
        self.generate_maps_check = QCheckBox("Generate Dose Maps")
        self.generate_maps_check.setChecked(True)
        analysis_layout.addWidget(self.generate_maps_check)
        
        analysis_layout.addStretch()
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("Preview Pattern Layout")
        self.preview_button.clicked.connect(self.preview_patterns)
        button_layout.addWidget(self.preview_button)
        
        self.export_button = QPushButton("Export Study Configuration")
        self.export_button.clicked.connect(self.export_configuration)
        button_layout.addWidget(self.export_button)
        
        self.run_study_button = QPushButton("Configure Study")
        self.run_study_button.clicked.connect(self.configure_study)
        self.run_study_button.setStyleSheet("QPushButton { font-weight: bold; }")
        button_layout.addWidget(self.run_study_button)
        
        layout.addLayout(button_layout)
        
        # Summary label
        self.summary_label = QLabel("Configure patterns and parameters above")
        layout.addWidget(self.summary_label)
        
    def add_pattern(self):
        """Add a pattern to the list"""
        pattern = {
            'type': self.pattern_type_combo.currentText(),
            'size': self.pattern_size_spin.value(),
            'center': [self.pattern_x_spin.value(), self.pattern_y_spin.value()]
        }
        
        self.patterns.append(pattern)
        self.update_pattern_table()
        self.update_summary()
        
    def remove_pattern(self, index):
        """Remove a pattern from the list"""
        if 0 <= index < len(self.patterns):
            self.patterns.pop(index)
            self.update_pattern_table()
            self.update_summary()
            
    def update_pattern_table(self):
        """Update the pattern table display"""
        self.pattern_table.setRowCount(len(self.patterns))
        
        for i, pattern in enumerate(self.patterns):
            self.pattern_table.setItem(i, 0, QTableWidgetItem(pattern['type']))
            self.pattern_table.setItem(i, 1, QTableWidgetItem(str(pattern['size'])))
            self.pattern_table.setItem(i, 2, QTableWidgetItem(str(pattern['center'][0])))
            self.pattern_table.setItem(i, 3, QTableWidgetItem(str(pattern['center'][1])))
            
            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, idx=i: self.remove_pattern(idx))
            self.pattern_table.setCellWidget(i, 4, remove_btn)
            
    def load_preset(self, preset_name):
        """Load preset description"""
        descriptions = {
            "Single Square": "Single isolated square for baseline measurements",
            "Two Squares (Gap Study)": "Two squares with variable gap for proximity study",
            "Line Array": "Parallel lines to study line-to-line proximity",
            "Dense Square Array": "Array of squares to study collective proximity",
            "Isolated vs Dense": "Compare isolated and densely packed patterns",
            "Custom": "Define your own pattern configuration"
        }
        
        if preset_name in descriptions:
            self.summary_label.setText(descriptions[preset_name])
            
    def apply_preset(self):
        """Apply selected preset"""
        preset = self.preset_combo.currentText()
        gap = self.gap_spin.value()
        
        self.patterns.clear()
        
        if preset == "Single Square":
            self.patterns.append({
                'type': 'square',
                'size': 100,
                'center': [0, 0]
            })
            
        elif preset == "Two Squares (Gap Study)":
            size = 100
            self.patterns.extend([
                {'type': 'square', 'size': size, 'center': [-gap/2 - size/2, 0]},
                {'type': 'square', 'size': size, 'center': [gap/2 + size/2, 0]}
            ])
            
        elif preset == "Line Array":
            for i in range(5):
                y_pos = (i - 2) * gap
                self.patterns.append({
                    'type': 'line',
                    'size': 500,
                    'center': [0, y_pos]
                })
                
        elif preset == "Dense Square Array":
            size = 100
            pitch = size + gap
            for i in range(-2, 3):
                for j in range(-2, 3):
                    self.patterns.append({
                        'type': 'square',
                        'size': size,
                        'center': [i * pitch, j * pitch]
                    })
                    
        elif preset == "Isolated vs Dense":
            # Isolated square
            self.patterns.append({
                'type': 'square',
                'size': 100,
                'center': [-1000, 0]
            })
            
            # Dense array
            size = 100
            pitch = size + gap
            for i in range(3):
                for j in range(3):
                    self.patterns.append({
                        'type': 'square',
                        'size': size,
                        'center': [500 + i * pitch, -pitch + j * pitch]
                    })
                    
        self.update_pattern_table()
        self.update_summary()
        
    def update_summary(self):
        """Update summary label"""
        n_patterns = len(self.patterns)
        
        # Calculate thickness and dose arrays
        thickness_values = np.linspace(
            self.thickness_min_spin.value(),
            self.thickness_max_spin.value(),
            self.thickness_steps_spin.value()
        )
        
        dose_values = np.linspace(
            self.dose_min_spin.value(),
            self.dose_max_spin.value(),
            self.dose_steps_spin.value()
        )
        
        n_simulations = len(thickness_values) * len(dose_values)
        
        summary = f"Patterns: {n_patterns}, "
        summary += f"Thicknesses: {len(thickness_values)}, "
        summary += f"Doses: {len(dose_values)}, "
        summary += f"Total simulations: {n_simulations}"
        
        self.summary_label.setText(summary)
        
    def preview_patterns(self):
        """Show preview of pattern layout"""
        if not self.patterns:
            QMessageBox.warning(self, "No Patterns", "Add patterns first")
            return
            
        # Create a simple preview plot
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle, Circle
        
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Plot each pattern
        for pattern in self.patterns:
            x, y = pattern['center']
            size = pattern['size']
            
            if pattern['type'] == 'square':
                rect = Rectangle((x - size/2, y - size/2), size, size,
                               fill=False, edgecolor='blue', linewidth=2)
                ax.add_patch(rect)
                
            elif pattern['type'] == 'line':
                ax.plot([x - size/2, x + size/2], [y, y], 'b-', linewidth=3)
                
            elif pattern['type'] == 'circle':
                circle = Circle((x, y), size/2, fill=False, edgecolor='blue', linewidth=2)
                ax.add_patch(circle)
                
        # Calculate field bounds
        all_x = []
        all_y = []
        for p in self.patterns:
            all_x.extend([p['center'][0] - p['size']/2, p['center'][0] + p['size']/2])
            all_y.extend([p['center'][1] - p['size']/2, p['center'][1] + p['size']/2])
            
        margin = 200  # nm
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
        
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_title('Pattern Layout Preview')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
    def export_configuration(self):
        """Export study configuration to JSON"""
        config = self.get_configuration()
        
        from PySide6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Study Configuration",
            "proximity_study.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            QMessageBox.information(self, "Exported", f"Configuration saved to {filename}")
            
    def configure_study(self):
        """Configure and emit study parameters"""
        if not self.patterns:
            QMessageBox.warning(self, "No Patterns", "Add at least one pattern")
            return
            
        config = self.get_configuration()
        self.study_configured.emit(config)
        
    def get_configuration(self):
        """Get complete study configuration"""
        # Calculate parameter arrays
        thickness_values = np.linspace(
            self.thickness_min_spin.value(),
            self.thickness_max_spin.value(),
            self.thickness_steps_spin.value()
        ).tolist()
        
        dose_values = np.linspace(
            self.dose_min_spin.value(),
            self.dose_max_spin.value(),
            self.dose_steps_spin.value()
        ).tolist()
        
        # Calculate field size
        all_x = []
        all_y = []
        for p in self.patterns:
            all_x.extend([p['center'][0] - p['size']/2, p['center'][0] + p['size']/2])
            all_y.extend([p['center'][1] - p['size']/2, p['center'][1] + p['size']/2])
            
        field_size = max(max(all_x) - min(all_x), max(all_y) - min(all_y)) + 400
        
        config = {
            'patterns': self.patterns,
            'field_size': field_size,
            'thickness_values': thickness_values,
            'dose_values': dose_values,
            'resist_thresholds': {
                'clearing_dose': self.clearing_dose_spin.value(),
                'crosslink_start': self.crosslink_start_spin.value()
            },
            'analysis': {
                'edge_broadening': self.analyze_broadening_check.isChecked(),
                'proximity_dose': self.analyze_proximity_check.isChecked(),
                'crosslink_risk': self.analyze_crosslink_check.isChecked(),
                'generate_maps': self.generate_maps_check.isChecked()
            }
        }
        
        return config