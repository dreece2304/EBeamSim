#!/usr/bin/env python3
"""
Modern EBL Simulation GUI with Enhanced UI/UX
============================================

Features:
- Material Design 3 inspired interface
- Modern typography and spacing
- Smooth animations and transitions
- Improved user experience flow
- Scientific computing optimized layout
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFrame, QScrollArea, QSplitter
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QLinearGradient

# Import the existing GUI as a base
from ebl_gui import EBLMainWindow


class ModernCard(QFrame):
    """Modern card component with shadow and hover effects"""
    
    def __init__(self, title="", content_widget=None, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            ModernCard {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 16px;
                padding: 24px;
            }
            ModernCard:hover {
                border-color: #6366f1;
                background-color: #1e293b;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                font-size: 18px;
                font-weight: 700;
                color: #6366f1;
                margin-bottom: 8px;
            """)
            layout.addWidget(title_label)
        
        if content_widget:
            layout.addWidget(content_widget)


class ModernHeaderWidget(QWidget):
    """Modern header with gradient background and typography"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setupUI()
    
    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        
        # Main title
        title = QLabel("EBL Simulation Suite")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6366f1, stop:1 #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        """)
        
        # Subtitle
        subtitle = QLabel("Professional Electron Beam Lithography Analysis")
        subtitle.setStyleSheet("""
            font-size: 16px;
            font-weight: 500;
            color: #9ca3af;
            margin-top: 8px;
        """)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Gradient background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#0f172a"))
        gradient.setColorAt(1, QColor("#1e293b"))
        
        painter.fillRect(self.rect(), gradient)


class ModernStatusPanel(QWidget):
    """Modern status panel with metrics and indicators"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
    
    def setupUI(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 16, 24, 16)
        
        # Status indicators
        self.create_status_indicator("Simulation", "Ready", "#10b981")
        self.create_status_indicator("Physics", "Optimized", "#6366f1")
        self.create_status_indicator("Output", "Available", "#f59e0b")
        
        layout.addStretch()
    
    def create_status_indicator(self, label, status, color):
        container = QWidget()
        container.setFixedWidth(120)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        
        # Status value
        status_widget = QLabel(status)
        status_widget.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {color};
        """)
        
        layout.addWidget(label_widget)
        layout.addWidget(status_widget)
        
        self.layout().addWidget(container)


class ModernActionButton(QPushButton):
    """Enhanced button with modern styling and animations"""
    
    def __init__(self, text, button_type="primary", parent=None):
        super().__init__(text, parent)
        
        self.setProperty("buttonType", button_type)
        self.setMinimumHeight(48)
        self.setMinimumWidth(140)
        
        # Setup animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.original_geometry = None
    
    def enterEvent(self, event):
        if not self.original_geometry:
            self.original_geometry = self.geometry()
        
        # Subtle lift animation
        new_rect = QRect(self.original_geometry)
        new_rect.translate(0, -2)
        
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(new_rect)
        self.animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if self.original_geometry:
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.original_geometry)
            self.animation.start()
        
        super().leaveEvent(event)


class ModernEBLGUI(QMainWindow):
    """Modern wrapper for the EBL GUI with enhanced UI/UX"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EBL Simulation Suite - Modern Interface")
        self.setMinimumSize(1600, 1000)
        
        # Load modern stylesheet
        self.load_modern_stylesheet()
        
        # Setup modern UI
        self.setup_modern_ui()
        
        # Initialize the original GUI as a component
        self.original_gui = EBLMainWindow()
    
    def load_modern_stylesheet(self):
        """Load the modern stylesheet"""
        style_path = Path(__file__).parent / "resources" / "modern_styles.qss"
        if style_path.exists():
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())
    
    def setup_modern_ui(self):
        """Setup the modern user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = ModernHeaderWidget()
        main_layout.addWidget(header)
        
        # Content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # Left panel - Quick actions and status
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Main content area
        main_content = self.create_main_content()
        splitter.addWidget(main_content)
        
        # Set splitter proportions
        splitter.setSizes([300, 1300])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        # Status panel
        status_panel = ModernStatusPanel()
        main_layout.addWidget(status_panel)
    
    def create_left_panel(self):
        """Create the left sidebar panel"""
        panel = QWidget()
        panel.setFixedWidth(320)
        panel.setStyleSheet("""
            QWidget {
                background-color: #111827;
                border-right: 1px solid #374151;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Quick Actions Card
        quick_actions = ModernCard("Quick Actions")
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(12)
        
        # Action buttons
        new_sim_btn = ModernActionButton("New Simulation", "primary")
        new_sim_btn.clicked.connect(self.new_simulation)
        
        open_results_btn = ModernActionButton("Open Results", "secondary")
        open_results_btn.clicked.connect(self.open_results)
        
        export_btn = ModernActionButton("Export Data", "secondary")
        export_btn.clicked.connect(self.export_data)
        
        actions_layout.addWidget(new_sim_btn)
        actions_layout.addWidget(open_results_btn)
        actions_layout.addWidget(export_btn)
        
        quick_actions_widget = QWidget()
        quick_actions_widget.setLayout(actions_layout)
        quick_actions.layout().addWidget(quick_actions_widget)
        
        layout.addWidget(quick_actions)
        
        # Recent Files Card
        recent_files = ModernCard("Recent Files")
        layout.addWidget(recent_files)
        
        layout.addStretch()
        
        return panel
    
    def create_main_content(self):
        """Create the main content area"""
        # For now, embed the original GUI
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        
        # We'll integrate the original GUI's central widget here
        # This is a placeholder - we'll enhance this further
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Welcome message for now
        welcome_card = ModernCard("Simulation Workspace", QLabel("Original EBL GUI will be integrated here\nwith modern enhancements"))
        content_layout.addWidget(welcome_card)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        return scroll_area
    
    # Placeholder methods for actions
    def new_simulation(self):
        print("New Simulation clicked")
    
    def open_results(self):
        print("Open Results clicked")
    
    def export_data(self):
        print("Export Data clicked")


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EBL Simulation Suite")
    app.setApplicationVersion("4.0")
    app.setOrganizationName("EBL Research")
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set modern font
    font = QFont("Inter", 10)
    if not font.exactMatch():
        font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show window
    window = ModernEBLGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()