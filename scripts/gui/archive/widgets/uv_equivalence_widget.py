"""
UV Energy Equivalence Widget
============================

Widget for calculating and displaying UV-equivalent exposure times
for e-beam doses, enabling comparative studies of resist graphitization
mechanisms between electron beam and UV photon exposure.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QCheckBox, QPushButton, QTextEdit, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QSpinBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from typing import Dict, List, Tuple
import numpy as np


class UVEquivalenceWidget(QWidget):
    """Widget for UV-ebeam energy equivalence calculations"""
    
    parameters_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Default parameters
        self.enabled = False
        self.uv_fluence_rate = 0.060  # J/cm²/min at 4" from 254nm lamp
        self.uv_absorptance = 0.3     # Estimated for alucone at 254nm
        self.ebeam_doses = [500, 1000, 2000, 5000, 10000, 15000]  # µC/cm²
        
        # Calculated values (will be updated from simulation)
        self.energy_absorption_coefficient = 0.0  # J/cm² per µC/cm²
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Enable/disable group
        enable_group = QGroupBox("UV Energy Equivalence Analysis")
        enable_layout = QHBoxLayout(enable_group)
        
        self.enable_checkbox = QCheckBox("Enable UV equivalence calculations")
        self.enable_checkbox.setToolTip(
            "Generate UV-equivalent exposure times for comparing e-beam and UV resist effects"
        )
        enable_layout.addWidget(self.enable_checkbox)
        
        enable_layout.addStretch()
        
        self.help_btn = QPushButton("Scientific Background")
        self.help_btn.setMaximumWidth(150)
        enable_layout.addWidget(self.help_btn)
        
        layout.addWidget(enable_group)
        
        # UV parameters group
        self.params_group = QGroupBox("UV Lamp Parameters")
        params_layout = QGridLayout(self.params_group)
        
        # UV fluence rate
        params_layout.addWidget(QLabel("UV fluence rate (J/cm²/min):"), 0, 0)
        self.fluence_spin = QDoubleSpinBox()
        self.fluence_spin.setRange(0.001, 1.0)
        self.fluence_spin.setDecimals(4)
        self.fluence_spin.setSingleStep(0.001)
        self.fluence_spin.setValue(self.uv_fluence_rate)
        self.fluence_spin.setToolTip("Measured UV power density at your working distance")
        params_layout.addWidget(self.fluence_spin, 0, 1)
        
        # UV wavelength info (read-only)
        params_layout.addWidget(QLabel("UV wavelength:"), 1, 0)
        wavelength_label = QLabel("254 nm (optimized for this wavelength)")
        wavelength_label.setStyleSheet("color: #888888; font-style: italic;")
        params_layout.addWidget(wavelength_label, 1, 1)
        
        # UV absorptance
        params_layout.addWidget(QLabel("Resist absorptance at 254 nm:"), 2, 0)
        self.absorptance_spin = QDoubleSpinBox()
        self.absorptance_spin.setRange(0.01, 1.0)
        self.absorptance_spin.setDecimals(3)
        self.absorptance_spin.setSingleStep(0.01)
        self.absorptance_spin.setValue(self.uv_absorptance)
        self.absorptance_spin.setToolTip("Fraction of UV light absorbed by the resist (0.1 = 10%)")
        params_layout.addWidget(self.absorptance_spin, 2, 1)
        
        # Measurement instructions
        instruction_label = QLabel("💡 Measure these parameters using UV power meter and UV-Vis spectroscopy")
        instruction_label.setStyleSheet("color: #4A90E2; font-weight: bold; padding: 5px;")
        params_layout.addWidget(instruction_label, 3, 0, 1, 2)
        
        layout.addWidget(self.params_group)
        
        # E-beam doses group
        doses_group = QGroupBox("E-beam Dose Range for Equivalence")
        doses_layout = QVBoxLayout(doses_group)
        
        # Preset dose ranges
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset ranges:"))
        
        self.low_dose_btn = QPushButton("Low (100-1000 µC/cm²)")
        self.med_dose_btn = QPushButton("Medium (1000-10000 µC/cm²)")
        self.high_dose_btn = QPushButton("High (5000-20000 µC/cm²)")
        self.graphitization_btn = QPushButton("Graphitization (10000+ µC/cm²)")
        
        for btn in [self.low_dose_btn, self.med_dose_btn, self.high_dose_btn, self.graphitization_btn]:
            btn.setMaximumWidth(200)
            preset_layout.addWidget(btn)
        
        preset_layout.addStretch()
        doses_layout.addLayout(preset_layout)
        
        # Custom dose input
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom doses (µC/cm²):"))
        
        self.doses_edit = QTextEdit()
        self.doses_edit.setMaximumHeight(60)
        self.doses_edit.setPlaceholderText("500, 1000, 2000, 5000, 10000, 15000")
        self.doses_edit.setPlainText(", ".join(map(str, self.ebeam_doses)))
        custom_layout.addWidget(self.doses_edit)
        
        doses_layout.addLayout(custom_layout)
        layout.addWidget(doses_group)
        
        # Results table
        self.results_group = QGroupBox("UV Equivalence Results")
        results_layout = QVBoxLayout(self.results_group)
        
        # Energy coefficient display
        coeff_layout = QHBoxLayout()
        coeff_layout.addWidget(QLabel("Energy absorption coefficient K:"))
        self.coeff_label = QLabel("Not calculated yet (run simulation)")
        self.coeff_label.setStyleSheet("font-weight: bold; color: #E2A440;")
        coeff_layout.addWidget(self.coeff_label)
        coeff_layout.addStretch()
        results_layout.addLayout(coeff_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels([
            "E-beam Dose (µC/cm²)", 
            "Absorbed Energy (J/cm²)", 
            "UV Time Required (min)"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setMaximumHeight(200)
        results_layout.addWidget(self.results_table)
        
        # Export button
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export Equivalence Table")
        self.export_btn.setMaximumWidth(200)
        export_layout.addWidget(self.export_btn)
        results_layout.addLayout(export_layout)
        
        layout.addWidget(self.results_group)
        
        # Initially disable parameter groups
        self.params_group.setEnabled(False)
        self.results_group.setEnabled(False)
        
    def connect_signals(self):
        """Connect widget signals"""
        self.enable_checkbox.toggled.connect(self.on_enable_toggled)
        self.fluence_spin.valueChanged.connect(self.on_parameters_changed)
        self.absorptance_spin.valueChanged.connect(self.on_parameters_changed)
        self.doses_edit.textChanged.connect(self.on_doses_changed)
        
        # Preset buttons
        self.low_dose_btn.clicked.connect(lambda: self.set_dose_preset([100, 250, 500, 750, 1000]))
        self.med_dose_btn.clicked.connect(lambda: self.set_dose_preset([1000, 2500, 5000, 7500, 10000]))
        self.high_dose_btn.clicked.connect(lambda: self.set_dose_preset([5000, 10000, 15000, 20000]))
        self.graphitization_btn.clicked.connect(lambda: self.set_dose_preset([10000, 15000, 20000, 30000, 50000]))
        
        self.help_btn.clicked.connect(self.show_scientific_background)
        self.export_btn.clicked.connect(self.export_results)
        
    def on_enable_toggled(self, enabled: bool):
        """Handle enable/disable of UV equivalence"""
        self.enabled = enabled
        self.params_group.setEnabled(enabled)
        self.results_group.setEnabled(enabled)
        self.parameters_changed.emit()
        
    def on_parameters_changed(self):
        """Handle parameter changes"""
        self.uv_fluence_rate = self.fluence_spin.value()
        self.uv_absorptance = self.absorptance_spin.value()
        self.update_calculations()
        self.parameters_changed.emit()
        
    def on_doses_changed(self):
        """Handle dose range changes"""
        try:
            dose_text = self.doses_edit.toPlainText().strip()
            self.ebeam_doses = [float(x.strip()) for x in dose_text.split(",") if x.strip()]
            self.update_calculations()
        except ValueError:
            pass  # Invalid input, ignore
            
    def set_dose_preset(self, doses: List[float]):
        """Set preset dose range"""
        self.ebeam_doses = doses
        self.doses_edit.setPlainText(", ".join(map(str, doses)))
        self.update_calculations()
        
    def update_energy_coefficient(self, coefficient: float):
        """Update energy absorption coefficient from simulation results"""
        self.energy_absorption_coefficient = coefficient
        self.coeff_label.setText(f"{coefficient:.3e} J/cm² per µC/cm²")
        self.coeff_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.update_calculations()
        
    def update_calculations(self):
        """Update equivalence calculations and table"""
        if not self.enabled or self.energy_absorption_coefficient == 0.0:
            return
            
        # Calculate UV equivalence for each e-beam dose
        results = []
        for dose in self.ebeam_doses:
            absorbed_energy = self.energy_absorption_coefficient * dose
            uv_absorbed_rate = self.uv_fluence_rate * self.uv_absorptance
            if uv_absorbed_rate > 0:
                uv_time = absorbed_energy / uv_absorbed_rate
                results.append((dose, absorbed_energy, uv_time))
            else:
                results.append((dose, absorbed_energy, 0.0))
        
        # Update table
        self.results_table.setRowCount(len(results))
        for i, (dose, energy, time) in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(f"{dose:.0f}"))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"{energy:.3e}"))
            self.results_table.setItem(i, 2, QTableWidgetItem(f"{time:.1f}"))
            
    def show_scientific_background(self):
        """Show scientific background dialog"""
        background_text = """
<h3>Scientific Background: E-beam to UV Energy Equivalence</h3>

<p><b>Goal:</b> Compare graphitization and chemistry changes in resist materials 
between high-dose e-beam irradiation and UV exposure on an energy-density basis.</p>

<p><b>Why Energy Equivalence Matters:</b></p>
<ul>
<li><b>E-beam:</b> Delivers energy via ionization/secondary electrons (spatially distributed)</li>
<li><b>UV photons:</b> Deposit energy only where absorbed (surface/optical depth limited)</li>
<li><b>Common scale:</b> Absorbed energy density in resist film (J/cm²)</li>
</ul>

<p><b>Scientific Questions:</b></p>
<ul>
<li>Is resist transformation energy-density driven or mechanism-specific?</li>
<li>Can UV serve as a cheap, scalable proxy for ultra-high e-beam doses?</li>
<li>Do graphitization thresholds correlate with absorbed J/cm²?</li>
</ul>

<p><b>Calculation Method:</b></p>
<ol>
<li>Simulate e-beam energy absorption per primary electron in resist</li>
<li>Calculate coefficient K = E_film × conversion_factor</li>
<li>For each e-beam dose D: E_abs = K × D</li>
<li>UV equivalent time = E_abs / (UV_rate × Absorptance)</li>
</ol>

<p><b>Usage:</b></p>
<ol>
<li>Measure your UV lamp's fluence rate with power meter</li>
<li>Measure resist absorptance at 254 nm with UV-Vis spectroscopy</li>
<li>Run simulation to get energy absorption coefficient</li>
<li>Use calculated UV times for comparative exposure experiments</li>
</ol>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("UV Energy Equivalence - Scientific Background")
        msg.setText(background_text)
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        
    def export_results(self):
        """Export results to CSV file"""
        if not self.enabled or self.energy_absorption_coefficient == 0.0:
            QMessageBox.warning(self, "No Results", "No equivalence results to export. Run simulation first.")
            return
            
        from PySide6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export UV Equivalence Results", 
            "uv_equivalence_results.csv",
            "CSV files (*.csv)"
        )
        
        if not filename:
            return
            
        try:
            import csv
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header with parameters
                writer.writerow(["# UV Energy Equivalence Results"])
                writer.writerow(["# Generated by EBL Simulation Suite"])
                writer.writerow([f"# UV fluence rate: {self.uv_fluence_rate} J/cm²/min"])
                writer.writerow([f"# UV absorptance: {self.uv_absorptance}"])
                writer.writerow([f"# Energy coefficient K: {self.energy_absorption_coefficient:.6e} J/cm² per µC/cm²"])
                writer.writerow([])
                
                # Write data
                writer.writerow(["E-beam_Dose_uC_cm2", "Absorbed_Energy_J_cm2", "UV_Time_Required_min"])
                
                for dose in self.ebeam_doses:
                    absorbed_energy = self.energy_absorption_coefficient * dose
                    uv_absorbed_rate = self.uv_fluence_rate * self.uv_absorptance
                    uv_time = absorbed_energy / uv_absorbed_rate if uv_absorbed_rate > 0 else 0.0
                    writer.writerow([dose, absorbed_energy, uv_time])
                    
            QMessageBox.information(self, "Export Complete", f"Results exported to:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}")
            
    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            "enabled": self.enabled,
            "uv_fluence_rate": self.uv_fluence_rate,
            "uv_absorptance": self.uv_absorptance,
            "ebeam_doses": self.ebeam_doses,
            "energy_absorption_coefficient": self.energy_absorption_coefficient
        }
        
    def set_config(self, config: Dict):
        """Set configuration"""
        self.enabled = config.get("enabled", False)
        self.uv_fluence_rate = config.get("uv_fluence_rate", 0.060)
        self.uv_absorptance = config.get("uv_absorptance", 0.3)
        self.ebeam_doses = config.get("ebeam_doses", [500, 1000, 2000, 5000, 10000, 15000])
        self.energy_absorption_coefficient = config.get("energy_absorption_coefficient", 0.0)
        
        # Update UI
        self.enable_checkbox.setChecked(self.enabled)
        self.fluence_spin.setValue(self.uv_fluence_rate)
        self.absorptance_spin.setValue(self.uv_absorptance)
        self.doses_edit.setPlainText(", ".join(map(str, self.ebeam_doses)))
        
        if self.energy_absorption_coefficient > 0:
            self.update_energy_coefficient(self.energy_absorption_coefficient)