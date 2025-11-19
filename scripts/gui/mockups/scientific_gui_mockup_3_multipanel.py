#!/usr/bin/env python3
"""
Scientific GUI Mockup #3: Multi-Panel Workspace Design
======================================================

Based on research findings, this mockup demonstrates:
- Dockable panels similar to PyMOL/ImageJ
- Flexible workspace layout
- Multiple simultaneous views
- Panel-based organization

Research Source: PyMOL and ImageJ use multi-panel interfaces
for complex analysis workflows with dockable windows.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QGroupBox, QTabWidget,
    QDockWidget, QSplitter, QTreeWidget, QTreeWidgetItem, QListWidget,
    QTextEdit, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor

class MockDockablePanel(QDockWidget):
    """Mock dockable panel for scientific tools"""
    
    def __init__(self, title: str, content_widget: QWidget, parent=None):
        super().__init__(title, parent)
        
        self.setFeatures(
            QDockWidget.DockWidgetMovable | 
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )
        
        # Style the dock widget
        self.setStyleSheet("""
            QDockWidget {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-weight: 600;
                color: #374151;
            }
            QDockWidget::title {
                background: #f3f4f6;
                border-bottom: 1px solid #d1d5db;
                padding: 8px;
                font-weight: 700;
                font-size: 12px;
            }
            QDockWidget::close-button, QDockWidget::float-button {
                background: transparent;
                border: none;
                padding: 2px;
            }
            QDockWidget::close-button:hover, QDockWidget::float-button:hover {
                background: #e5e7eb;
                border-radius: 3px;
            }
        """)
        
        self.setWidget(content_widget)


class MockParameterPanel(QWidget):
    """Mock parameter panel with scientific controls"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(250)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Parameter groups
        self.create_beam_group(layout)
        self.create_resist_group(layout)
        self.create_simulation_group(layout)
        
        layout.addStretch()
    
    def create_beam_group(self, layout):
        """Create beam parameter group"""
        group = QGroupBox("Beam Parameters")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
                padding-top: 10px;
                margin-top: 6px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background: white;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        
        # Energy
        energy_layout = QHBoxLayout()
        energy_layout.addWidget(QLabel("Energy (keV):"))
        energy_spin = QDoubleSpinBox()
        energy_spin.setRange(1.0, 300.0)
        energy_spin.setValue(30.0)
        energy_spin.setStyleSheet("padding: 4px; border: 1px solid #d1d5db; border-radius: 3px;")
        energy_layout.addWidget(energy_spin)
        
        # Beam Size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Size (nm):"))
        size_spin = QDoubleSpinBox()
        size_spin.setRange(0.1, 50.0)
        size_spin.setValue(1.0)
        size_spin.setStyleSheet("padding: 4px; border: 1px solid #d1d5db; border-radius: 3px;")
        size_layout.addWidget(size_spin)
        
        group_layout.addLayout(energy_layout)
        group_layout.addLayout(size_layout)
        
        layout.addWidget(group)
    
    def create_resist_group(self, layout):
        """Create resist parameter group"""
        group = QGroupBox("Resist Parameters")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
                padding-top: 10px;
                margin-top: 6px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background: white;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        
        # Material
        material_layout = QHBoxLayout()
        material_layout.addWidget(QLabel("Material:"))
        material_combo = QComboBox()
        material_combo.addItems(["PMMA", "HSQ", "ZEP", "Alucone_XPS"])
        material_combo.setCurrentText("Alucone_XPS")
        material_combo.setStyleSheet("padding: 4px; border: 1px solid #d1d5db; border-radius: 3px;")
        material_layout.addWidget(material_combo)
        
        # Thickness
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Thickness (nm):"))
        thickness_spin = QDoubleSpinBox()
        thickness_spin.setRange(1.0, 1000.0)
        thickness_spin.setValue(30.0)
        thickness_spin.setStyleSheet("padding: 4px; border: 1px solid #d1d5db; border-radius: 3px;")
        thickness_layout.addWidget(thickness_spin)
        
        group_layout.addLayout(material_layout)
        group_layout.addLayout(thickness_layout)
        
        layout.addWidget(group)
    
    def create_simulation_group(self, layout):
        """Create simulation parameter group"""
        group = QGroupBox("Simulation")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #374151;
                padding-top: 10px;
                margin-top: 6px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background: white;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        
        # Events
        events_layout = QHBoxLayout()
        events_layout.addWidget(QLabel("Events:"))
        events_spin = QSpinBox()
        events_spin.setRange(1000, 10000000)
        events_spin.setValue(100000)
        events_spin.setStyleSheet("padding: 4px; border: 1px solid #d1d5db; border-radius: 3px;")
        events_layout.addWidget(events_spin)
        
        # Physics options
        physics_check = QCheckBox("Full Physics")
        physics_check.setChecked(True)
        physics_check.setStyleSheet("color: #374151; font-weight: 500;")
        
        group_layout.addLayout(events_layout)
        group_layout.addWidget(physics_check)
        
        layout.addWidget(group)


class MockResultsPanel(QWidget):
    """Mock results panel with analysis data"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Results table
        self.create_results_table(layout)
    
    def create_results_table(self, layout):
        """Create results table"""
        table = QTableWidget(8, 3)
        table.setHorizontalHeaderLabels(["Parameter", "Value", "Unit"])
        
        # Add some mock data
        results_data = [
            ("FWHM", "2.1", "nm"),
            ("α (Forward)", "0.85", ""),
            ("β (Backscatter)", "0.15", ""),
            ("Peak Intensity", "45.2", "eV/nm²"),
            ("Energy Efficiency", "94.0", "%"),
            ("PSF Range", "15.8", "nm"),
            ("Forward Fraction", "85.0", "%"),
            ("Backscatter Fraction", "15.0", "%")
        ]
        
        for i, (param, value, unit) in enumerate(results_data):
            table.setItem(i, 0, QTableWidgetItem(param))
            table.setItem(i, 1, QTableWidgetItem(value))
            table.setItem(i, 2, QTableWidgetItem(unit))
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                gridline-color: #e5e7eb;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #1e40af;
            }
            QHeaderView::section {
                background: #f9fafb;
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid #e5e7eb;
                font-weight: 600;
                font-size: 10px;
                color: #374151;
            }
        """)
        
        # Resize columns
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(table)


class MockFileExplorer(QWidget):
    """Mock file explorer panel"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # File tree
        tree = QTreeWidget()
        tree.setHeaderLabel("Project Files")
        
        # Add some mock file structure
        root = QTreeWidgetItem(tree, ["EBL_Project"])
        
        data_folder = QTreeWidgetItem(root, ["📁 Data"])
        QTreeWidgetItem(data_folder, ["📊 psf_analysis_001.dat"])
        QTreeWidgetItem(data_folder, ["📊 psf_analysis_002.dat"])
        QTreeWidgetItem(data_folder, ["📊 resist_calibration.csv"])
        
        results_folder = QTreeWidgetItem(root, ["📁 Results"])
        QTreeWidgetItem(results_folder, ["📈 fwhm_analysis.png"])
        QTreeWidgetItem(results_folder, ["📈 alpha_beta_plot.png"])
        QTreeWidgetItem(results_folder, ["📄 analysis_report.pdf"])
        
        config_folder = QTreeWidgetItem(root, ["📁 Config"])
        QTreeWidgetItem(config_folder, ["⚙️ beam_settings.json"])
        QTreeWidgetItem(config_folder, ["⚙️ resist_materials.json"])
        
        tree.expandAll()
        
        # Style the tree
        tree.setStyleSheet("""
            QTreeWidget {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px;
                border-bottom: 1px solid #f9fafb;
            }
            QTreeWidget::item:selected {
                background: #dbeafe;
                color: #1e40af;
            }
            QTreeWidget::item:hover:!selected {
                background: #f1f5f9;
            }
            QTreeWidget::branch:has-children:closed {
                image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAYAAADgkQYQAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAFYSURBVBiVjY+9SgNBEIafgxeQFoQUKexsLISAlhYWNkKwsLBQsLKwsLBQG1sLwdZCG1sLG2uxUBsLG7WwsLNQG1sLKwsLtbBQG1sLG7WwsLCwsLBQCwsLG7WwsBBsLCwsLCwsLCwsLCwsBBsLCwsLCwsLCwsLG7WwUAsLCwsLCwsLCwsLtbBQCwsLG7WwsLCwsLBQG1sLG7WwsLCwsLBQG1sLKwsLtbBQCwsLG7WwsLCwsLBQG1sLKwsLtbBQCwsLG7WwsLCwsLBQG1sLKwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsL); }
        """)
        
        layout.addWidget(tree)


class MockLogPanel(QWidget):
    """Mock log/console panel"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Log text area
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        
        # Add some mock log entries
        log_text.append("[12:34:56] INFO: Starting PSF analysis...")
        log_text.append("[12:35:01] INFO: Beam energy set to 30.0 keV")
        log_text.append("[12:35:02] INFO: Resist material: Alucone_XPS")
        log_text.append("[12:35:03] INFO: Initializing Geant4 simulation...")
        log_text.append("[12:35:05] INFO: Running 100,000 primary events")
        log_text.append("[12:35:15] INFO: Processing energy deposition data...")
        log_text.append("[12:35:20] INFO: Calculating PSF parameters...")
        log_text.append("[12:35:22] SUCCESS: Analysis completed successfully")
        log_text.append("[12:35:23] INFO: Results saved to: /project/results/psf_001.dat")
        
        # Style the log
        log_text.setStyleSheet("""
            QTextEdit {
                background: #1f2937;
                border: 1px solid #374151;
                border-radius: 4px;
                color: #d1d5db;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        
        layout.addWidget(log_text)


class MockVisualizationArea(QWidget):
    """Mock main visualization area with tabs"""
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget for different views
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d1d5db;
                background: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #f3f4f6;
                color: #6b7280;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 500;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1f2937;
                border-bottom: 2px solid #3b82f6;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #e5e7eb;
                color: #374151;
            }
        """)
        
        # Create tabs
        main_view = self.create_plot_tab("🎯 2D PSF Map", "Main intensity visualization")
        radial_view = self.create_plot_tab("📊 Radial Profile", "PSF radial distribution")
        log_view = self.create_plot_tab("📈 Log Scale View", "Logarithmic intensity scale")
        comparison_view = self.create_plot_tab("📋 Comparison", "Multi-PSF comparison")
        
        tab_widget.addTab(main_view, "Main View")
        tab_widget.addTab(radial_view, "Radial")
        tab_widget.addTab(log_view, "Log Scale")
        tab_widget.addTab(comparison_view, "Compare")
        
        layout.addWidget(tab_widget)
    
    def create_plot_tab(self, title: str, description: str) -> QWidget:
        """Create a plot tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Plot area placeholder
        plot_area = QLabel(f"{title}\n\n{description}\n\nInteractive visualization area")
        plot_area.setAlignment(Qt.AlignCenter)
        plot_area.setStyleSheet("""
            QLabel {
                background: #f8fafc;
                border: 2px dashed #cbd5e1;
                border-radius: 8px;
                color: #64748b;
                font-size: 14px;
                line-height: 1.6;
                padding: 60px;
            }
        """)
        
        layout.addWidget(plot_area)
        return tab


class ScientificMultiPanelMockup(QMainWindow):
    """
    Mockup #3: Multi-Panel Workspace Design
    
    Features demonstrated:
    - Dockable panels for different tools
    - Flexible workspace layout
    - Multiple simultaneous views
    - Panel-based organization
    - File explorer integration
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scientific GUI Mockup #3: Multi-Panel Workspace Design")
        self.setMinimumSize(1400, 900)
        
        # Light theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the multi-panel interface"""
        # Central visualization area
        viz_area = MockVisualizationArea()
        self.setCentralWidget(viz_area)
        
        # Create dockable panels
        self.create_parameter_panel()
        self.create_results_panel()
        self.create_file_explorer_panel()
        self.create_log_panel()
        
        # Setup menu bar
        self.create_menu_bar()
        
        # Setup status bar
        self.create_status_bar()
    
    def create_parameter_panel(self):
        """Create parameters dock panel"""
        params_widget = MockParameterPanel()
        params_dock = MockDockablePanel("Parameters", params_widget, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, params_dock)
    
    def create_results_panel(self):
        """Create results dock panel"""
        results_widget = MockResultsPanel()
        results_dock = MockDockablePanel("Analysis Results", results_widget, self)
        self.addDockWidget(Qt.RightDockWidgetArea, results_dock)
    
    def create_file_explorer_panel(self):
        """Create file explorer dock panel"""
        explorer_widget = MockFileExplorer()
        explorer_dock = MockDockablePanel("Project Files", explorer_widget, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, explorer_dock)
    
    def create_log_panel(self):
        """Create log dock panel"""
        log_widget = MockLogPanel()
        log_dock = MockDockablePanel("Console Log", log_widget, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
                padding: 4px 8px;
                font-size: 11px;
            }
            QMenuBar::item {
                padding: 6px 12px;
                background: transparent;
                color: #374151;
            }
            QMenuBar::item:selected {
                background: #e2e8f0;
                color: #1f2937;
            }
        """)
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        # Analysis menu
        analysis_menu = menubar.addMenu("Analysis")
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # Help menu
        help_menu = menubar.addMenu("Help")
    
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
        
        status_bar.showMessage("Ready • Panels: 4 active • Workspace: Multi-panel layout")


def main():
    """Run multi-panel mockup"""
    app = QApplication(sys.argv)
    
    # High DPI support
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    
    # Set font for high DPI
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = ScientificMultiPanelMockup()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()