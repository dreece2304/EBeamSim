#!/usr/bin/env python3
"""
EBL Animation Generator GUI
Simple interface to create electron trajectory animations
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QProgressBar, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from trajectory_animator import ElectronAnimator


class AnimationWorker(QThread):
    """Worker thread for generating animation"""
    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, animator, output_file, fps, duration):
        super().__init__()
        self.animator = animator
        self.output_file = output_file
        self.fps = fps
        self.duration = duration

    def run(self):
        try:
            self.progress.emit("Generating trajectories...")
            self.animator.generate_trajectories(15)

            self.progress.emit("Creating animation frames...")
            output = self.animator.create_animation(
                output_file=self.output_file,
                fps=self.fps,
                duration=self.duration
            )
            self.finished.emit(output)
        except Exception as e:
            self.error.emit(str(e))


class AnimationGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EBL Electron Animation Generator")
        self.setMinimumSize(450, 400)

        self.worker = None
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Electron Trajectory Animator")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Material settings
        mat_group = QGroupBox("Material Settings")
        mat_layout = QGridLayout(mat_group)

        mat_layout.addWidget(QLabel("Resist:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems(["Zincone", "Alucone", "Tincone", "PMMA", "HSQ"])
        mat_layout.addWidget(self.material_combo, 0, 1)

        mat_layout.addWidget(QLabel("Thickness:"), 1, 0)
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(10, 5000)
        self.thickness_spin.setValue(100)
        self.thickness_spin.setSuffix(" nm")
        mat_layout.addWidget(self.thickness_spin, 1, 1)

        layout.addWidget(mat_group)

        # Beam settings
        beam_group = QGroupBox("Beam Settings")
        beam_layout = QGridLayout(beam_group)

        beam_layout.addWidget(QLabel("Energy:"), 0, 0)
        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(1, 300)
        self.energy_spin.setValue(100)
        self.energy_spin.setSuffix(" keV")
        beam_layout.addWidget(self.energy_spin, 0, 1)

        beam_layout.addWidget(QLabel("Electrons:"), 1, 0)
        self.electrons_spin = QSpinBox()
        self.electrons_spin.setRange(1, 50)
        self.electrons_spin.setValue(15)
        beam_layout.addWidget(self.electrons_spin, 1, 1)

        layout.addWidget(beam_group)

        # Animation settings
        anim_group = QGroupBox("Animation Settings")
        anim_layout = QGridLayout(anim_group)

        anim_layout.addWidget(QLabel("Duration:"), 0, 0)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1, 20)
        self.duration_spin.setValue(5.0)
        self.duration_spin.setSuffix(" sec")
        anim_layout.addWidget(self.duration_spin, 0, 1)

        anim_layout.addWidget(QLabel("FPS:"), 1, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(30)
        anim_layout.addWidget(self.fps_spin, 1, 1)

        layout.addWidget(anim_group)

        # Generate button
        self.generate_btn = QPushButton("Generate Animation")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.generate_btn.clicked.connect(self.generate_animation)
        layout.addWidget(self.generate_btn)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
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
                background-color: #2a6a4a;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a8a6a;
            }
            QPushButton:pressed {
                background-color: #1a5a3a;
            }
            QPushButton:disabled {
                background-color: #404060;
                color: #808080;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #353555;
                border: 1px solid #4a4a6a;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QLabel {
                color: #cccccc;
            }
        """)

    def generate_animation(self):
        # Get output filename
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Animation",
            f"electron_{self.material_combo.currentText()}_{self.energy_spin.value()}keV.gif",
            "GIF Files (*.gif)"
        )

        if not output_file:
            return

        self.generate_btn.setEnabled(False)
        self.status_label.setText("Generating...")

        # Create animator
        animator = ElectronAnimator(
            resist_thickness=self.thickness_spin.value(),
            resist_material=self.material_combo.currentText(),
            beam_energy=self.energy_spin.value()
        )

        # Generate trajectories
        animator.generate_trajectories(self.electrons_spin.value())

        # Create animation in thread
        self.worker = AnimationWorker(
            animator, output_file, self.fps_spin.value(), self.duration_spin.value()
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, msg):
        self.status_label.setText(msg)

    def on_finished(self, output_file):
        self.generate_btn.setEnabled(True)
        self.status_label.setText(f"Saved: {Path(output_file).name}")
        QMessageBox.information(self, "Success", f"Animation saved to:\n{output_file}")

    def on_error(self, error_msg):
        self.generate_btn.setEnabled(True)
        self.status_label.setText("Error!")
        QMessageBox.critical(self, "Error", f"Failed to create animation:\n{error_msg}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = AnimationGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
