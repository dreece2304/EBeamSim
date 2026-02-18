#!/usr/bin/env python3
"""
EBL Visualization Launcher
A sleek GUI to control the Geant4 electron scattering visualization
"""

import sys
import subprocess
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QTextEdit, QSlider, QFrame
)
from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtGui import QFont, QPalette, QColor


class VisLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EBL Electron Scattering Visualizer")
        self.setMinimumSize(500, 600)
        self.process = None

        # Find the executable
        self.exe_path = self._find_executable()

        self._setup_ui()
        self._apply_style()

    def _find_executable(self):
        """Find the ebl_sim executable"""
        script_dir = Path(__file__).parent
        possible_paths = [
            script_dir.parent.parent / "build" / "bin" / "ebl_sim",
            Path.home() / "projects" / "research" / "ebl-simulation" / "build" / "bin" / "ebl_sim",
        ]
        for p in possible_paths:
            if p.exists():
                return str(p)
        return "ebl_sim"  # Hope it's in PATH

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("⚡ Electron Scattering Visualizer")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Material Selection
        mat_group = QGroupBox("Material")
        mat_layout = QGridLayout(mat_group)

        mat_layout.addWidget(QLabel("Resist:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems([
            "Zincone (Zn, Z=30)",
            "Alucone (Al, Z=13)",
            "Tincone (Sn, Z=50)",
            "PMMA (C₅H₈O₂)",
            "HSQ (SiH₁O₁.₅)"
        ])
        self.material_combo.setMinimumWidth(200)
        mat_layout.addWidget(self.material_combo, 0, 1)

        mat_layout.addWidget(QLabel("Thickness:"), 1, 0)
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(100, 10000)
        self.thickness_spin.setValue(2000)
        self.thickness_spin.setSuffix(" nm")
        self.thickness_spin.setSingleStep(100)
        mat_layout.addWidget(self.thickness_spin, 1, 1)

        layout.addWidget(mat_group)

        # Beam Settings
        beam_group = QGroupBox("Beam")
        beam_layout = QGridLayout(beam_group)

        beam_layout.addWidget(QLabel("Energy:"), 0, 0)
        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(1, 300)
        self.energy_spin.setValue(100)
        self.energy_spin.setSuffix(" keV")
        beam_layout.addWidget(self.energy_spin, 0, 1)

        beam_layout.addWidget(QLabel("Electrons:"), 1, 0)
        self.events_spin = QSpinBox()
        self.events_spin.setRange(1, 500)
        self.events_spin.setValue(50)
        beam_layout.addWidget(self.events_spin, 1, 1)

        layout.addWidget(beam_group)

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.launch_btn = QPushButton("🚀 Launch Viewer")
        self.launch_btn.setMinimumHeight(50)
        self.launch_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.launch_btn.clicked.connect(self.launch_viewer)
        btn_layout.addWidget(self.launch_btn)

        layout.addLayout(btn_layout)

        # Quick Commands (when viewer is running)
        cmd_group = QGroupBox("Quick Commands (paste in viewer)")
        cmd_layout = QVBoxLayout(cmd_group)

        self.cmd_text = QTextEdit()
        self.cmd_text.setMaximumHeight(150)
        self.cmd_text.setFont(QFont("Consolas", 10))
        self.cmd_text.setReadOnly(True)
        self._update_commands()
        cmd_layout.addWidget(self.cmd_text)

        copy_btn = QPushButton("📋 Copy Commands")
        copy_btn.clicked.connect(self._copy_commands)
        cmd_layout.addWidget(copy_btn)

        layout.addWidget(cmd_group)

        # Connect signals
        self.material_combo.currentIndexChanged.connect(self._update_commands)
        self.thickness_spin.valueChanged.connect(self._update_commands)
        self.energy_spin.valueChanged.connect(self._update_commands)
        self.events_spin.valueChanged.connect(self._update_commands)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #eaeaea;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a6a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #252545;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #00d4ff;
            }
            QPushButton {
                background-color: #4a4a8a;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a6aaa;
            }
            QPushButton:pressed {
                background-color: #3a3a6a;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #353555;
                border: 1px solid #4a4a6a;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QTextEdit {
                background-color: #0d0d1a;
                border: 1px solid #4a4a6a;
                border-radius: 4px;
                color: #00ff88;
            }
            QLabel {
                color: #cccccc;
            }
        """)

    def _get_material_params(self):
        """Get material parameters based on selection"""
        materials = {
            0: ("Zn:1,C:2,H:4,O:2", 2.1, "Zincone"),
            1: ("Al:1,C:5,H:4,O:2", 1.35, "Alucone"),
            2: ("Sn:1,C:8,H:8,O:4", 2.0, "Tincone"),
            3: ("C:5,H:8,O:2", 1.19, "PMMA"),
            4: ("Si:1,H:1,O:1.5", 1.4, "HSQ"),
        }
        return materials.get(self.material_combo.currentIndex(), materials[0])

    def _update_commands(self):
        comp, density, name = self._get_material_params()
        thickness = self.thickness_spin.value()
        energy = self.energy_spin.value()
        events = self.events_spin.value()

        commands = f"""/det/setResistComposition {comp}
/det/setResistDensity {density} g/cm3
/det/setResistThickness {thickness} nm
/gun/energy {energy} keV
/gun/position 0 0 {thickness + 500} nm
/run/reinitialize
/vis/drawVolume
/run/beamOn {events}"""

        self.cmd_text.setText(commands)

    def _copy_commands(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.cmd_text.toPlainText())
        self.status_label.setText("Commands copied to clipboard!")
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))

    def launch_viewer(self):
        """Launch the Geant4 visualization"""
        self.status_label.setText("Launching viewer...")

        # Generate a custom init macro
        comp, density, name = self._get_material_params()
        thickness = self.thickness_spin.value()
        energy = self.energy_spin.value()

        # Launch the process
        try:
            exe_dir = Path(self.exe_path).parent
            subprocess.Popen(
                [self.exe_path, "-u"],
                cwd=str(exe_dir),
                start_new_session=True
            )
            self.status_label.setText(f"Viewer launched! Use commands above to configure.")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = VisLauncher()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
