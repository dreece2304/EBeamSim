#!/usr/bin/env python3
"""
EBL Visualization - Embedded Controller
Embeds Geant4 OpenGL window directly into the Python Qt application
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QSpinBox, QGroupBox, QGridLayout,
    QTextEdit, QFrame, QLineEdit, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, QProcess, QTimer, Signal, QSize
from PySide6.QtGui import QFont, QTextCursor, QWindow


class Geant4Process(QProcess):
    """Geant4 process with command interface"""

    output_received = Signal(str)

    def __init__(self, exe_path: str, parent=None):
        super().__init__(parent)
        self.exe_path = exe_path
        self.readyReadStandardOutput.connect(self._handle_stdout)
        self.readyReadStandardError.connect(self._handle_stderr)

    def _handle_stdout(self):
        data = self.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.output_received.emit(data)

    def _handle_stderr(self):
        data = self.readAllStandardError().data().decode('utf-8', errors='replace')
        self.output_received.emit(data)

    def start_geant4(self):
        exe_dir = Path(self.exe_path).parent
        self.setWorkingDirectory(str(exe_dir))

        # Set environment for Geant4 libraries and display
        env = self.processEnvironment()

        # Pass through display environment from parent
        if os.environ.get("DISPLAY"):
            env.insert("DISPLAY", os.environ["DISPLAY"])
        if os.environ.get("WAYLAND_DISPLAY"):
            env.insert("WAYLAND_DISPLAY", os.environ["WAYLAND_DISPLAY"])
        if os.environ.get("XDG_RUNTIME_DIR"):
            env.insert("XDG_RUNTIME_DIR", os.environ["XDG_RUNTIME_DIR"])

        # Add Geant4 library path
        geant4_lib = "/opt/geant4/lib"
        current_ld = env.value("LD_LIBRARY_PATH", "")
        if geant4_lib not in current_ld:
            env.insert("LD_LIBRARY_PATH", f"{geant4_lib}:{current_ld}" if current_ld else geant4_lib)

        # Add Geant4 data paths if needed
        env.insert("G4ENSDFSTATEDATA", "/opt/geant4/share/Geant4/data/G4ENSDFSTATE2.3")
        env.insert("G4LEDATA", "/opt/geant4/share/Geant4/data/G4EMLOW8.2")
        env.insert("G4LEVELGAMMADATA", "/opt/geant4/share/Geant4/data/PhotonEvaporation5.7")
        env.insert("G4PARTICLEXSDATA", "/opt/geant4/share/Geant4/data/G4PARTICLEXS4.0")
        env.insert("G4SAIDXSDATA", "/opt/geant4/share/Geant4/data/G4SAIDDATA2.0")

        self.setProcessEnvironment(env)

        # Use -p (pipe mode) to read commands from stdin with visualization
        self.start(self.exe_path, ["-p"])

    def send_command(self, cmd: str):
        if self.state() == QProcess.Running:
            self.write(f"{cmd}\n".encode())


class EmbeddedVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ EBL Electron Scattering Visualizer")
        self.setMinimumSize(1400, 900)

        self.exe_path = self._find_executable()
        self.process: Optional[Geant4Process] = None
        self.g4_window_id = None
        self.embedded_window = None
        self.embed_retry_count = 0

        self._setup_ui()
        self._apply_style()

        # Don't auto-launch - let user click the button
        # QTimer.singleShot(500, self.launch_viewer)

    def _find_executable(self):
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
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left panel - Controls (collapsible width)
        left_panel = QWidget()
        left_panel.setMaximumWidth(320)
        left_panel.setMinimumWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Header with status
        header = QHBoxLayout()
        title = QLabel("⚡ Controls")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        header.addWidget(title)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #ff4444; font-size: 16px;")
        header.addWidget(self.status_dot)
        header.addStretch()
        left_layout.addLayout(header)

        # Material
        mat_group = self._create_material_group()
        left_layout.addWidget(mat_group)

        # Beam
        beam_group = self._create_beam_group()
        left_layout.addWidget(beam_group)

        # Run controls
        run_group = self._create_run_group()
        left_layout.addWidget(run_group)

        # View controls
        view_group = self._create_view_group()
        left_layout.addWidget(view_group)

        # Export
        export_group = self._create_export_group()
        left_layout.addWidget(export_group)

        left_layout.addStretch()

        # Launch/Restart buttons at bottom
        self.launch_btn = QPushButton("🚀 Launch Viewer")
        self.launch_btn.setStyleSheet("background-color: #1a4a2a; font-weight: bold; font-size: 12px; padding: 10px;")
        self.launch_btn.clicked.connect(self.launch_viewer)
        left_layout.addWidget(self.launch_btn)

        restart_btn = QPushButton("🔄 Restart Viewer")
        restart_btn.clicked.connect(self.restart_viewer)
        left_layout.addWidget(restart_btn)

        # Right panel - Embedded viewer + output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Viewer container (where Geant4 window will be embedded)
        self.viewer_container = QWidget()
        self.viewer_container.setMinimumSize(800, 600)
        self.viewer_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.viewer_container.setStyleSheet("background-color: #000010;")

        viewer_layout = QVBoxLayout(self.viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)

        self.viewer_placeholder = QLabel("Click 'Launch' to start Geant4 visualization")
        self.viewer_placeholder.setAlignment(Qt.AlignCenter)
        self.viewer_placeholder.setStyleSheet("color: #666; font-size: 18px;")
        viewer_layout.addWidget(self.viewer_placeholder)

        right_layout.addWidget(self.viewer_container, stretch=4)

        # Output panel (collapsible)
        output_widget = QWidget()
        output_widget.setMaximumHeight(150)
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(5, 5, 5, 5)
        output_layout.setSpacing(2)

        output_header = QHBoxLayout()
        output_label = QLabel("📟 Output")
        output_label.setFont(QFont("Arial", 10, QFont.Bold))
        output_header.addWidget(output_label)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Type command and press Enter...")
        self.cmd_input.returnPressed.connect(self.send_custom_cmd)
        output_header.addWidget(self.cmd_input, stretch=1)

        output_layout.addLayout(output_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(100)
        self.output_text.setFont(QFont("Consolas", 8))
        output_layout.addWidget(self.output_text)

        right_layout.addWidget(output_widget)

        # Add to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

    def _create_material_group(self):
        group = QGroupBox("📦 Material")
        layout = QGridLayout(group)
        layout.setSpacing(5)

        self.material_combo = QComboBox()
        self.materials = {
            "Zincone (Zn, Z=30)": ("Zn:1,C:2,H:4,O:2", 2.1),
            "Alucone (Al, Z=13)": ("Al:1,C:5,H:4,O:2", 1.35),
            "Tincone (Sn, Z=50)": ("Sn:1,C:8,H:8,O:4", 2.0),
            "PMMA": ("C:5,H:8,O:2", 1.19),
            "HSQ": ("Si:1,H:1,O:1.5", 1.4),
        }
        self.material_combo.addItems(self.materials.keys())
        layout.addWidget(self.material_combo, 0, 0, 1, 2)

        layout.addWidget(QLabel("Thickness:"), 1, 0)
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(100, 10000)
        self.thickness_spin.setValue(2000)
        self.thickness_spin.setSuffix(" nm")
        self.thickness_spin.setSingleStep(100)
        layout.addWidget(self.thickness_spin, 1, 1)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_material)
        layout.addWidget(apply_btn, 2, 0, 1, 2)

        return group

    def _create_beam_group(self):
        group = QGroupBox("🔬 Beam")
        layout = QGridLayout(group)
        layout.setSpacing(5)

        layout.addWidget(QLabel("Energy:"), 0, 0)
        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(1, 300)
        self.energy_spin.setValue(100)
        self.energy_spin.setSuffix(" keV")
        layout.addWidget(self.energy_spin, 0, 1)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_beam)
        layout.addWidget(apply_btn, 1, 0, 1, 2)

        return group

    def _create_run_group(self):
        group = QGroupBox("▶️ Simulation")
        layout = QGridLayout(group)
        layout.setSpacing(5)

        layout.addWidget(QLabel("Electrons:"), 0, 0)
        self.events_spin = QSpinBox()
        self.events_spin.setRange(1, 1000)
        self.events_spin.setValue(50)
        layout.addWidget(self.events_spin, 0, 1)

        btn_layout = QHBoxLayout()

        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setStyleSheet("background-color: #1a5a2a; font-weight: bold;")
        self.run_btn.clicked.connect(self.run_events)
        btn_layout.addWidget(self.run_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_trajectories)
        btn_layout.addWidget(clear_btn)

        layout.addLayout(btn_layout, 1, 0, 1, 2)

        return group

    def _create_view_group(self):
        group = QGroupBox("🎥 View")
        layout = QGridLayout(group)
        layout.setSpacing(3)

        zoom_in = QPushButton("+")
        zoom_in.setMaximumWidth(40)
        zoom_in.clicked.connect(lambda: self.send_cmd("/vis/viewer/zoom 1.5"))
        layout.addWidget(zoom_in, 0, 0)

        zoom_out = QPushButton("-")
        zoom_out.setMaximumWidth(40)
        zoom_out.clicked.connect(lambda: self.send_cmd("/vis/viewer/zoom 0.67"))
        layout.addWidget(zoom_out, 0, 1)

        focus = QPushButton("Focus")
        focus.setToolTip("Center view on resist surface")
        focus.clicked.connect(self.focus_on_resist)
        layout.addWidget(focus, 0, 2)

        reset = QPushButton("Reset")
        reset.clicked.connect(self.reset_view)
        layout.addWidget(reset, 0, 3)

        return group

    def _create_export_group(self):
        group = QGroupBox("💾 Export")
        layout = QHBoxLayout(group)
        layout.setSpacing(3)

        self.export_name = QLineEdit("scatter")
        self.export_name.setMaximumWidth(100)
        layout.addWidget(self.export_name)

        pdf_btn = QPushButton("PDF")
        pdf_btn.clicked.connect(lambda: self.export_image("pdf"))
        layout.addWidget(pdf_btn)

        eps_btn = QPushButton("EPS")
        eps_btn.clicked.connect(lambda: self.export_image("eps"))
        layout.addWidget(eps_btn)

        return group

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0d0d14;
                color: #e0e0e0;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 10px;
                border: 1px solid #2a2a4a;
                border-radius: 5px;
                margin-top: 10px;
                padding: 8px;
                padding-top: 18px;
                background-color: #14141e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
                color: #00c8ff;
            }
            QPushButton {
                background-color: #1e1e32;
                border: 1px solid #3a3a5a;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2a2a4a;
                border-color: #00c8ff;
            }
            QPushButton:pressed {
                background-color: #141428;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #0a0a12;
                border: 1px solid #2a2a4a;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
                border-color: #00c8ff;
            }
            QTextEdit {
                background-color: #06060a;
                border: 1px solid #1a1a2a;
                border-radius: 3px;
                color: #00ff80;
                font-size: 9px;
            }
            QLabel {
                color: #a0a0a0;
                font-size: 11px;
            }
        """)

    def launch_viewer(self):
        """Launch Geant4 and attempt to embed its window"""
        if self.process and self.process.state() == QProcess.Running:
            return

        self.launch_btn.setEnabled(False)
        self.launch_btn.setText("Starting...")
        self.viewer_placeholder.setText("🔄 Starting Geant4...")

        self.process = Geant4Process(self.exe_path, self)
        self.process.output_received.connect(self.append_output)
        self.process.finished.connect(self.on_process_finished)
        self.process.start_geant4()

        self.status_dot.setStyleSheet("color: #44ff44; font-size: 16px;")
        self.launch_btn.setText("✓ Running")

        # Try to find and embed the window after a delay (with retries)
        self.embed_retry_count = 0
        QTimer.singleShot(2000, self.try_embed_window)

    def try_embed_window(self):
        """Try to find and embed the Geant4 OpenGL window"""
        xdotool_path = "/usr/bin/xdotool"

        # Try different window name patterns that Geant4 might use
        search_patterns = ["OpenGL", "G4OpenGL", "ebl_sim", "OGL"]

        for pattern in search_patterns:
            try:
                result = subprocess.run(
                    [xdotool_path, "search", "--name", pattern],
                    capture_output=True, text=True, timeout=5
                )

                if result.stdout.strip():
                    window_ids = result.stdout.strip().split('\n')
                    for wid in window_ids:
                        try:
                            self.g4_window_id = int(wid)
                            self.embed_window(self.g4_window_id)
                            self.append_output(f"[Found window '{pattern}' (ID: {wid})]\n")
                            return
                        except ValueError:
                            continue
            except subprocess.TimeoutExpired:
                continue
            except FileNotFoundError:
                self.append_output("[xdotool not found - running in separate window mode]\n")
                break
            except Exception as e:
                self.append_output(f"[Window search error: {e}]\n")
                continue

        # Retry a few times before giving up
        self.embed_retry_count += 1
        if self.embed_retry_count < 5:
            self.viewer_placeholder.setText(f"🔄 Looking for viewer window... (attempt {self.embed_retry_count}/5)")
            QTimer.singleShot(1500, self.try_embed_window)
        else:
            # If embedding failed after retries, show message
            self.viewer_placeholder.setText(
                "Geant4 viewer running in separate window.\n"
                "Use controls on the left to interact."
            )
            self.append_output("[Could not embed window - using separate window mode]\n")

    def embed_window(self, window_id: int):
        """Embed external window into our container"""
        try:
            # Create a QWindow from the foreign window ID
            foreign_window = QWindow.fromWinId(window_id)
            if foreign_window is None:
                self.append_output(f"[Could not create window from ID {window_id}]\n")
                return

            # Create a container widget for the foreign window
            container = QWidget.createWindowContainer(foreign_window, self.viewer_container)
            if container is None:
                self.append_output("[Could not create window container]\n")
                return

            container.setMinimumSize(800, 600)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Replace placeholder with embedded window
            layout = self.viewer_container.layout()
            layout.removeWidget(self.viewer_placeholder)
            self.viewer_placeholder.hide()
            layout.addWidget(container)

            self.embedded_window = container
            self.append_output("[Window embedded successfully]\n")

        except RuntimeError as e:
            # Common when window ID is invalid or window was destroyed
            self.append_output(f"[Embed failed - window may have closed: {e}]\n")
        except Exception as e:
            self.append_output(f"[Embed error: {e}]\n")

    def restart_viewer(self):
        """Restart the Geant4 viewer"""
        if self.process and self.process.state() == QProcess.Running:
            self.send_cmd("exit")
            self.process.waitForFinished(2000)
            if self.process.state() == QProcess.Running:
                self.process.kill()

        # Reset UI
        if self.embedded_window:
            self.embedded_window.hide()
            self.embedded_window.deleteLater()
            self.embedded_window = None

        self.viewer_placeholder.setText("🔄 Restarting...")
        self.viewer_placeholder.show()

        QTimer.singleShot(500, self.launch_viewer)

    def on_process_finished(self):
        self.status_dot.setStyleSheet("color: #ff4444; font-size: 16px;")
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText("🚀 Launch Viewer")
        self.viewer_placeholder.setText("Viewer stopped. Click 'Launch Viewer' to start again.")
        self.viewer_placeholder.show()

    def send_cmd(self, cmd: str):
        if self.process and self.process.state() == QProcess.Running:
            self.process.send_command(cmd)
            self.append_output(f">>> {cmd}\n")

    def append_output(self, text: str):
        # Limit output size
        if self.output_text.document().characterCount() > 50000:
            self.output_text.clear()
        self.output_text.moveCursor(QTextCursor.End)
        self.output_text.insertPlainText(text)
        self.output_text.moveCursor(QTextCursor.End)

    def apply_material(self):
        mat_name = self.material_combo.currentText()
        comp, density = self.materials[mat_name]
        thickness = self.thickness_spin.value()

        for cmd in [
            # Set new parameters
            f"/det/setResistComposition {comp}",
            f"/det/setResistDensity {density} g/cm3",
            f"/det/setResistThickness {thickness} nm",
            # Rebuild geometry from scratch (needed for size changes)
            "/run/reinitializeGeometry",
            "/run/initialize",
            # Redraw and recolor
            "/vis/viewer/rebuild",
            "/vis/geometry/set/colour Resist 0 0.2 0.7 0.8 0.6",
            "/vis/geometry/set/colour Substrate 0 0.3 0.3 0.35 1.0",
            # Update gun position for new thickness
            f"/gun/position 0 0 {thickness + 50} nm",
        ]:
            self.send_cmd(cmd)

    def apply_beam(self):
        energy = self.energy_spin.value()
        thickness = self.thickness_spin.value()
        for cmd in [
            f"/gun/energy {energy} keV",
            f"/gun/position 0 0 {thickness + 50} nm",  # 50nm above resist surface
        ]:
            self.send_cmd(cmd)

    def run_events(self):
        # Run events
        self.send_cmd(f"/run/beamOn {self.events_spin.value()}")
        # Flush viewer to show accumulated trajectories
        self.send_cmd("/vis/viewer/flush")

    def clear_trajectories(self):
        # Clear all trajectories and redraw geometry
        self.send_cmd("/vis/viewer/clear")
        self.send_cmd("/vis/drawVolume")
        # Restore accumulate mode
        self.send_cmd("/vis/scene/endOfEventAction accumulate 200")

    def focus_on_resist(self):
        """Center view on resist and zoom in close"""
        thickness = self.thickness_spin.value()
        # Reset and set up side view
        self.send_cmd("/vis/viewer/reset")
        self.send_cmd("/vis/viewer/set/upVector 0 0 1")
        self.send_cmd("/vis/viewer/set/viewpointVector 0 1 0")
        # Target middle of resist (bottom=0, top=thickness)
        self.send_cmd(f"/vis/viewer/set/targetPoint 0 0 {thickness * 0.5} nm")
        # Dolly camera closer to target (negative = closer)
        self.send_cmd(f"/vis/viewer/dolly {-thickness * 10} nm")
        self.send_cmd("/vis/viewer/zoom 2")

    def reset_view(self):
        """Reset to default side view showing full geometry"""
        thickness = self.thickness_spin.value()
        self.send_cmd("/vis/viewer/reset")
        self.send_cmd("/vis/viewer/set/upVector 0 0 1")
        self.send_cmd("/vis/viewer/set/viewpointVector 0 1 0")
        self.send_cmd(f"/vis/viewer/set/targetPoint 0 0 {thickness * 0.5} nm")

    def export_image(self, fmt: str):
        name = self.export_name.text() or "export"
        self.send_cmd(f"/vis/ogl/export {name}.{fmt}")

    def send_custom_cmd(self):
        cmd = self.cmd_input.text().strip()
        if cmd:
            self.send_cmd(cmd)
            self.cmd_input.clear()

    def closeEvent(self, event):
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = EmbeddedVisualizer()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
