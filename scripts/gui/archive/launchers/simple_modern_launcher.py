#!/usr/bin/env python3
"""
Simple Modern EBL Launcher - Reliable Version
=============================================

Clean, working implementation of the separated PSF/Pattern interface concept.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFrame, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap


class SimpleCard(QFrame):
    """Simple card widget without complex animations"""
    
    clicked = Signal()
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d3748;
                border: 2px solid #4a5568;
                border-radius: 12px;
                padding: 20px;
                margin: 8px;
            }
            QFrame:hover {
                border-color: #6366f1;
                background-color: #374151;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)
        
        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet("""
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 8px;
            """)
            self.layout.addWidget(self.title_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ModeCard(SimpleCard):
    """Card for mode selection"""
    
    mode_selected = Signal(str)
    
    def __init__(self, mode_name, title, description, features, parent=None):
        super().__init__(title, parent)
        self.mode_name = mode_name
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 14px;
            color: #a0aec0;
            line-height: 1.4;
        """)
        desc_label.setWordWrap(True)
        self.layout.addWidget(desc_label)
        
        # Features
        features_label = QLabel("Key Features:")
        features_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #ffffff;
            margin-top: 16px;
        """)
        self.layout.addWidget(features_label)
        
        for feature in features:
            feature_label = QLabel(f"• {feature}")
            feature_label.setStyleSheet("""
                font-size: 13px;
                color: #e2e8f0;
                margin-left: 16px;
                margin-bottom: 4px;
            """)
            self.layout.addWidget(feature_label)
        
        # Button
        self.select_btn = QPushButton(f"Select {title}")
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #5a67d8;
            }
            QPushButton:pressed {
                background-color: #4c51bf;
            }
        """)
        self.select_btn.clicked.connect(lambda: self.mode_selected.emit(self.mode_name))
        self.layout.addWidget(self.select_btn)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mode_selected.emit(self.mode_name)
        super().mousePressEvent(event)


class SimpleLauncher(QMainWindow):
    """Simple, working EBL launcher"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EBL Simulation Suite")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a202c, stop:1 #2d3748);
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Mode selection
        self.stacked_widget = QStackedWidget()
        
        # Create mode selection page
        mode_page = self.create_mode_selection()
        self.stacked_widget.addWidget(mode_page)
        
        # Placeholder pages for PSF and Pattern modes
        psf_page = self.create_placeholder_page("PSF Analysis Mode", 
            "Point Spread Function analysis interface would be loaded here.\n\n"
            "Features:\n• Resist characterization\n• Energy deposition analysis\n• BEAMER integration")
        
        pattern_page = self.create_placeholder_page("Pattern Simulation Mode",
            "Advanced pattern design interface would be loaded here.\n\n"
            "Features:\n• Pattern design tools\n• 3D visualization\n• Proximity effect analysis")
        
        self.stacked_widget.addWidget(psf_page)
        self.stacked_widget.addWidget(pattern_page)
        
        layout.addWidget(self.stacked_widget, 1)
        
        # Back button (initially hidden)
        self.back_btn = QPushButton("← Back to Mode Selection")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5568;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #718096;
            }
        """)
        self.back_btn.clicked.connect(self.show_mode_selection)
        self.back_btn.setVisible(False)
        layout.addWidget(self.back_btn)
        
        # Status bar
        self.statusBar().showMessage("Ready • Select simulation mode to begin")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background: #2d3748;
                color: #e2e8f0;
                border: none;
                padding: 6px;
            }
        """)
    
    def create_header(self):
        """Create application header"""
        header = QWidget()
        header.setFixedHeight(120)
        
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 20, 0, 20)
        
        title = QLabel("EBL Simulation Suite")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            text-align: center;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Professional Electron Beam Lithography Analysis")
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #a0aec0;
            text-align: center;
            margin-top: 8px;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        return header
    
    def create_mode_selection(self):
        """Create mode selection page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # Welcome text
        welcome = QLabel("Choose Your Simulation Workflow")
        welcome.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            text-align: center;
        """)
        welcome.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome)
        
        # Cards container
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setSpacing(40)
        
        # PSF Card
        psf_features = [
            "Point spread function analysis",
            "Resist optimization studies", 
            "Alpha/beta parameter extraction",
            "BEAMER export integration",
            "Energy deposition mapping"
        ]
        
        psf_card = ModeCard("psf", "PSF Analysis",
            "Specialized workflow for point spread function characterization and resist optimization.",
            psf_features)
        psf_card.mode_selected.connect(self.switch_to_mode)
        
        # Pattern Card
        pattern_features = [
            "Complex pattern design",
            "Multi-pattern simulation",
            "3D dose visualization",
            "Proximity effect correction",
            "Advanced pattern analysis"
        ]
        
        pattern_card = ModeCard("pattern", "Pattern Simulation",
            "Advanced pattern design workflow with visualization and proximity effect analysis.",
            pattern_features)
        pattern_card.mode_selected.connect(self.switch_to_mode)
        
        cards_layout.addWidget(psf_card)
        cards_layout.addWidget(pattern_card)
        
        layout.addWidget(cards_widget, 1)
        
        return page
    
    def create_placeholder_page(self, title, description):
        """Create placeholder page for modes"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            text-align: center;
            margin-bottom: 20px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 16px;
            color: #a0aec0;
            text-align: center;
            line-height: 1.6;
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        
        return page
    
    def switch_to_mode(self, mode):
        """Switch to selected mode"""
        if mode == "psf":
            self.stacked_widget.setCurrentIndex(1)
            self.statusBar().showMessage("PSF Analysis Mode Active")
            self.setWindowTitle("EBL Simulation Suite - PSF Analysis")
        elif mode == "pattern":
            self.stacked_widget.setCurrentIndex(2)
            self.statusBar().showMessage("Pattern Simulation Mode Active")
            self.setWindowTitle("EBL Simulation Suite - Pattern Simulation")
        
        self.back_btn.setVisible(True)
    
    def show_mode_selection(self):
        """Return to mode selection"""
        self.stacked_widget.setCurrentIndex(0)
        self.back_btn.setVisible(False)
        self.statusBar().showMessage("Ready • Select simulation mode to begin")
        self.setWindowTitle("EBL Simulation Suite")


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EBL Simulation Suite")
    app.setApplicationVersion("4.0")
    
    # Set font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show launcher
    launcher = SimpleLauncher()
    launcher.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()