#!/usr/bin/env python3
"""
Scientific GUI Mockup #2: Ribbon/Toolbar Design  
================================================

Based on research findings, this mockup demonstrates:
- Ribbon interface similar to MATLAB/LabVIEW
- Grouped tool organization
- Context-sensitive toolbar sections
- Professional scientific software styling

Research Source: MATLAB and LabVIEW use ribbon interfaces extensively
for complex scientific workflows with grouped functionality.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QGroupBox, QTabWidget,
    QToolBar, QAction, QButtonGroup, QSplitter, QTextEdit
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

class MockRibbonSection(QFrame):
    """Mock ribbon section with grouped controls"""
    
    def __init__(self, title: str, buttons: list):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setMaximumWidth(250)
        
        self.setStyleSheet("""
            MockRibbonSection {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                margin: 2px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 4)
        
        # Section title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 10px;
            font-weight: 600;
            color: #475569;
            text-align: center;
            border-top: 1px solid #e2e8f0;
            padding-top: 4px;
            margin-top: 4px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # Button grid
        button_grid = QGridLayout()
        button_grid.setSpacing(2)
        
        for i, (btn_text, btn_icon, btn_size) in enumerate(buttons):
            btn = QPushButton(btn_text)
            
            if btn_size == "large":
                btn.setMinimumSize(80, 60)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 1px solid #cbd5e1;
                        border-radius: 4px;
                        padding: 8px 4px;
                        text-align: center;
                        font-size: 10px;
                        font-weight: 500;
                        color: #374151;
                    }
                    QPushButton:hover {
                        background: #f1f5f9;
                        border-color: #3b82f6;
                    }
                    QPushButton:pressed {
                        background: #e2e8f0;
                    }
                """)
                button_grid.addWidget(btn, 0, i, 2, 1)  # Span 2 rows
                
            else:  # small button
                btn.setMinimumSize(75, 28)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 1px solid #cbd5e1;  
                        border-radius: 3px;
                        padding: 4px 6px;
                        font-size: 9px;
                        color: #374151;
                    }
                    QPushButton:hover {
                        background: #f1f5f9;
                        border-color: #3b82f6;
                    }
                """)
                row = i // 2
                col = i % 2
                button_grid.addWidget(btn, row, col + 2)  # Offset for large buttons
        
        layout.addLayout(button_grid)
        layout.addWidget(title_label)


class MockPropertyPanel(QFrame):
    """Mock property panel similar to MATLAB/LabVIEW"""
    
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setMinimumWidth(280)
        self.setMaximumWidth(320)
        
        self.setStyleSheet("""
            MockPropertyPanel {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Panel title
        title_label = QLabel("Properties Panel")
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 700;
            color: #1f2937;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 8px;
        """)
        
        # Property groups
        self.create_property_group(layout, "Beam Properties", [
            ("Energy (keV)", "30.0"),
            ("Beam Size (nm)", "1.0"), 
            ("Current (pA)", "10.0"),
            ("Dwell Time (μs)", "1.0")
        ])
        
        self.create_property_group(layout, "Resist Properties", [
            ("Material", "Alucone_XPS"),
            ("Thickness (nm)", "30.0"),
            ("Density (g/cm³)", "1.35"),
            ("Temperature (°C)", "23.0")
        ])
        
        self.create_property_group(layout, "Analysis Settings", [
            ("Grid Size", "512 x 512"),
            ("Pixel Size (nm)", "0.5"),
            ("Energy Bins", "100"),
            ("Statistics", "Monte Carlo")
        ])
        
        layout.addWidget(title_label)
        layout.addStretch()
    
    def create_property_group(self, parent_layout, title: str, properties: list):
        """Create a property group section"""
        group_frame = QFrame()
        group_frame.setStyleSheet("""
            QFrame {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        group_layout = QVBoxLayout(group_frame)
        group_layout.setSpacing(6)
        
        # Group title
        group_title = QLabel(title)
        group_title.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 4px;
        """)
        
        group_layout.addWidget(group_title)
        
        # Properties
        for prop_name, prop_value in properties:
            prop_layout = QHBoxLayout()
            
            name_label = QLabel(prop_name + ":")
            name_label.setStyleSheet("""
                font-size: 10px;
                color: #6b7280;
                font-weight: 500;
            """)
            name_label.setFixedWidth(120)
            
            value_label = QLabel(prop_value)
            value_label.setStyleSheet("""
                font-size: 10px;
                color: #1f2937;
                font-weight: 600;
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 3px;
                padding: 2px 6px;
            """)
            
            prop_layout.addWidget(name_label)
            prop_layout.addWidget(value_label)
            prop_layout.addStretch()
            
            group_layout.addLayout(prop_layout)
        
        parent_layout.addWidget(group_frame)


class MockWorkspace(QFrame):
    """Mock workspace area with multiple views"""
    
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        
        self.setStyleSheet("""
            MockWorkspace {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget for multiple views
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #64748b;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1e40af;
                border-bottom: 2px solid #3b82f6;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
                color: #475569;
            }
        """)
        
        # Main plot view
        main_view = self.create_plot_view("PSF Analysis - Main View", 
            "🎯 2D Intensity Map\n\nInteractive visualization showing:\n• Electron intensity distribution\n• Forward and backscattered components\n• Real-time parameter updates\n• Export capabilities")
        
        # Results view  
        results_view = self.create_plot_view("Analysis Results",
            "📊 Statistical Analysis\n\n• FWHM measurements\n• α/β parameter extraction\n• Energy efficiency calculations\n• Comparison with reference data")
        
        # 3D view
        view_3d = self.create_plot_view("3D Visualization", 
            "🌐 3D PSF Rendering\n\n• Volume visualization\n• Isosurface rendering\n• Cross-section analysis\n• Animation controls")
        
        # Report view
        report_view = self.create_report_view()
        
        tab_widget.addTab(main_view, "Main View")
        tab_widget.addTab(results_view, "Results")
        tab_widget.addTab(view_3d, "3D View")
        tab_widget.addTab(report_view, "Report")
        
        layout.addWidget(tab_widget)
    
    def create_plot_view(self, title: str, content: str) -> QWidget:
        """Create a mock plot view"""
        view = QWidget()
        layout = QVBoxLayout(view)
        
        # View title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #1f2937;
            padding: 12px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        """)
        
        # Plot area
        plot_area = QLabel(content)
        plot_area.setAlignment(Qt.AlignCenter)
        plot_area.setStyleSheet("""
            QLabel {
                background: #fafafa;
                border: 2px dashed #cbd5e1;
                border-radius: 8px;
                color: #64748b;
                font-size: 14px;
                line-height: 1.6;
                padding: 40px;
                margin: 12px;
            }
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(plot_area, 1)
        
        return view
    
    def create_report_view(self) -> QWidget:
        """Create a mock report view"""
        view = QWidget()
        layout = QVBoxLayout(view)
        
        # Report editor
        report_editor = QTextEdit()
        report_editor.setHtml("""
        <h2 style="color: #1f2937;">PSF Analysis Report</h2>
        <p><strong>Experiment:</strong> Alucone_XPS Resist Characterization</p>
        <p><strong>Date:</strong> 2024-12-xx</p>
        <hr>
        <h3>Parameters Used:</h3>
        <ul>
            <li>Beam Energy: 30.0 keV</li>
            <li>Beam Size: 1.0 nm FWHM</li>
            <li>Beam Current: 10.0 pA</li>
            <li>Resist: Alucone_XPS, 30 nm thick</li>
        </ul>
        <h3>Key Results:</h3>
        <ul>
            <li>FWHM: 2.1 nm</li>
            <li>Forward scattering (α): 0.85</li>
            <li>Backscattering (β): 0.15</li>
            <li>Energy efficiency: 94.0%</li>
        </ul>
        <h3>Analysis Notes:</h3>
        <p>The PSF shows excellent characteristics for high-resolution lithography...</p>
        """)
        
        report_editor.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 16px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 11px;
                line-height: 1.5;
            }
        """)
        
        layout.addWidget(report_editor)
        return view


class ScientificRibbonMockup(QMainWindow):
    """
    Mockup #2: Ribbon/Toolbar Design
    
    Features demonstrated:
    - Ribbon interface with grouped tools
    - Context-sensitive sections
    - Properties panel (similar to MATLAB)
    - Multi-tab workspace
    - Professional scientific styling
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scientific GUI Mockup #2: Ribbon/Toolbar Design")
        self.setMinimumSize(1400, 900)
        
        # Light theme for this mockup
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the ribbon interface"""
        # Create ribbon toolbar
        self.create_ribbon_toolbar()
        
        # Create main widget that contains both ribbon and content
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add ribbon
        main_layout.addWidget(self.ribbon_widget)
        
        # Create content area
        content_widget = QWidget()
        main_layout.addWidget(content_widget, 1)
        
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Main splitter for workspace and properties
        splitter = QSplitter(Qt.Horizontal)
        
        # Main workspace
        workspace = MockWorkspace()
        splitter.addWidget(workspace)
        
        # Properties panel
        properties = MockPropertyPanel()
        splitter.addWidget(properties)
        
        # Set splitter proportions (workspace gets more space)
        splitter.setSizes([1000, 300])
        
        layout.addWidget(splitter, 1)
        
        # Status bar
        self.create_status_bar()
    
    def create_ribbon_toolbar(self):
        """Create ribbon-style toolbar"""
        # Main ribbon container
        ribbon_widget = QWidget()
        ribbon_widget.setFixedHeight(100)
        ribbon_widget.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-bottom: 2px solid #e2e8f0;
            }
        """)
        
        ribbon_layout = QHBoxLayout(ribbon_widget)
        ribbon_layout.setSpacing(12)
        ribbon_layout.setContentsMargins(12, 8, 12, 8)
        
        # File operations section
        file_buttons = [
            ("New\nProject", "📄", "large"),
            ("Open", "📂", "small"),
            ("Save", "💾", "small"),
            ("Export", "📤", "small"),
            ("Import", "📥", "small")
        ]
        file_section = MockRibbonSection("File", file_buttons)
        
        # Analysis tools section
        analysis_buttons = [
            ("Run\nAnalysis", "▶️", "large"),
            ("PSF Map", "🎯", "small"),
            ("Statistics", "📊", "small"),
            ("Compare", "📈", "small"),
            ("Optimize", "⚙️", "small")
        ]
        analysis_section = MockRibbonSection("Analysis", analysis_buttons)
        
        # Visualization section
        viz_buttons = [
            ("Plot\nSetup", "📊", "large"),
            ("2D View", "🗺️", "small"),
            ("3D View", "🌐", "small"),
            ("Animation", "🎬", "small"),
            ("Export Plot", "🖼️", "small")
        ]
        viz_section = MockRibbonSection("Visualization", viz_buttons)
        
        # Tools section
        tools_buttons = [
            ("Beam\nSetup", "⚡", "large"),
            ("Materials", "🧪", "small"),
            ("Simulate", "🔄", "small"),
            ("Calibrate", "📐", "small"),
            ("Settings", "⚙️", "small")
        ]
        tools_section = MockRibbonSection("Tools", tools_buttons)
        
        # Add sections to ribbon
        ribbon_layout.addWidget(file_section)
        ribbon_layout.addWidget(analysis_section)
        ribbon_layout.addWidget(viz_section)
        ribbon_layout.addWidget(tools_section)
        ribbon_layout.addStretch()
        
        # Store ribbon widget for later use
        self.ribbon_widget = ribbon_widget
    
    def create_status_bar(self):
        """Create status bar"""
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background: #f1f5f9;
                border-top: 1px solid #d1d5db;
                padding: 4px 12px;
                font-size: 11px;
                color: #475569;
            }
        """)
        
        # Add status information
        status_bar.showMessage("Ready • Simulation: Idle • Memory: 2.1GB used • CPU: 15%")


def main():
    """Run ribbon mockup"""
    app = QApplication(sys.argv)
    
    # High DPI support
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    
    # Set font for high DPI
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = ScientificRibbonMockup()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()