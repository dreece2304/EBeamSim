#!/usr/bin/env python3
"""
EBL Visualization Controller
Real-time control of Geant4 electron scattering visualization
Sends commands directly to the running Geant4 process
"""

import sys
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QTextEdit, QSlider, QFrame,
    QSplitter, QToolButton, QButtonGroup, QLineEdit
)
from PySide6.QtCore import Qt, QProcess, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QTextCursor, QIcon, QColor


class Geant4Process(QProcess):
    """Wrapper for Geant4 process with command interface"""

    output_received = Signal(str)
    error_received = Signal(str)

    def __init__(self, exe_path: str, parent=None):
        super().__init__(parent)
        self.exe_path = exe_path

        self.readyReadStandardOutput.connect(self._handle_stdout)
        self.readyReadStandardError.connect(self._handle_stderr)
        self.finished.connect(self._handle_finished)

    def _handle_stdout(self):
        data = self.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.output_received.emit(data)

    def _handle_stderr(self):
        data = self.readAllStandardError().data().decode('utf-8', errors='replace')
        self.error_received.emit(data)

    def _handle_finished(self):
        self.output_received.emit("\n[Process finished]\n")

    def start_geant4(self):
        """Start the Geant4 process in interactive mode"""
        exe_dir = Path(self.exe_path).parent
        self.setWorkingDirectory(str(exe_dir))

        # Set environment for Geant4 libraries
        env = self.processEnvironment()
        geant4_lib = "/opt/geant4/lib"
        current_ld = env.value("LD_LIBRARY_PATH", "")
        if geant4_lib not in current_ld:
            env.insert("LD_LIBRARY_PATH", f"{geant4_lib}:{current_ld}" if current_ld else geant4_lib)
        self.setProcessEnvironment(env)

        self.start(self.exe_path, ["-u"])

    def send_command(self, cmd: str):
        """Send a command to Geant4"""
        if self.state() == QProcess.Running:
            self.write(f"{cmd}\n".encode())
            self.output_received.emit(f">>> {cmd}\n")


class VisController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ EBL Visualization Controller")
        self.setMinimumSize(900, 700)

        self.exe_path = self._find_executable()
        self.process: Optional[Geant4Process] = None

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
        return "ebl_sim"

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        left_panel.setMaximumWidth(350)

        # Title
        title = QLabel("⚡ EBL Visualizer")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)

        # Connection status
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(self.status_frame)
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #ff4444; font-size: 20px;")
        self.status_label = QLabel("Disconnected")
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        left_layout.addWidget(self.status_frame)

        # Launch/Stop buttons
        launch_layout = QHBoxLayout()
        self.launch_btn = QPushButton("🚀 Launch")
        self.launch_btn.clicked.connect(self.launch_viewer)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_viewer)
        self.stop_btn.setEnabled(False)
        launch_layout.addWidget(self.launch_btn)
        launch_layout.addWidget(self.stop_btn)
        left_layout.addLayout(launch_layout)

        # Material Selection
        mat_group = QGroupBox("📦 Material")
        mat_layout = QGridLayout(mat_group)

        self.material_combo = QComboBox()
        self.materials = {
            "Zincone (Zn)": ("Zn:1,C:2,H:4,O:2", 2.1),
            "Alucone (Al)": ("Al:1,C:5,H:4,O:2", 1.35),
            "Tincone (Sn)": ("Sn:1,C:8,H:8,O:4", 2.0),
            "PMMA": ("C:5,H:8,O:2", 1.19),
            "HSQ": ("Si:1,H:1,O:1.5", 1.4),
        }
        self.material_combo.addItems(self.materials.keys())
        mat_layout.addWidget(QLabel("Type:"), 0, 0)
        mat_layout.addWidget(self.material_combo, 0, 1)

        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(100, 10000)
        self.thickness_spin.setValue(2000)
        self.thickness_spin.setSuffix(" nm")
        self.thickness_spin.setSingleStep(100)
        mat_layout.addWidget(QLabel("Thickness:"), 1, 0)
        mat_layout.addWidget(self.thickness_spin, 1, 1)

        self.apply_material_btn = QPushButton("Apply Material")
        self.apply_material_btn.clicked.connect(self.apply_material)
        mat_layout.addWidget(self.apply_material_btn, 2, 0, 1, 2)

        left_layout.addWidget(mat_group)

        # Beam Settings
        beam_group = QGroupBox("🔬 Beam")
        beam_layout = QGridLayout(beam_group)

        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(1, 300)
        self.energy_spin.setValue(100)
        self.energy_spin.setSuffix(" keV")
        beam_layout.addWidget(QLabel("Energy:"), 0, 0)
        beam_layout.addWidget(self.energy_spin, 0, 1)

        self.apply_beam_btn = QPushButton("Apply Beam")
        self.apply_beam_btn.clicked.connect(self.apply_beam)
        beam_layout.addWidget(self.apply_beam_btn, 1, 0, 1, 2)

        left_layout.addWidget(beam_group)

        # Run Controls
        run_group = QGroupBox("▶️ Simulation")
        run_layout = QGridLayout(run_group)

        self.events_spin = QSpinBox()
        self.events_spin.setRange(1, 1000)
        self.events_spin.setValue(50)
        run_layout.addWidget(QLabel("Electrons:"), 0, 0)
        run_layout.addWidget(self.events_spin, 0, 1)

        run_btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setStyleSheet("background-color: #2d8a4e;")
        self.run_btn.clicked.connect(self.run_events)
        run_btn_layout.addWidget(self.run_btn)

        self.clear_btn = QPushButton("🗑 Clear")
        self.clear_btn.clicked.connect(self.clear_trajectories)
        run_btn_layout.addWidget(self.clear_btn)

        run_layout.addLayout(run_btn_layout, 1, 0, 1, 2)

        left_layout.addWidget(run_group)

        # View Controls
        view_group = QGroupBox("🎥 View")
        view_layout = QGridLayout(view_group)

        zoom_layout = QHBoxLayout()
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(lambda: self.send_cmd("/vis/viewer/zoom 1.5"))
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(lambda: self.send_cmd("/vis/viewer/zoom 0.67"))
        reset_btn = QPushButton("⟲ Reset")
        reset_btn.clicked.connect(self.reset_view)
        zoom_layout.addWidget(zoom_in_btn)
        zoom_layout.addWidget(zoom_out_btn)
        zoom_layout.addWidget(reset_btn)
        view_layout.addLayout(zoom_layout, 0, 0, 1, 2)

        left_layout.addWidget(view_group)

        # Export
        export_group = QGroupBox("💾 Export")
        export_layout = QHBoxLayout(export_group)

        self.export_name = QLineEdit("electron_scatter")
        export_layout.addWidget(self.export_name)

        export_pdf_btn = QPushButton("PDF")
        export_pdf_btn.clicked.connect(lambda: self.export_image("pdf"))
        export_eps_btn = QPushButton("EPS")
        export_eps_btn.clicked.connect(lambda: self.export_image("eps"))
        export_layout.addWidget(export_pdf_btn)
        export_layout.addWidget(export_eps_btn)

        left_layout.addWidget(export_group)

        # Custom command
        cmd_group = QGroupBox("⌨️ Custom Command")
        cmd_layout = QHBoxLayout(cmd_group)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("/vis/viewer/zoom 2")
        self.cmd_input.returnPressed.connect(self.send_custom_cmd)
        cmd_layout.addWidget(self.cmd_input)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_custom_cmd)
        cmd_layout.addWidget(send_btn)

        left_layout.addWidget(cmd_group)

        left_layout.addStretch()

        # Right panel - Output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        output_label = QLabel("📟 Geant4 Output")
        output_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        right_layout.addWidget(self.output_text)

        clear_output_btn = QPushButton("Clear Output")
        clear_output_btn.clicked.connect(self.output_text.clear)
        right_layout.addWidget(clear_output_btn)

        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #12121a;
                color: #e0e0e0;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #3a3a5a;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
                padding-top: 20px;
                background-color: #1a1a28;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #00d4ff;
            }
            QPushButton {
                background-color: #2a2a4a;
                border: 1px solid #4a4a7a;
                border-radius: 5px;
                padding: 8px 15px;
                color: #ffffff;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #3a3a6a;
                border-color: #00d4ff;
            }
            QPushButton:pressed {
                background-color: #1a1a3a;
            }
            QPushButton:disabled {
                background-color: #1a1a2a;
                color: #555555;
                border-color: #2a2a3a;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #0a0a14;
                border: 1px solid #3a3a5a;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                selection-background-color: #00d4ff;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
                border-color: #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #00d4ff;
                margin-right: 8px;
            }
            QTextEdit {
                background-color: #08080f;
                border: 1px solid #2a2a4a;
                border-radius: 4px;
                color: #00ff88;
                selection-background-color: #00d4ff;
            }
            QLabel {
                color: #b0b0b0;
            }
            QFrame {
                background-color: #1a1a28;
                border-radius: 4px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2a2a4a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00d4ff;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
        """)

    def launch_viewer(self):
        """Launch Geant4 process"""
        if self.process and self.process.state() == QProcess.Running:
            return

        self.process = Geant4Process(self.exe_path, self)
        self.process.output_received.connect(self.append_output)
        self.process.error_received.connect(self.append_output)
        self.process.finished.connect(self.on_process_finished)

        self.process.start_geant4()

        self.status_indicator.setStyleSheet("color: #44ff44; font-size: 20px;")
        self.status_label.setText("Connected")
        self.launch_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_viewer(self):
        """Stop Geant4 process"""
        if self.process:
            self.send_cmd("exit")
            QTimer.singleShot(1000, self._force_stop)

    def _force_stop(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()

    def on_process_finished(self):
        self.status_indicator.setStyleSheet("color: #ff4444; font-size: 20px;")
        self.status_label.setText("Disconnected")
        self.launch_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def send_cmd(self, cmd: str):
        """Send command to Geant4"""
        if self.process and self.process.state() == QProcess.Running:
            self.process.send_command(cmd)

    def append_output(self, text: str):
        """Append text to output window"""
        self.output_text.moveCursor(QTextCursor.End)
        self.output_text.insertPlainText(text)
        self.output_text.moveCursor(QTextCursor.End)

    def apply_material(self):
        """Apply selected material settings"""
        mat_name = self.material_combo.currentText()
        comp, density = self.materials[mat_name]
        thickness = self.thickness_spin.value()

        commands = [
            f"/det/setResistComposition {comp}",
            f"/det/setResistDensity {density} g/cm3",
            f"/det/setResistThickness {thickness} nm",
            "/run/reinitialize",
            "/vis/drawVolume",
        ]
        for cmd in commands:
            self.send_cmd(cmd)

    def apply_beam(self):
        """Apply beam settings"""
        energy = self.energy_spin.value()
        thickness = self.thickness_spin.value()

        commands = [
            f"/gun/energy {energy} keV",
            f"/gun/position 0 0 {thickness + 500} nm",
        ]
        for cmd in commands:
            self.send_cmd(cmd)

    def run_events(self):
        """Run electron events"""
        n = self.events_spin.value()
        self.send_cmd(f"/run/beamOn {n}")

    def clear_trajectories(self):
        """Clear displayed trajectories"""
        self.send_cmd("/vis/scene/endOfEventAction refresh")

    def reset_view(self):
        """Reset camera view"""
        commands = [
            "/vis/viewer/set/viewpointVector 0 1 0",
            "/vis/viewer/set/upVector 0 0 1",
            "/vis/viewer/zoom 1",
            "/vis/viewer/set/targetPoint 0 0 1000 nm",
        ]
        for cmd in commands:
            self.send_cmd(cmd)

    def export_image(self, fmt: str):
        """Export current view"""
        name = self.export_name.text() or "export"
        self.send_cmd(f"/vis/ogl/export {name}.{fmt}")

    def send_custom_cmd(self):
        """Send custom command from input field"""
        cmd = self.cmd_input.text().strip()
        if cmd:
            self.send_cmd(cmd)
            self.cmd_input.clear()

    def closeEvent(self, event):
        """Clean up on close"""
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = VisController()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
