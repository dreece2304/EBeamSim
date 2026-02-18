#!/usr/bin/env python3
"""
Quick test for high DPI sizing improvements
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("High DPI Test")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Test various font sizes
        for size in [8, 10, 12, 14, 16, 18, 20]:
            label = QLabel(f"Font size {size}px - This is a test line")
            label.setStyleSheet(f"font-size: {size}px; margin: 4px; padding: 2px;")
            layout.addWidget(label)
        
        # Screen info
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            dpi = screen.logicalDotsPerInch()
            device_ratio = screen.devicePixelRatio()
            
            info_label = QLabel(
                f"Screen: {geometry.width()}x{geometry.height()}\n"
                f"DPI: {dpi}\n"
                f"Device Pixel Ratio: {device_ratio}"
            )
            info_label.setStyleSheet("font-size: 12px; background: #333; color: white; padding: 10px; margin: 10px;")
            layout.addWidget(info_label)

def main():
    app = QApplication(sys.argv)
    
    # Set smaller font for high DPI
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = TestWindow()
    window.show()
    
    print(f"Application font: {app.font().pointSize()}px")
    print("Test window opened. Close it when done.")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())