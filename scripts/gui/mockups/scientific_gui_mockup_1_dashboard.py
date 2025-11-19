#!/usr/bin/env python3
"""
Scientific GUI Mockup #1: Dashboard-Focused Design
==================================================

Based on research findings, this mockup demonstrates:
- Clean dashboard with key metrics prominent
- Card-based layout for information hierarchy  
- Progressive disclosure design
- High DPI optimization

Research Source: Berkeley Lab's STRUDEL project emphasizes user-centric design
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QGroupBox, QProgressBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor

# Add path for components (would use actual path in real implementation)
sys.path.append(str(Path(__file__).parent.parent / "widgets" / "modern"))

class MockMetricCard(QFrame):
    """Mock metric display card"""
    
    def __init__(self, title: str, value: str, unit: str = "", status: str = "normal"):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setMinimumSize(200, 120)
        
        # Color coding based on status
        colors = {
            "normal": "#1f2937",
            "warning": "#451a03", 
            "critical": "#450a0a",
            "success": "#064e3b"
        }
        
        self.setStyleSheet(f"""
            MockMetricCard {{
                background: {colors.get(status, colors["normal"])};
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 16px;
            }}
            MockMetricCard:hover {{
                border-color: #6366f1;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            margin-bottom: 8px;
        """)
        
        # Value + Unit
        value_layout = QHBoxLayout()
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 800;
            color: #f9fafb;
            line-height: 1;
        """)
        
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #6b7280;
            margin-left: 4px;
            margin-top: 14px;
        """)
        
        value_layout.addWidget(value_label)
        if unit:
            value_layout.addWidget(unit_label)
        value_layout.addStretch()
        
        # Status indicator
        if status != "normal":
            status_label = QLabel(f"● {status.title()}")
            status_colors = {
                "warning": "#f59e0b",
                "critical": "#ef4444", 
                "success": "#10b981"
            }
            status_label.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 600;
                color: {status_colors.get(status, "#6b7280")};
                margin-top: 8px;
            """)
            layout.addWidget(status_label)
        
        layout.addWidget(title_label)
        layout.addLayout(value_layout)
        layout.addStretch()


class MockControlPanel(QFrame):
    """Mock control panel with scientific instrument controls"""
    
    def __init__(self, title: str):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setMinimumHeight(200)
        
        self.setStyleSheet("""
            MockControlPanel {
                background: #1f2937;
                border: 1px solid #374151; 
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Panel title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #f9fafb;
            margin-bottom: 12px;
        """)
        
        # Mock controls
        controls_layout = QVBoxLayout()
        
        # Parameter display
        param_label = QLabel("Current Settings:")
        param_label.setStyleSheet("font-size: 12px; color: #9ca3af; margin-bottom: 8px;")
        
        settings_label = QLabel("• Energy: 30.0 keV\n• Beam Size: 1.0 nm\n• Current: 10.0 pA")
        settings_label.setStyleSheet("font-size: 13px; color: #d1d5db; margin-bottom: 12px;")
        
        # Action buttons
        config_btn = QPushButton("Configure Parameters")
        config_btn.setStyleSheet("""
            QPushButton {
                background: #374151;
                border: 1px solid #6b7280;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                color: #f9fafb;
            }
            QPushButton:hover {
                background: #4b5563;
                border-color: #9ca3af;
            }
        """)
        
        run_btn = QPushButton("Run Analysis")
        run_btn.setStyleSheet("""
            QPushButton {
                background: #10b981;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 700;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        
        controls_layout.addWidget(param_label)
        controls_layout.addWidget(settings_label)
        controls_layout.addWidget(config_btn)
        controls_layout.addWidget(run_btn)
        controls_layout.addStretch()
        
        layout.addWidget(title_label)
        layout.addLayout(controls_layout)


class MockVisualizationArea(QFrame):
    """Mock visualization area for scientific plots"""
    
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setMinimumHeight(400)
        
        self.setStyleSheet("""
            MockVisualizationArea {
                background: #1f2937;
                border: 1px solid #374151;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title bar
        title_bar = QHBoxLayout()
        title_label = QLabel("PSF Analysis Results")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #f9fafb;
        """)
        
        # View controls
        controls_layout = QHBoxLayout()
        for view in ["2D Map", "Radial", "Log Scale", "3D"]:
            btn = QPushButton(view)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid #4b5563;
                    border-radius: 4px;
                    padding: 4px 12px;
                    color: #9ca3af;
                    font-size: 11px;
                }
                QPushButton:hover {
                    border-color: #6366f1;
                    color: #d1d5db;
                }
            """)
            controls_layout.addWidget(btn)
        
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        title_bar.addLayout(controls_layout)
        
        # Mock plot area
        plot_area = QLabel("📊 Interactive PSF Visualization\n\nReal-time plotting area would show:\n• 2D intensity maps\n• Radial profiles\n• Statistical analysis\n• Comparison overlays")
        plot_area.setAlignment(Qt.AlignCenter)
        plot_area.setStyleSheet("""
            QLabel {
                background: #374151;
                border: 2px dashed #4b5563;
                border-radius: 8px;
                color: #9ca3af;
                font-size: 14px;
                line-height: 1.6;
                padding: 40px;
            }
        """)
        
        layout.addLayout(title_bar)
        layout.addWidget(plot_area, 1)


class ScientificDashboardMockup(QMainWindow):
    """
    Mockup #1: Dashboard-Focused Scientific Interface
    
    Features demonstrated:
    - Clean metrics dashboard at top
    - Control panels on left 
    - Large visualization area
    - Status monitoring
    - Progressive disclosure
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scientific GUI Mockup #1: Dashboard-Focused Design")
        self.setMinimumSize(1400, 900)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111827;
            }
        """)
        
        self.setup_ui()
        self.setup_mock_data()
    
    def setup_ui(self):
        """Setup the dashboard interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        self.create_header(layout)
        
        # Key metrics dashboard
        self.create_metrics_dashboard(layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Left sidebar - controls
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel)
        
        # Right area - visualization
        viz_area = MockVisualizationArea()
        content_layout.addWidget(viz_area, 2)  # Takes more space
        
        layout.addLayout(content_layout, 1)
        
        # Status bar
        self.create_status_bar(layout)
    
    def create_header(self, layout):
        """Create application header"""
        header = QFrame()
        header.setMinimumHeight(80)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e293b, stop:1 #334155);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        header_layout = QHBoxLayout(header)
        
        # Title section
        title_label = QLabel("EBL Simulation Suite - Dashboard Design")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 800;
            color: #ffffff;
        """)
        
        subtitle_label = QLabel("Real-time monitoring and control interface")
        subtitle_label.setStyleSheet("""
            font-size: 12px;
            color: #cbd5e1;
            margin-top: 4px;
        """)
        
        title_section = QVBoxLayout()
        title_section.addWidget(title_label)
        title_section.addWidget(subtitle_label)
        
        # System status
        status_section = QVBoxLayout()
        system_label = QLabel("System Status: ● Online")
        system_label.setStyleSheet("font-size: 12px; color: #10b981; font-weight: 600;")
        
        time_label = QLabel("Last Update: Just now")
        time_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        
        status_section.addWidget(system_label)
        status_section.addWidget(time_label)
        
        header_layout.addLayout(title_section)
        header_layout.addStretch()
        header_layout.addLayout(status_section)
        
        layout.addWidget(header)
    
    def create_metrics_dashboard(self, layout):
        """Create key metrics dashboard"""
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("QFrame { background: transparent; }")
        
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setSpacing(16)
        
        # Key scientific metrics
        metrics = [
            {"title": "FWHM", "value": "2.1", "unit": "nm", "status": "normal"},
            {"title": "α (Forward)", "value": "0.85", "unit": "", "status": "success"},
            {"title": "β (Back)", "value": "0.15", "unit": "", "status": "warning"},
            {"title": "Energy Efficiency", "value": "94.0", "unit": "%", "status": "success"},
            {"title": "Peak Intensity", "value": "45.2", "unit": "eV/nm²", "status": "normal"},
            {"title": "PSF Range", "value": "15.8", "unit": "nm", "status": "normal"}
        ]
        
        for i, metric in enumerate(metrics):
            card = MockMetricCard(
                metric["title"], 
                metric["value"],
                metric["unit"],
                metric["status"]
            )
            row, col = divmod(i, 3)
            metrics_layout.addWidget(card, row, col)
        
        layout.addWidget(metrics_frame)
    
    def create_left_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        panel.setFixedWidth(350)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        
        # Control panels
        beam_panel = MockControlPanel("Beam Control")
        resist_panel = MockControlPanel("Resist Parameters")
        sim_panel = MockControlPanel("Simulation")
        
        layout.addWidget(beam_panel)
        layout.addWidget(resist_panel) 
        layout.addWidget(sim_panel)
        layout.addStretch()
        
        return panel
    
    def create_status_bar(self, layout):
        """Create status bar"""
        status_frame = QFrame()
        status_frame.setMaximumHeight(50)
        status_frame.setStyleSheet("""
            QFrame {
                background: #1f2937;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        
        # Progress info
        progress_label = QLabel("Simulation Progress:")
        progress_label.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: 600;")
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(73)
        progress_bar.setMaximumWidth(200)
        progress_bar.setStyleSheet("""
            QProgressBar {
                background: #374151;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: #6366f1;
                border-radius: 4px;
            }
        """)
        
        # System info
        info_label = QLabel("CPU: 23% • Memory: 2.1GB • GPU: Available")
        info_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        
        status_layout.addWidget(progress_label)
        status_layout.addWidget(progress_bar)
        status_layout.addStretch()
        status_layout.addWidget(info_label)
        
        layout.addWidget(status_frame)
    
    def setup_mock_data(self):
        """Setup mock data updates"""
        # This would update metrics in real implementation
        pass


def main():
    """Run dashboard mockup"""
    app = QApplication(sys.argv)
    
    # High DPI support
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    
    # Set font for high DPI
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = ScientificDashboardMockup()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()