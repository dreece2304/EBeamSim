#!/usr/bin/env python3
"""
Modern EBL Simulation Launcher
===============================

Unified modern launcher that provides clear separation between:
- PSF Analysis workflow (resist characterization, BEAMER integration)
- Pattern Simulation workflow (complex pattern design and visualization)

Features intuitive mode selection with modern Material Design 3 interface.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "interfaces"))
sys.path.append(str(Path(__file__).parent / "widgets" / "modern"))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFrame, QStackedWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QLinearGradient

# Import modern components
from modern_components import MaterialCard, ModernButton, ModernTabWidget, ModernProgressBar

# Import the specialized interfaces
from psf_dashboard_interface import PSFDashboardInterface
from pattern_interface import PatternSimulationInterface

# Import simulation utilities
sys.path.append(str(Path(__file__).parent / "utils"))
from threading_utils import SimulationWorker


class ModeSelectionCard(MaterialCard):
    """Enhanced card for mode selection with visual preview"""
    
    mode_selected = Signal(str)
    
    def __init__(self, mode_name: str, title: str, description: str, 
                 features: list, icon_path: str = "", parent=None):
        super().__init__(parent=parent)
        self.mode_name = mode_name
        self.setup_mode_ui(title, description, features, icon_path)
        
        # Make card clickable
        self.setCursor(Qt.PointingHandCursor)
    
    def setup_mode_ui(self, title: str, description: str, features: list, icon_path: str):
        """Setup the mode selection UI"""
        layout = QVBoxLayout()
        layout.setSpacing(12)  # Reduced spacing
        layout.setContentsMargins(20, 20, 20, 20)  # Reduced margins
        
        # Icon and title section
        header_layout = QHBoxLayout()
        
        # Mode icon (placeholder for now)
        icon_label = QLabel("🔬" if "PSF" in title else "🎯")
        icon_label.setStyleSheet("""
            font-size: 32px;
            margin-right: 12px;
        """)
        
        # Title and subtitle
        title_container = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #6366f1;
            margin-bottom: 6px;
        """)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #9ca3af;
            line-height: 1.4;
        """)
        desc_label.setWordWrap(True)
        
        title_container.addWidget(title_label)
        title_container.addWidget(desc_label)
        title_container.addStretch()
        
        header_layout.addWidget(icon_label)
        title_widget = QWidget()
        title_widget.setLayout(title_container)
        header_layout.addWidget(title_widget, 1)
        
        # Features list
        features_label = QLabel("Key Features:")
        features_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #f9fafb;
            margin-top: 12px;
            margin-bottom: 6px;
        """)
        
        features_container = QVBoxLayout()
        for feature in features:
            feature_item = QLabel(f"• {feature}")
            feature_item.setStyleSheet("""
                font-size: 11px;
                color: #d1d5db;
                margin-left: 12px;
                margin-bottom: 2px;
            """)
            features_container.addWidget(feature_item)
        
        # Select button
        self.select_btn = ModernButton(f"Select {title}", "primary")
        self.select_btn.clicked.connect(lambda: self.mode_selected.emit(self.mode_name))
        
        # Add all components to main layout
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
        layout.addWidget(features_label)
        
        features_widget = QWidget()
        features_widget.setLayout(features_container)
        layout.addWidget(features_widget)
        
        layout.addStretch()
        layout.addWidget(self.select_btn)
        
        # Add to card
        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.layout().addWidget(main_widget)
    
    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.LeftButton:
            self.mode_selected.emit(self.mode_name)
        super().mousePressEvent(event)


class ModernHeaderWidget(QWidget):
    """Modern application header with gradient and branding"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)  # Reduced from 140 for high DPI
        self.setup_ui()
    
    def setup_ui(self):
        """Setup header UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)  # Reduced margins
        layout.setSpacing(4)
        
        # Main title
        title = QLabel("EBL Simulation Suite")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.3px;
        """)
        
        # Subtitle
        subtitle = QLabel("Professional Electron Beam Lithography Analysis & Pattern Design")
        subtitle.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #cbd5e1;
            margin-top: 2px;
        """)
        
        # Version badge
        version_badge = QLabel("v4.0 • Modern Interface")
        version_badge.setStyleSheet("""
            font-size: 11px;
            font-weight: 600;
            color: #94a3b8;
            margin-top: 4px;
        """)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version_badge)
        layout.addStretch()
    
    def paintEvent(self, event):
        """Custom paint for gradient background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#0f172a"))
        gradient.setColorAt(0.5, QColor("#1e293b"))
        gradient.setColorAt(1, QColor("#334155"))
        
        painter.fillRect(self.rect(), gradient)


class EBLModernLauncher(QMainWindow):
    """Modern EBL Simulation Launcher with Mode Selection"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EBL Simulation Suite - Modern Interface")
        
        # Optimize sizing for high DPI displays
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Initialize simulation worker
        self.simulation_worker = None
        
        # Load modern stylesheet
        self.load_stylesheet()
        
        # Setup UI
        self.setup_ui()
        
        # Setup connections
        self.setup_connections()
    
    def load_stylesheet(self):
        """Load the modern stylesheet"""
        style_path = Path(__file__).parent / "resources" / "modern_styles.qss"
        if style_path.exists():
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())
    
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.header = ModernHeaderWidget()
        main_layout.addWidget(self.header)
        
        # Main content with stacked widget
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, 1)
        
        # Create mode selection page
        self.mode_selection_page = self.create_mode_selection_page()
        self.stacked_widget.addWidget(self.mode_selection_page)
        
        # Create PSF interface
        self.psf_interface = PSFDashboardInterface()
        self.stacked_widget.addWidget(self.psf_interface)
        
        # Create Pattern interface
        self.pattern_interface = PatternSimulationInterface()
        self.stacked_widget.addWidget(self.pattern_interface)
        
        # Status bar
        self.statusBar().showMessage("Ready • Select simulation mode to begin")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background: #1f2937;
                border-top: 1px solid #374151;
                padding: 8px 16px;
                font-weight: 500;
                color: #d1d5db;
            }
        """)
    
    def create_mode_selection_page(self) -> QWidget:
        """Create the mode selection landing page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)  # Reduced margins
        layout.setSpacing(20)  # Reduced spacing
        
        # Welcome section
        welcome_label = QLabel("Choose Your Simulation Workflow")
        welcome_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #f9fafb;
            text-align: center;
            margin-bottom: 12px;
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        
        description_label = QLabel(
            "Select the simulation type that best matches your research objectives. "
            "Each workflow is optimized for specific lithography analysis tasks."
        )
        description_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #9ca3af;
            text-align: center;
            line-height: 1.5;
        """)
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)
        
        layout.addWidget(welcome_label)
        layout.addWidget(description_label)
        
        # Mode selection cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)  # Reduced spacing between cards
        
        # PSF Analysis Card
        psf_features = [
            "Point spread function characterization",
            "Resist material optimization",
            "α/β parameter extraction",
            "BEAMER export integration",
            "Energy deposition analysis",
            "FWHM and proximity calculations"
        ]
        
        self.psf_card = ModeSelectionCard(
            "psf",
            "PSF Analysis",
            "Specialized for point spread function characterization and resist optimization studies. Ideal for understanding electron scattering and material properties.",
            psf_features
        )
        
        # Pattern Simulation Card
        pattern_features = [
            "Complex pattern design tools",
            "Multi-pattern exposure simulation",
            "3D dose visualization",
            "Proximity effect correction",
            "GDS file import/export",
            "Advanced pattern analysis"
        ]
        
        self.pattern_card = ModeSelectionCard(
            "pattern",
            "Pattern Simulation",
            "Advanced pattern design and simulation workflow. Perfect for complex lithography patterns and proximity effect studies.",
            pattern_features
        )
        
        cards_layout.addWidget(self.psf_card)
        cards_layout.addWidget(self.pattern_card)
        
        layout.addLayout(cards_layout, 1)
        
        # Back to selection button (hidden initially)
        self.back_to_selection_btn = ModernButton("← Back to Mode Selection", "secondary")
        self.back_to_selection_btn.setVisible(False)
        layout.addWidget(self.back_to_selection_btn)
        
        return page
    
    def setup_connections(self):
        """Setup signal connections"""
        # Mode selection
        self.psf_card.mode_selected.connect(self.switch_to_mode)
        self.pattern_card.mode_selected.connect(self.switch_to_mode)
        self.back_to_selection_btn.clicked.connect(self.show_mode_selection)
        
        # Simulation interfaces
        self.psf_interface.simulation_started.connect(self.start_simulation)
        self.pattern_interface.simulation_started.connect(self.start_simulation)
    
    def switch_to_mode(self, mode: str):
        """Switch to the selected simulation mode"""
        if mode == "psf":
            self.stacked_widget.setCurrentWidget(self.psf_interface)
            self.statusBar().showMessage("PSF Analysis Mode • Configure parameters and run analysis")
        elif mode == "pattern":
            self.stacked_widget.setCurrentWidget(self.pattern_interface)
            self.statusBar().showMessage("Pattern Simulation Mode • Design patterns and run simulation")
        
        # Show back button
        self.back_to_selection_btn.setVisible(True)
        
        # Update window title
        mode_name = "PSF Analysis" if mode == "psf" else "Pattern Simulation"
        self.setWindowTitle(f"EBL Simulation Suite - {mode_name}")
    
    def show_mode_selection(self):
        """Return to mode selection page"""
        self.stacked_widget.setCurrentWidget(self.mode_selection_page)
        self.back_to_selection_btn.setVisible(False)
        self.setWindowTitle("EBL Simulation Suite - Modern Interface")
        self.statusBar().showMessage("Ready • Select simulation mode to begin")
    
    def start_simulation(self, params: dict):
        """Start simulation with given parameters"""
        simulation_type = params.get('type', 'unknown')
        self.statusBar().showMessage(f"Running {simulation_type} simulation...")
        
        # Connect progress updates
        current_interface = self.stacked_widget.currentWidget()
        if hasattr(current_interface, 'update_progress'):
            # For now, we'll simulate progress
            # In a real implementation, this would create a SimulationWorker with proper parameters
            self.simulate_progress(current_interface)
    
    def simulate_progress(self, interface):
        """Simulate simulation progress (placeholder)"""
        self.progress_timer = QTimer()
        self.progress_value = 0
        
        def update_progress():
            self.progress_value += 2
            interface.update_progress(self.progress_value)
            
            if self.progress_value >= 100:
                self.progress_timer.stop()
                self.statusBar().showMessage("Simulation completed successfully")
        
        self.progress_timer.timeout.connect(update_progress)
        self.progress_timer.start(100)  # Update every 100ms


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EBL Simulation Suite")
    app.setApplicationVersion("4.0")
    app.setOrganizationName("EBL Research")
    
    # Optimize for high DPI displays
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)  # Allow proper DPI scaling
    
    # Set appropriately sized font for high DPI displays
    font = QFont("Inter", 9)  # Smaller base font size for high DPI
    if not font.exactMatch():
        font = QFont("Segoe UI", 9)  # Reduced from 10 to 9
    app.setFont(font)
    
    # Create and show launcher
    launcher = EBLModernLauncher()
    launcher.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()