"""
Modular EBL Simulation GUI - Main Application
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QStatusBar, QMessageBox, QFileDialog,
    QProgressBar, QLabel, QPushButton, QSplitter
)
from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QAction, QFont

# Import our modular components
from models.simulation_model import SimulationModel
from models.material_model import MaterialModel
from models.beam_model import BeamModel

from services.simulation_controller import SimulationController
from services.macro_generator import MacroGeneratorService
from services.file_service import FileService
from services.beamer_converter import BeamerConverterService

from widgets.resist_properties_widget import ResistPropertiesWidget
from widgets.enhanced_beam_widget import EnhancedBeamWidget
from widgets.simulation_widget import SimulationWidget
from widgets.output_widget import OutputWidget
from widgets.plot_widget import PlotWidget

from utils.plotting_utils import PlottingUtils


class ModularEBLMainWindow(QMainWindow):
    """Main window for modular EBL simulation GUI"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("EBL", "ModularSimulationGUI")
        
        # Initialize services
        self.simulation_controller = SimulationController(self)
        self.macro_generator = MacroGeneratorService()
        self.file_service = FileService()
        self.beamer_converter = BeamerConverterService()
        
        # Initialize data models
        self.simulation_model = SimulationModel()
        
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.connect_signals()
        self.load_settings()
        
        # Apply plotting style
        PlottingUtils.setup_matplotlib_style()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("EBL Simulation - Modular Edition")
        self.setMinimumSize(1400, 900)
        
        # Apply modern styling
        self.apply_modern_style()
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create and add tabs
        self.setup_tabs()
        
        layout.addWidget(self.tab_widget)
        
        # Add control panel at bottom
        self.setup_control_panel()
        layout.addLayout(self.control_panel_layout)
    
    def setup_tabs(self):
        """Setup all tabs"""
        # Resist Properties Tab
        self.resist_widget = ResistPropertiesWidget()
        self.tab_widget.addTab(self.resist_widget, "Resist Properties")
        
        # Beam Parameters Tab
        self.beam_widget = EnhancedBeamWidget()
        self.tab_widget.addTab(self.beam_widget, "Beam Parameters")
        
        # Simulation Control Tab
        self.simulation_widget = SimulationWidget()
        self.tab_widget.addTab(self.simulation_widget, "Simulation")
        
        # Output Management Tab
        self.output_widget = OutputWidget()
        self.tab_widget.addTab(self.output_widget, "Output")
        
        # Visualization Tab
        self.plot_widget = PlotWidget()
        self.tab_widget.addTab(self.plot_widget, "Visualization")
    
    def setup_control_panel(self):
        """Setup bottom control panel"""
        self.control_panel_layout = QHBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.control_panel_layout.addWidget(self.progress_bar)
        
        # Quick action buttons
        self.quick_run_btn = QPushButton("Quick Run")
        self.quick_run_btn.setFixedWidth(100)
        self.control_panel_layout.addWidget(self.quick_run_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.setEnabled(False)
        self.control_panel_layout.addWidget(self.stop_btn)
        
        self.control_panel_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.control_panel_layout.addWidget(self.status_label)
    
    def setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Configuration", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_configuration)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Configuration", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_configuration)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Configuration", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        validate_action = QAction("Validate Configuration", self)
        validate_action.triggered.connect(self.validate_configuration)
        tools_menu.addAction(validate_action)
        
        beamer_action = QAction("Convert to BEAMER", self)
        beamer_action.triggered.connect(self.convert_to_beamer)
        tools_menu.addAction(beamer_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def connect_signals(self):
        """Connect signals between components"""
        # Connect widget signals to update simulation model
        self.resist_widget.material_changed.connect(self.on_material_changed)
        self.beam_widget.beam_changed.connect(self.on_beam_changed)
        
        # Connect simulation controller signals
        self.simulation_controller.simulation_started.connect(self.on_simulation_started)
        self.simulation_controller.simulation_finished.connect(self.on_simulation_finished)
        self.simulation_controller.simulation_progress.connect(self.on_simulation_progress)
        self.simulation_controller.simulation_output.connect(self.on_simulation_output)
        self.simulation_controller.simulation_error.connect(self.on_simulation_error)
        
        # Connect control panel buttons
        self.quick_run_btn.clicked.connect(self.quick_run_simulation)
        self.stop_btn.clicked.connect(self.stop_simulation)
    
    def apply_modern_style(self):
        """Apply modern dark theme styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #555555;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #007acc;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #3c3c3c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #3c3c3c;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
        """)
    
    def on_material_changed(self, material: MaterialModel):
        """Handle material change"""
        self.simulation_model.material = material
        self.update_status("Material updated")
    
    def on_beam_changed(self, beam: BeamModel):
        """Handle beam change"""
        self.simulation_model.beam = beam
        self.update_status("Beam parameters updated")
    
    def on_simulation_started(self):
        """Handle simulation start"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.quick_run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.update_status("Simulation running...")
    
    def on_simulation_finished(self, success: bool, message: str):
        """Handle simulation completion"""
        self.progress_bar.setVisible(False)
        self.quick_run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.update_status("Simulation completed successfully")
            QMessageBox.information(self, "Success", message)
        else:
            self.update_status("Simulation failed")
            QMessageBox.warning(self, "Simulation Failed", message)
    
    def on_simulation_progress(self, progress: int):
        """Handle simulation progress update"""
        self.progress_bar.setValue(progress)
        self.update_status(f"Simulation progress: {progress}%")
    
    def on_simulation_output(self, output: str):
        """Handle simulation output"""
        # Forward to output widget if it exists
        if hasattr(self, 'output_widget'):
            # Add output handling to output widget
            pass
    
    def on_simulation_error(self, error: str):
        """Handle simulation error"""
        self.update_status(f"Error: {error}")
        QMessageBox.critical(self, "Simulation Error", error)
    
    def update_status(self, message: str):
        """Update status bar and label"""
        self.status_bar.showMessage(message)
        self.status_label.setText(message)
    
    def quick_run_simulation(self):
        """Run simulation with current parameters"""
        # Validate configuration first
        if not self.simulation_model.validate():
            QMessageBox.warning(self, "Invalid Configuration", 
                              "Please check your simulation parameters")
            return
        
        # Check if executable is set
        valid, message = self.simulation_controller.validate_setup()
        if not valid:
            QMessageBox.warning(self, "Setup Error", message)
            return
        
        # Start simulation
        success = self.simulation_controller.run_simulation(self.simulation_model)
        if not success:
            QMessageBox.critical(self, "Failed to Start", 
                               "Could not start simulation")
    
    def stop_simulation(self):
        """Stop running simulation"""
        self.simulation_controller.stop_simulation()
        self.update_status("Stopping simulation...")
    
    def new_configuration(self):
        """Create new configuration"""
        self.simulation_model = SimulationModel()
        self.resist_widget.set_material(self.simulation_model.material)
        self.beam_widget.set_beam(self.simulation_model.beam)
        self.update_status("New configuration created")
    
    def open_configuration(self):
        """Open configuration from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "", "JSON files (*.json)"
        )
        
        if file_path:
            try:
                self.simulation_model = self.file_service.load_simulation_config(Path(file_path))
                self.resist_widget.set_material(self.simulation_model.material)
                self.beam_widget.set_beam(self.simulation_model.beam)
                self.update_status(f"Configuration loaded from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load configuration:\n{str(e)}")
    
    def save_configuration(self):
        """Save configuration to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "simulation_config.json", "JSON files (*.json)"
        )
        
        if file_path:
            try:
                self.file_service.save_simulation_config(self.simulation_model, Path(file_path))
                self.update_status(f"Configuration saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")
    
    def validate_configuration(self):
        """Validate current configuration"""
        if self.simulation_model.validate():
            QMessageBox.information(self, "Validation", "Configuration is valid!")
        else:
            QMessageBox.warning(self, "Validation", "Configuration has errors. Please check parameters.")
    
    def convert_to_beamer(self):
        """Convert PSF data to BEAMER format"""
        # This would typically be handled by the output widget
        QMessageBox.information(self, "BEAMER Conversion", 
                              "BEAMER conversion feature available in Output tab")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About EBL Simulation", 
                         """
                         EBL Simulation - Modular Edition
                         
                         A modular, extensible GUI for electron beam lithography simulations.
                         Built with PySide6 and featuring:
                         
                         • Clean separation of concerns
                         • Testable components
                         • Modern UI design
                         • Advanced visualization
                         • BEAMER compatibility
                         
                         Version 2.0
                         """)
    
    def load_settings(self):
        """Load application settings"""
        # Restore window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Load executable path
        executable_path = self.settings.value("executable_path", "")
        if executable_path:
            self.simulation_controller.set_executable_path(executable_path)
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        
    def closeEvent(self, event):
        """Handle application close"""
        self.save_settings()
        
        # Stop any running simulation
        if self.simulation_controller.get_simulation_status()["is_running"]:
            reply = QMessageBox.question(
                self, "Simulation Running", 
                "A simulation is running. Stop it and exit?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.simulation_controller.stop_simulation()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("EBL Simulation")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("EBL")
    
    # Set application icon (if available)
    # app.setWindowIcon(QIcon("path/to/icon.png"))
    
    window = ModularEBLMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()