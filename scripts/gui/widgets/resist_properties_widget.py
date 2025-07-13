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

from ..models.material_model import MaterialModel


class ResistPropertiesWidget(QWidget):
    """Widget for configuring resist material properties"""
    
    material_changed = Signal(MaterialModel)
    
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
        
        # Composition help group
        help_group = QGroupBox("Composition Format Help")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QLabel("""
        Format: Element:Ratio,Element:Ratio,...
        
        Examples:
        • PMMA: C:5,H:8,O:2
        • HSQ: Si:1,H:1,O:1.5
        • Alucone: Al:1,C:5,H:4,O:2
        
        Use standard element symbols (C, H, O, Si, Al, etc.)
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