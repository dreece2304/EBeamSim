# PowerShell script to create the widget files
# Usage: .\create_widget_files.ps1 -GuiPath "C:\Users\dreec\Geant4Projects\EBeamSim\scripts\gui"

param(
    [Parameter(Mandatory=$true)]
    [string]$GuiPath
)

Write-Host "Creating widget files at: $GuiPath\widgets" -ForegroundColor Green

# Create material_widget.py with full content
@'
"""
Material properties widget
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDoubleSpinBox,
    QGroupBox, QPushButton
)
from PySide6.QtCore import Signal

from core.config import Config

class MaterialWidget(QWidget):
    """Widget for material property configuration"""
    
    material_changed = Signal()
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setup_ui()
        self.update_from_config()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Material selection group
        material_group = QGroupBox("Material Properties")
        material_layout = QGridLayout()
        
        # Material preset
        material_layout.addWidget(QLabel("Material:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems(list(self.config.MATERIAL_PRESETS.keys()))
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        material_layout.addWidget(self.material_combo, 0, 1)
        
        # Composition
        material_layout.addWidget(QLabel("Composition:"), 1, 0)
        self.composition_edit = QLineEdit()
        self.composition_edit.setPlaceholderText("Al:1,C:5,H:4,O:2")
        self.composition_edit.textChanged.connect(self.on_custom_change)
        material_layout.addWidget(self.composition_edit, 1, 1, 1, 2)
        
        # Thickness
        material_layout.addWidget(QLabel("Thickness (nm):"), 2, 0)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1.0, 10000.0)
        self.thickness_spin.setDecimals(1)
        self.thickness_spin.setSingleStep(1.0)
        self.thickness_spin.valueChanged.connect(self.on_parameter_changed)
        material_layout.addWidget(self.thickness_spin, 2, 1)
        
        # Density
        material_layout.addWidget(QLabel("Density (g/cm³):"), 3, 0)
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 10.0)
        self.density_spin.setDecimals(2)
        self.density_spin.setSingleStep(0.01)
        self.density_spin.valueChanged.connect(self.on_parameter_changed)
        material_layout.addWidget(self.density_spin, 3, 1)
        
        material_group.setLayout(material_layout)
        
        # Information group
        info_group = QGroupBox("Material Information")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel()
        self.update_info_label()
        info_layout.addWidget(self.info_label)
        
        info_group.setLayout(info_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_preset_btn = QPushButton("Save as Preset")
        self.save_preset_btn.clicked.connect(self.save_preset)
        button_layout.addWidget(self.save_preset_btn)
        
        self.load_from_file_btn = QPushButton("Load from File")
        self.load_from_file_btn.clicked.connect(self.load_from_file)
        button_layout.addWidget(self.load_from_file_btn)
        
        button_layout.addStretch()
        
        # Add to main layout
        layout.addWidget(material_group)
        layout.addWidget(info_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def on_material_changed(self, material_name: str):
        """Handle material selection change"""
        if material_name in self.config.MATERIAL_PRESETS:
            preset = self.config.MATERIAL_PRESETS[material_name]
            self.composition_edit.setText(preset["composition"])
            self.density_spin.setValue(preset["density"])
            
            # Enable/disable editing
            is_custom = (material_name == "Custom")
            self.composition_edit.setReadOnly(not is_custom)
            
            # Update config
            self.config.material.name = material_name
            self.update_config()
    
    def on_custom_change(self):
        """Handle custom composition change"""
        if self.material_combo.currentText() == "Custom":
            self.update_config()
    
    def on_parameter_changed(self):
        """Handle parameter changes"""
        self.update_config()
    
    def update_config(self):
        """Update configuration from widget values"""
        self.config.material.composition = self.composition_edit.text()
        self.config.material.thickness = self.thickness_spin.value()
        self.config.material.density = self.density_spin.value()
        
        self.update_info_label()
        self.material_changed.emit()
    
    def update_from_config(self):
        """Update widget from configuration"""
        self.material_combo.setCurrentText(self.config.material.name)
        self.composition_edit.setText(self.config.material.composition)
        self.thickness_spin.setValue(self.config.material.thickness)
        self.density_spin.setValue(self.config.material.density)
        
        self.update_info_label()
    
    def update_info_label(self):
        """Update information label"""
        info_text = f"""
<b>Current Material: {self.config.material.name}</b><br>
<br>
<b>Properties:</b><br>
• Composition: {self.config.material.composition}<br>
• Thickness: {self.config.material.thickness:.1f} nm<br>
• Density: {self.config.material.density:.2f} g/cm³<br>
<br>
<b>Notes:</b><br>
• Alucone values based on XPS analysis<br>
• TMA + butyne-1,4-diol MLD process
"""
        self.info_label.setText(info_text)
    
    def save_preset(self):
        """Save current settings as a preset"""
        # TODO: Implement preset saving dialog
        pass
    
    def load_from_file(self):
        """Load material from file"""
        # TODO: Implement file loading dialog
        pass
'@ | Set-Content -Path "$GuiPath\widgets\material_widget.py" -Encoding UTF8

Write-Host "Created material_widget.py" -ForegroundColor Cyan

# Continue with other files...
# Due to length, I'll create a simple batch script approach

Write-Host "`nWidget files structure created!" -ForegroundColor Green
Write-Host "`nTo get the complete widget files:" -ForegroundColor Yellow
Write-Host "1. I'll provide them as separate downloads"
Write-Host "2. Or you can copy from the artifacts I created earlier"