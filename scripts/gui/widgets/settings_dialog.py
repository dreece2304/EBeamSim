"""
Settings Dialog for EBL Simulation GUI
Handles application configuration including Geant4 path
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from pathlib import Path
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.geant4_detector import Geant4PathDetector


class SettingsDialog(QDialog):
    """Dialog for configuring application settings"""

    settings_changed = Signal(dict)  # Emits updated settings

    def __init__(self, parent=None, current_g4_path: Optional[Path] = None):
        super().__init__(parent)
        self.detector = Geant4PathDetector()
        self.current_g4_path = current_g4_path

        self.setWindowTitle("EBL Simulation Settings")
        self.setMinimumWidth(600)
        self.setup_ui()

    def setup_ui(self):
        """Create the settings UI"""
        layout = QVBoxLayout(self)

        # Geant4 Path Settings
        g4_group = QGroupBox("Geant4 Installation")
        g4_layout = QVBoxLayout()

        # Current path display
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Installation Path:"))
        self.g4_path_edit = QLineEdit()
        if self.current_g4_path:
            self.g4_path_edit.setText(str(self.current_g4_path))
        else:
            detected = self.detector.detect_geant4_path()
            if detected:
                self.g4_path_edit.setText(str(detected))
        path_layout.addWidget(self.g4_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_geant4_path)
        path_layout.addWidget(browse_btn)

        g4_layout.addLayout(path_layout)

        # Auto-detect button
        detect_btn = QPushButton("Auto-Detect Geant4")
        detect_btn.clicked.connect(self.auto_detect_geant4)
        g4_layout.addWidget(detect_btn)

        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")
        g4_layout.addWidget(self.status_label)

        # Show search locations
        locations_btn = QPushButton("Show Search Locations")
        locations_btn.clicked.connect(self.show_search_locations)
        g4_layout.addWidget(locations_btn)

        g4_group.setLayout(g4_layout)
        layout.addWidget(g4_group)

        # Validate current path if set
        if self.g4_path_edit.text():
            self.validate_path(Path(self.g4_path_edit.text()))

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        layout.addStretch()

    def browse_geant4_path(self):
        """Open file browser to select Geant4 directory"""
        current_path = self.g4_path_edit.text() or str(Path.home())

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Geant4 Installation Directory",
            current_path,
            QFileDialog.ShowDirsOnly
        )

        if directory:
            path = Path(directory)
            self.g4_path_edit.setText(str(path))
            self.validate_path(path)

    def auto_detect_geant4(self):
        """Attempt to automatically detect Geant4 installation"""
        self.status_label.setText("Searching for Geant4 installation...")
        self.status_label.setStyleSheet("color: #007acc;")

        detected_path = self.detector.detect_geant4_path()

        if detected_path:
            self.g4_path_edit.setText(str(detected_path))
            self.status_label.setText(f"✓ Auto-detected: {detected_path}")
            self.status_label.setStyleSheet("color: #00aa00;")
        else:
            self.status_label.setText(
                "✗ Could not auto-detect Geant4. Please browse manually."
            )
            self.status_label.setStyleSheet("color: #cc0000;")

    def validate_path(self, path: Path):
        """Validate selected Geant4 path"""
        if self.detector.validate_geant4_path(path):
            data_dirs = self.detector.get_data_directories(path)
            self.status_label.setText(
                f"✓ Valid Geant4 installation ({len(data_dirs)} data libraries found)"
            )
            self.status_label.setStyleSheet("color: #00aa00;")
            return True
        else:
            self.status_label.setText(
                "✗ Not a valid Geant4 installation (missing required directories)"
            )
            self.status_label.setStyleSheet("color: #cc0000;")
            return False

    def show_search_locations(self):
        """Show all locations that are searched for Geant4"""
        locations = self.detector.get_search_locations()
        locations_text = "Geant4 Search Locations:\n\n" + "\n".join(
            f"• {loc}" for loc in locations
        )

        QMessageBox.information(
            self,
            "Geant4 Search Locations",
            locations_text
        )

    def accept_settings(self):
        """Validate and accept settings"""
        g4_path_text = self.g4_path_edit.text().strip()

        if not g4_path_text:
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Geant4 path cannot be empty. Please specify a valid path."
            )
            return

        g4_path = Path(g4_path_text)

        if not self.validate_path(g4_path):
            reply = QMessageBox.question(
                self,
                "Invalid Geant4 Path",
                "The selected path does not appear to be a valid Geant4 installation.\n\n"
                "Continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Emit settings
        settings = {
            'geant4_path': g4_path
        }
        self.settings_changed.emit(settings)
        self.accept()

    def get_geant4_path(self) -> Optional[Path]:
        """Get the configured Geant4 path"""
        text = self.g4_path_edit.text().strip()
        return Path(text) if text else None
