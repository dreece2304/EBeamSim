#!/usr/bin/env python3
"""
Test PSF Dashboard Interface
============================

Quick test launcher to see the new PSF dashboard interface in action.
Optimized for high DPI displays.
"""

import sys
import os
from pathlib import Path

# Add paths for imports
gui_dir = Path(__file__).parent
sys.path.append(str(gui_dir))
sys.path.append(str(gui_dir / "interfaces"))
sys.path.append(str(gui_dir / "widgets" / "modern"))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import our new dashboard interface
from psf_dashboard_interface import PSFDashboardInterface


class TestWindow(QMainWindow):
    """Test window for PSF dashboard"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSF Dashboard Test - High DPI Optimized")
        
        # Optimize for high DPI displays  
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # Set up the dashboard interface
        self.psf_dashboard = PSFDashboardInterface()
        self.setCentralWidget(self.psf_dashboard)
        
        # Connect signals
        self.psf_dashboard.simulation_started.connect(self.on_simulation_started)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111827;
            }
        """)
    
    def on_simulation_started(self, params):
        """Handle simulation start"""
        print("Simulation started with params:", params)
        
        # Simulate some progress updates
        from PySide6.QtCore import QTimer
        self.timer = QTimer()
        self.progress = 0
        
        def update_progress():
            self.progress += 5
            self.psf_dashboard.update_progress(self.progress)
            if self.progress >= 100:
                self.timer.stop()
        
        self.timer.timeout.connect(update_progress)
        self.timer.start(200)  # Update every 200ms


def main():
    """Main test function"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("PSF Dashboard Test")
    app.setApplicationVersion("1.0")
    
    # High DPI support
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    
    # Set font optimized for high DPI
    font = QFont("Segoe UI", 9)  # Smaller font for high DPI
    app.setFont(font)
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()