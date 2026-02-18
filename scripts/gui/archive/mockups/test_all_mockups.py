#!/usr/bin/env python3
"""
Test All Scientific GUI Mockups
===============================

Convenient launcher to test all four scientific GUI design mockups.
Allows you to quickly compare different approaches.
"""

import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QFont

class MockupLauncher(QMainWindow):
    """Launcher for all GUI mockups"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scientific GUI Mockup Launcher")
        self.setMinimumSize(800, 600)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup launcher interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("Scientific GUI Design Mockups")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #1f2937;
            text-align: center;
            margin-bottom: 16px;
        """)
        header.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Choose a design approach to test on your high DPI display")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #6b7280;
            text-align: center;
            margin-bottom: 32px;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        
        # Mockup buttons
        mockups = [
            {
                "name": "Dashboard-Focused Design",
                "file": "scientific_gui_mockup_1_dashboard.py",
                "description": "Clean dashboard with key metrics prominent. Ideal for monitoring workflows.",
                "color": "#3b82f6"
            },
            {
                "name": "Ribbon/Toolbar Design", 
                "file": "scientific_gui_mockup_2_ribbon.py",
                "description": "Professional interface similar to MATLAB/LabVIEW. Feature-rich with grouped tools.",
                "color": "#10b981"
            },
            {
                "name": "Multi-Panel Workspace",
                "file": "scientific_gui_mockup_3_multipanel.py", 
                "description": "Flexible dockable panels like PyMOL/ImageJ. Maximum customization.",
                "color": "#f59e0b"
            },
            {
                "name": "Wizard/Step-by-Step",
                "file": "scientific_gui_mockup_4_wizard.py",
                "description": "Guided workflow with help and explanations. Perfect for beginners.",
                "color": "#8b5cf6"
            }
        ]
        
        for mockup in mockups:
            button = self.create_mockup_button(
                mockup["name"],
                mockup["description"], 
                mockup["file"],
                mockup["color"]
            )
            layout.addWidget(button)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(200)
        instructions.setHtml("""
        <h3>Evaluation Instructions:</h3>
        <ol>
            <li><strong>Test each design</strong> by clicking the buttons above</li>
            <li><strong>Resize windows</strong> to see how they adapt to different screen sizes</li>
            <li><strong>Check high DPI scaling</strong> - text should be crisp and readable</li>
            <li><strong>Navigate the interfaces</strong> to understand the information flow</li>
            <li><strong>Consider your workflow</strong> - which approach matches how you work?</li>
        </ol>
        <p><strong>Note:</strong> These are interactive mockups demonstrating UI patterns. 
        Full functionality would be implemented in the chosen design approach.</p>
        """)
        instructions.setStyleSheet("""
            QTextEdit {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 16px;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        
        layout.addWidget(header)
        layout.addWidget(subtitle)
        layout.addWidget(instructions)
        layout.addStretch()
    
    def create_mockup_button(self, name: str, description: str, filename: str, color: str) -> QWidget:
        """Create button for launching a mockup"""
        container = QFrame()
        container.setFrameStyle(QFrame.Box)
        container.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                padding: 16px;
            }}
            QFrame:hover {{
                border-color: {color};
                background: #fafafa;
            }}
        """)
        
        layout = QHBoxLayout(container)
        
        # Info section
        info_layout = QVBoxLayout()
        
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {color};
            margin-bottom: 4px;
        """)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #6b7280;
            line-height: 1.4;
        """)
        desc_label.setWordWrap(True)
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        
        # Launch button
        launch_btn = QPushButton("Launch")
        launch_btn.setFixedSize(100, 40)
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {self.darken_color(color)};
            }}
        """)
        
        launch_btn.clicked.connect(lambda: self.launch_mockup(filename))
        
        layout.addLayout(info_layout, 1)
        layout.addWidget(launch_btn)
        
        return container
    
    def darken_color(self, color: str) -> str:
        """Darken a hex color for hover effects"""
        color_map = {
            "#3b82f6": "#2563eb",
            "#10b981": "#059669", 
            "#f59e0b": "#d97706",
            "#8b5cf6": "#7c3aed"
        }
        return color_map.get(color, color)
    
    def launch_mockup(self, filename: str):
        """Launch a mockup file"""
        try:
            mockup_path = Path(__file__).parent / filename
            if mockup_path.exists():
                # Launch in separate process so multiple mockups can run
                subprocess.Popen([sys.executable, str(mockup_path)])
            else:
                print(f"Mockup file not found: {filename}")
        except Exception as e:
            print(f"Error launching mockup: {e}")


def main():
    """Main launcher function"""
    app = QApplication(sys.argv)
    
    # High DPI support
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    
    # Set font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    launcher = MockupLauncher()
    launcher.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()