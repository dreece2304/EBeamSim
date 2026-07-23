"""
Resist properties configuration widget
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QTextEdit, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.material_model import MaterialModel


class ResistPropertiesWidget(QWidget):
    """Widget for configuring resist material properties"""
    
    material_changed = Signal(MaterialModel)
    uv_properties_changed = Signal(float, str)  # absorptance, measurement_status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_material = MaterialModel.from_preset("PMMA")
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Material selection group
        selection_group = QGroupBox("Material Selection")
        selection_layout = QGridLayout(selection_group)
        
        # Preset combo box
        selection_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(MaterialModel.PRESETS.keys()))
        self.preset_combo.addItem("Custom")
        selection_layout.addWidget(self.preset_combo, 0, 1)
        
        # Load/Save buttons
        self.load_btn = QPushButton("Load Config")
        self.save_btn = QPushButton("Save Config")
        selection_layout.addWidget(self.load_btn, 0, 2)
        selection_layout.addWidget(self.save_btn, 0, 3)
        
        layout.addWidget(selection_group)
        
        # Material properties group
        properties_group = QGroupBox("Material Properties")
        properties_layout = QGridLayout(properties_group)
        
        # Name
        properties_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        properties_layout.addWidget(self.name_edit, 0, 1)
        
        # Composition
        properties_layout.addWidget(QLabel("Composition:"), 1, 0)
        self.composition_edit = QLineEdit()
        self.composition_edit.setPlaceholderText("e.g., C:5,H:8,O:2")
        properties_layout.addWidget(self.composition_edit, 1, 1)
        
        # Density
        properties_layout.addWidget(QLabel("Density (g/cm³):"), 2, 0)
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 10.0)
        self.density_spin.setDecimals(3)
        self.density_spin.setSingleStep(0.01)
        properties_layout.addWidget(self.density_spin, 2, 1)
        
        # Thickness
        properties_layout.addWidget(QLabel("Thickness (nm):"), 3, 0)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 1000.0)
        self.thickness_spin.setDecimals(1)
        self.thickness_spin.setSingleStep(1.0)
        properties_layout.addWidget(self.thickness_spin, 3, 1)
        
        # Description
        properties_layout.addWidget(QLabel("Description:"), 4, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        properties_layout.addWidget(self.description_edit, 4, 1)
        
        # Validate button
        self.validate_btn = QPushButton("Validate Material")
        properties_layout.addWidget(self.validate_btn, 5, 0, 1, 2)
        
        layout.addWidget(properties_group)
        
        # UV properties group (for energy equivalence calculations)
        uv_group = QGroupBox("UV Optical Properties (Optional)")
        uv_layout = QGridLayout(uv_group)
        
        # UV absorptance at 254 nm
        uv_layout.addWidget(QLabel("UV absorptance @ 254 nm:"), 0, 0)
        self.uv_absorptance_spin = QDoubleSpinBox()
        self.uv_absorptance_spin.setRange(0.01, 1.0)
        self.uv_absorptance_spin.setDecimals(3)
        self.uv_absorptance_spin.setSingleStep(0.01)
        self.uv_absorptance_spin.setValue(0.3)  # Default estimate
        self.uv_absorptance_spin.setToolTip("Fraction of 254nm UV light absorbed (measure with UV-Vis)")
        uv_layout.addWidget(self.uv_absorptance_spin, 0, 1)
        
        # Measurement status
        uv_layout.addWidget(QLabel("Measurement status:"), 1, 0)
        self.uv_measured_combo = QComboBox()
        self.uv_measured_combo.addItems(["Estimated", "Measured", "Literature"])
        uv_layout.addWidget(self.uv_measured_combo, 1, 1)
        
        # Info label
        uv_info = QLabel("💡 Required for UV energy equivalence calculations")
        uv_info.setStyleSheet("color: #4A90E2; font-style: italic;")
        uv_layout.addWidget(uv_info, 2, 0, 1, 2)
        
        layout.addWidget(uv_group)
        
        # Composition help group
        help_group = QGroupBox("Composition Format Help")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QLabel("""
        Format: Element:Ratio,Element:Ratio,...

        Examples:
        • PMMA: C:5,H:8,O:2
        • HSQ: Si:1,H:1,O:1.5
        • Alucone: Al:1,C:5,H:4,O:2
        • Sn-MLD: Sn:1,C:8,H:8,O:4

        Use standard element symbols (C, H, O, Si, Al, Sn, etc.)
        Ratios can be decimals (e.g., O:1.5)
        """)
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_group)
        
        layout.addStretch()
    
    def connect_signals(self):
        """Connect widget signals"""
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        self.name_edit.textChanged.connect(self.on_property_changed)
        self.composition_edit.textChanged.connect(self.on_property_changed)
        self.density_spin.valueChanged.connect(self.on_property_changed)
        self.thickness_spin.valueChanged.connect(self.on_property_changed)
        self.description_edit.textChanged.connect(self.on_property_changed)
        self.validate_btn.clicked.connect(self.validate_material)
        self.load_btn.clicked.connect(self.load_material_config)
        self.save_btn.clicked.connect(self.save_material_config)
        
        # UV properties signals
        self.uv_absorptance_spin.valueChanged.connect(self.on_uv_properties_changed)
        self.uv_measured_combo.currentTextChanged.connect(self.on_uv_properties_changed)
    
    def on_preset_changed(self, preset_name: str):
        """Handle preset selection change"""
        if preset_name == "Custom":
            return
        
        if preset_name in MaterialModel.PRESETS:
            self.current_material = MaterialModel.from_preset(
                preset_name, 
                self.thickness_spin.value()
            )
            self.update_ui_from_material()
            self.material_changed.emit(self.current_material)
    
    def on_property_changed(self):
        """Handle property change"""
        self.current_material = MaterialModel(
            name=self.name_edit.text(),
            composition=self.composition_edit.text(),
            density=self.density_spin.value(),
            thickness=self.thickness_spin.value(),
            description=self.description_edit.toPlainText()
        )
        
        # Update preset combo to "Custom" if values don't match preset
        if not self._matches_preset():
            self.preset_combo.setCurrentText("Custom")
        
        self.material_changed.emit(self.current_material)
    
    def _matches_preset(self) -> bool:
        """Check if current values match a preset"""
        for preset_name, preset_data in MaterialModel.PRESETS.items():
            if (self.composition_edit.text() == preset_data["composition"] and
                abs(self.density_spin.value() - preset_data["density"]) < 0.01):
                return True
        return False
    
    def update_ui_from_material(self):
        """Update UI controls from current material"""
        self.name_edit.setText(self.current_material.name)
        self.composition_edit.setText(self.current_material.composition)
        self.density_spin.setValue(self.current_material.density)
        self.thickness_spin.setValue(self.current_material.thickness)
        self.description_edit.setPlainText(self.current_material.description)
    
    def set_material(self, material: MaterialModel):
        """Set current material"""
        self.current_material = material
        self.update_ui_from_material()
        
        # Update preset combo if material matches a preset
        for preset_name, preset_data in MaterialModel.PRESETS.items():
            if (material.composition == preset_data["composition"] and
                abs(material.density - preset_data["density"]) < 0.01):
                self.preset_combo.setCurrentText(preset_name)
                break
        else:
            self.preset_combo.setCurrentText("Custom")
    
    def get_material(self) -> MaterialModel:
        """Get current material"""
        return self.current_material
    
    def validate_material(self):
        """Validate current material properties"""
        if self.current_material.validate():
            QMessageBox.information(
                self, 
                "Validation", 
                "Material properties are valid!"
            )
        else:
            errors = []
            if not self.current_material.composition:
                errors.append("Composition cannot be empty")
            if self.current_material.density <= 0:
                errors.append("Density must be positive")
            if self.current_material.thickness <= 0:
                errors.append("Thickness must be positive")
            
            QMessageBox.warning(
                self, 
                "Validation Error", 
                "Material validation failed:\n" + "\n".join(errors)
            )
    
    def load_material_config(self):
        """Load material configuration from file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Material Configuration",
            "",
            "JSON files (*.json);;All files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                material = MaterialModel.from_dict(data)
                self.set_material(material)
                self.material_changed.emit(self.current_material)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Material configuration loaded from {file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load material configuration:\n{str(e)}"
                )
    
    def save_material_config(self):
        """Save material configuration to file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Material Configuration",
            f"{self.current_material.name.replace(' ', '_')}.json",
            "JSON files (*.json);;All files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.current_material.to_dict(), f, indent=2)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Material configuration saved to {file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save material configuration:\n{str(e)}"
                )
    
    def reset_to_defaults(self):
        """Reset to default PMMA material"""
        self.current_material = MaterialModel.from_preset("PMMA")
        self.update_ui_from_material()
        self.preset_combo.setCurrentText("PMMA")
        self.material_changed.emit(self.current_material)
        
    def on_uv_properties_changed(self):
        """Handle UV properties change"""
        absorptance = self.uv_absorptance_spin.value()
        measurement_status = self.uv_measured_combo.currentText()
        self.uv_properties_changed.emit(absorptance, measurement_status)
        
    def get_uv_absorptance(self) -> float:
        """Get current UV absorptance value"""
        return self.uv_absorptance_spin.value()
        
    def set_uv_absorptance(self, absorptance: float):
        """Set UV absorptance value"""
        self.uv_absorptance_spin.setValue(absorptance)
        
    def get_uv_measurement_status(self) -> str:
        """Get UV measurement status"""
        return self.uv_measured_combo.currentText()
        
    def set_uv_measurement_status(self, status: str):
        """Set UV measurement status"""
        index = self.uv_measured_combo.findText(status)
        if index >= 0:
            self.uv_measured_combo.setCurrentIndex(index)
            
    def get_estimated_uv_absorptance_for_composition(self, composition: str) -> float:
        """Get estimated UV absorptance based on material composition"""
        # Simple estimation based on common resist materials
        # This could be expanded with a more sophisticated model

        composition_lower = composition.lower()

        # Tin-containing resists (Sn-oxo cages, etc.)
        if 'sn' in composition_lower:
            return 0.65  # Very high absorption due to heavy metal content

        # Alucone and aluminum-containing resists
        elif 'al' in composition_lower:
            return 0.4  # Higher absorption due to metal content

        # Silicon-containing resists (HSQ, etc.)
        elif 'si' in composition_lower:
            return 0.2  # Lower absorption

        # PMMA-like organic resists
        elif 'c' in composition_lower and 'o' in composition_lower:
            return 0.3  # Moderate absorption

        # Default estimate
        else:
            return 0.25
            
    def update_uv_estimate_from_composition(self):
        """Update UV absorptance estimate when composition changes"""
        if self.uv_measured_combo.currentText() == "Estimated":
            composition = self.composition_edit.text()
            estimated_absorptance = self.get_estimated_uv_absorptance_for_composition(composition)
            self.uv_absorptance_spin.setValue(estimated_absorptance)