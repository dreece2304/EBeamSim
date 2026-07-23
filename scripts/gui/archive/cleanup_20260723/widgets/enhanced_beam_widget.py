"""
Enhanced beam parameters configuration widget
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QSlider, QCheckBox, QSpinBox
)
from PySide6.QtCore import Signal, Qt
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.beam_model import BeamModel


class EnhancedBeamWidget(QWidget):
    """Enhanced widget for configuring electron beam parameters"""
    
    beam_changed = Signal(BeamModel)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_beam = BeamModel()
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Energy configuration group
        energy_group = QGroupBox("Beam Energy")
        energy_layout = QGridLayout(energy_group)
        
        # Energy preset
        energy_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.energy_preset_combo = QComboBox()
        self.energy_preset_combo.addItems(list(BeamModel.ENERGY_PRESETS.keys()))
        self.energy_preset_combo.addItem("Custom")
        energy_layout.addWidget(self.energy_preset_combo, 0, 1)
        
        # Energy value
        energy_layout.addWidget(QLabel("Energy (keV):"), 1, 0)
        self.energy_spin = QDoubleSpinBox()
        self.energy_spin.setRange(1.0, 1000.0)
        self.energy_spin.setDecimals(1)
        self.energy_spin.setSingleStep(1.0)
        self.energy_spin.setValue(100.0)
        energy_layout.addWidget(self.energy_spin, 1, 1)
        
        # Energy slider for quick adjustment
        self.energy_slider = QSlider(Qt.Horizontal)
        self.energy_slider.setRange(10, 500)
        self.energy_slider.setValue(100)
        energy_layout.addWidget(self.energy_slider, 2, 0, 1, 2)
        
        layout.addWidget(energy_group)
        
        # Beam geometry group
        geometry_group = QGroupBox("Beam Geometry")
        geometry_layout = QGridLayout(geometry_group)
        
        # Beam size
        geometry_layout.addWidget(QLabel("Beam Size (nm):"), 0, 0)
        self.beam_size_spin = QDoubleSpinBox()
        self.beam_size_spin.setRange(0.1, 100.0)
        self.beam_size_spin.setDecimals(2)
        self.beam_size_spin.setSingleStep(0.1)
        self.beam_size_spin.setValue(2.0)
        geometry_layout.addWidget(self.beam_size_spin, 0, 1)
        
        # Particle type
        geometry_layout.addWidget(QLabel("Particle Type:"), 1, 0)
        self.particle_combo = QComboBox()
        self.particle_combo.addItems(["e-", "e+", "proton", "alpha"])
        geometry_layout.addWidget(self.particle_combo, 1, 1)
        
        layout.addWidget(geometry_group)
        
        # Position group
        position_group = QGroupBox("Beam Position")
        position_layout = QGridLayout(position_group)
        
        # X position
        position_layout.addWidget(QLabel("X (nm):"), 0, 0)
        self.pos_x_spin = QDoubleSpinBox()
        self.pos_x_spin.setRange(-1000.0, 1000.0)
        self.pos_x_spin.setDecimals(1)
        self.pos_x_spin.setValue(0.0)
        position_layout.addWidget(self.pos_x_spin, 0, 1)
        
        # Y position
        position_layout.addWidget(QLabel("Y (nm):"), 1, 0)
        self.pos_y_spin = QDoubleSpinBox()
        self.pos_y_spin.setRange(-1000.0, 1000.0)
        self.pos_y_spin.setDecimals(1)
        self.pos_y_spin.setValue(0.0)
        position_layout.addWidget(self.pos_y_spin, 1, 1)
        
        # Z position
        position_layout.addWidget(QLabel("Z (nm):"), 2, 0)
        self.pos_z_spin = QDoubleSpinBox()
        self.pos_z_spin.setRange(-1000.0, 1000.0)
        self.pos_z_spin.setDecimals(1)
        self.pos_z_spin.setValue(100.0)
        position_layout.addWidget(self.pos_z_spin, 2, 1)
        
        # Center beam button
        self.center_btn = QPushButton("Center Beam")
        position_layout.addWidget(self.center_btn, 3, 0, 1, 2)
        
        layout.addWidget(position_group)
        
        # Direction group
        direction_group = QGroupBox("Beam Direction")
        direction_layout = QGridLayout(direction_group)
        
        # Direction presets
        direction_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.direction_preset_combo = QComboBox()
        self.direction_preset_combo.addItems([
            "Normal (-Z)", "45° Tilt", "Custom"
        ])
        direction_layout.addWidget(self.direction_preset_combo, 0, 1)
        
        # X direction
        direction_layout.addWidget(QLabel("X Direction:"), 1, 0)
        self.dir_x_spin = QDoubleSpinBox()
        self.dir_x_spin.setRange(-1.0, 1.0)
        self.dir_x_spin.setDecimals(3)
        self.dir_x_spin.setValue(0.0)
        direction_layout.addWidget(self.dir_x_spin, 1, 1)
        
        # Y direction
        direction_layout.addWidget(QLabel("Y Direction:"), 2, 0)
        self.dir_y_spin = QDoubleSpinBox()
        self.dir_y_spin.setRange(-1.0, 1.0)
        self.dir_y_spin.setDecimals(3)
        self.dir_y_spin.setValue(0.0)
        direction_layout.addWidget(self.dir_y_spin, 2, 1)
        
        # Z direction
        direction_layout.addWidget(QLabel("Z Direction:"), 3, 0)
        self.dir_z_spin = QDoubleSpinBox()
        self.dir_z_spin.setRange(-1.0, 1.0)
        self.dir_z_spin.setDecimals(3)
        self.dir_z_spin.setValue(-1.0)
        direction_layout.addWidget(self.dir_z_spin, 3, 1)
        
        # Normalize direction button
        self.normalize_btn = QPushButton("Normalize Direction")
        direction_layout.addWidget(self.normalize_btn, 4, 0, 1, 2)
        
        layout.addWidget(direction_group)
        
        # Advanced options group
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QGridLayout(advanced_group)
        
        # Beam divergence
        advanced_layout.addWidget(QLabel("Beam Divergence (mrad):"), 0, 0)
        self.divergence_spin = QDoubleSpinBox()
        self.divergence_spin.setRange(0.0, 10.0)
        self.divergence_spin.setDecimals(2)
        self.divergence_spin.setValue(0.0)
        advanced_layout.addWidget(self.divergence_spin, 0, 1)
        
        # Energy spread
        advanced_layout.addWidget(QLabel("Energy Spread (eV):"), 1, 0)
        self.energy_spread_spin = QDoubleSpinBox()
        self.energy_spread_spin.setRange(0.0, 1000.0)
        self.energy_spread_spin.setDecimals(1)
        self.energy_spread_spin.setValue(0.0)
        advanced_layout.addWidget(self.energy_spread_spin, 1, 1)
        
        # Enable advanced physics
        self.advanced_physics_check = QCheckBox("Enable Advanced Physics")
        advanced_layout.addWidget(self.advanced_physics_check, 2, 0, 1, 2)
        
        layout.addWidget(advanced_group)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset to Defaults")
        self.validate_btn = QPushButton("Validate Parameters")
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.validate_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def connect_signals(self):
        """Connect widget signals"""
        # Energy controls
        self.energy_preset_combo.currentTextChanged.connect(self.on_energy_preset_changed)
        self.energy_spin.valueChanged.connect(self.on_beam_changed)
        self.energy_slider.valueChanged.connect(self.on_energy_slider_changed)
        
        # Geometry controls
        self.beam_size_spin.valueChanged.connect(self.on_beam_changed)
        self.particle_combo.currentTextChanged.connect(self.on_beam_changed)
        
        # Position controls
        self.pos_x_spin.valueChanged.connect(self.on_beam_changed)
        self.pos_y_spin.valueChanged.connect(self.on_beam_changed)
        self.pos_z_spin.valueChanged.connect(self.on_beam_changed)
        self.center_btn.clicked.connect(self.center_beam)
        
        # Direction controls
        self.direction_preset_combo.currentTextChanged.connect(self.on_direction_preset_changed)
        self.dir_x_spin.valueChanged.connect(self.on_beam_changed)
        self.dir_y_spin.valueChanged.connect(self.on_beam_changed)
        self.dir_z_spin.valueChanged.connect(self.on_beam_changed)
        self.normalize_btn.clicked.connect(self.normalize_direction)
        
        # Advanced controls
        self.divergence_spin.valueChanged.connect(self.on_beam_changed)
        self.energy_spread_spin.valueChanged.connect(self.on_beam_changed)
        self.advanced_physics_check.toggled.connect(self.on_beam_changed)
        
        # Buttons
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        self.validate_btn.clicked.connect(self.validate_parameters)
    
    def on_energy_preset_changed(self, preset_name: str):
        """Handle energy preset change"""
        if preset_name == "Custom":
            return
        
        if preset_name in BeamModel.ENERGY_PRESETS:
            energy = BeamModel.ENERGY_PRESETS[preset_name]
            self.energy_spin.setValue(energy)
            self.energy_slider.setValue(int(energy))
    
    def on_energy_slider_changed(self, value: int):
        """Handle energy slider change"""
        self.energy_spin.setValue(float(value))
        self.energy_preset_combo.setCurrentText("Custom")
    
    def on_direction_preset_changed(self, preset_name: str):
        """Handle direction preset change"""
        if preset_name == "Normal (-Z)":
            self.dir_x_spin.setValue(0.0)
            self.dir_y_spin.setValue(0.0)
            self.dir_z_spin.setValue(-1.0)
        elif preset_name == "45° Tilt":
            import math
            self.dir_x_spin.setValue(0.0)
            self.dir_y_spin.setValue(math.sin(math.radians(45)))
            self.dir_z_spin.setValue(-math.cos(math.radians(45)))
    
    def on_beam_changed(self):
        """Handle beam parameter change"""
        self.current_beam = BeamModel(
            energy=self.energy_spin.value(),
            beam_size=self.beam_size_spin.value(),
            position=(self.pos_x_spin.value(), self.pos_y_spin.value(), self.pos_z_spin.value()),
            direction=(self.dir_x_spin.value(), self.dir_y_spin.value(), self.dir_z_spin.value()),
            particle_type=self.particle_combo.currentText()
        )
        
        # Update preset combos if values don't match presets
        if not self._matches_energy_preset():
            self.energy_preset_combo.setCurrentText("Custom")
        
        if not self._matches_direction_preset():
            self.direction_preset_combo.setCurrentText("Custom")
        
        self.beam_changed.emit(self.current_beam)
    
    def _matches_energy_preset(self) -> bool:
        """Check if current energy matches a preset"""
        current_energy = self.energy_spin.value()
        for preset_energy in BeamModel.ENERGY_PRESETS.values():
            if abs(current_energy - preset_energy) < 0.1:
                return True
        return False
    
    def _matches_direction_preset(self) -> bool:
        """Check if current direction matches a preset"""
        x, y, z = self.dir_x_spin.value(), self.dir_y_spin.value(), self.dir_z_spin.value()
        
        # Normal direction
        if abs(x) < 0.001 and abs(y) < 0.001 and abs(z + 1.0) < 0.001:
            return True
        
        # 45° tilt
        import math
        expected_y = math.sin(math.radians(45))
        expected_z = -math.cos(math.radians(45))
        if (abs(x) < 0.001 and abs(y - expected_y) < 0.001 and 
            abs(z - expected_z) < 0.001):
            return True
        
        return False
    
    def center_beam(self):
        """Center the beam at origin"""
        self.pos_x_spin.setValue(0.0)
        self.pos_y_spin.setValue(0.0)
    
    def normalize_direction(self):
        """Normalize the direction vector"""
        import math
        x = self.dir_x_spin.value()
        y = self.dir_y_spin.value()
        z = self.dir_z_spin.value()
        
        magnitude = math.sqrt(x*x + y*y + z*z)
        if magnitude > 0:
            self.dir_x_spin.setValue(x / magnitude)
            self.dir_y_spin.setValue(y / magnitude)
            self.dir_z_spin.setValue(z / magnitude)
    
    def reset_to_defaults(self):
        """Reset to default beam parameters"""
        self.current_beam = BeamModel()
        self.update_ui_from_beam()
        self.beam_changed.emit(self.current_beam)
    
    def validate_parameters(self):
        """Validate beam parameters"""
        from PySide6.QtWidgets import QMessageBox
        
        if self.current_beam.validate():
            QMessageBox.information(
                self,
                "Validation",
                "Beam parameters are valid!"
            )
        else:
            errors = []
            if self.current_beam.energy <= 0:
                errors.append("Energy must be positive")
            if self.current_beam.beam_size <= 0:
                errors.append("Beam size must be positive")
            
            QMessageBox.warning(
                self,
                "Validation Error",
                "Beam validation failed:\n" + "\n".join(errors)
            )
    
    def update_ui_from_beam(self):
        """Update UI controls from current beam"""
        self.energy_spin.setValue(self.current_beam.energy)
        self.energy_slider.setValue(int(self.current_beam.energy))
        self.beam_size_spin.setValue(self.current_beam.beam_size)
        self.particle_combo.setCurrentText(self.current_beam.particle_type)
        
        self.pos_x_spin.setValue(self.current_beam.position_x)
        self.pos_y_spin.setValue(self.current_beam.position_y)
        self.pos_z_spin.setValue(self.current_beam.position_z)
        
        self.dir_x_spin.setValue(self.current_beam.direction_x)
        self.dir_y_spin.setValue(self.current_beam.direction_y)
        self.dir_z_spin.setValue(self.current_beam.direction_z)
    
    def set_beam(self, beam: BeamModel):
        """Set current beam"""
        self.current_beam = beam
        self.update_ui_from_beam()
    
    def get_beam(self) -> BeamModel:
        """Get current beam"""
        return self.current_beam