#!/usr/bin/env python3
"""
Scientific GUI Mockup #4: Wizard/Step-by-Step Design
====================================================

Based on research findings, this mockup demonstrates:
- Guided workflow with step-by-step process
- Progressive disclosure of complexity
- Clear navigation and progress indication
- Beginner-friendly approach with expert options

Research Source: Modern scientific software increasingly uses guided
workflows to make complex analysis accessible to non-experts while
providing expert options for advanced users.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QGroupBox, QStackedWidget,
    QProgressBar, QWizard, QWizardPage, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QRadioButton, QButtonGroup, QTextEdit, QListWidget,
    QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

class MockStepIndicator(QWidget):
    """Mock step indicator showing progress through wizard"""
    
    def __init__(self, steps: list, current_step: int = 0):
        super().__init__()
        self.steps = steps
        self.current_step = current_step
        self.setFixedHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        for i, step_name in enumerate(steps):
            # Step circle
            step_widget = self.create_step_widget(i + 1, step_name, i <= current_step, i == current_step)
            layout.addWidget(step_widget)
            
            # Connector line
            if i < len(steps) - 1:
                connector = self.create_connector(i < current_step)
                layout.addWidget(connector)
    
    def create_step_widget(self, number: int, name: str, completed: bool, active: bool) -> QWidget:
        """Create individual step widget"""
        widget = QWidget()
        widget.setFixedWidth(120)
        
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        
        # Circle with number
        circle = QLabel(str(number))
        circle.setFixedSize(40, 40)
        circle.setAlignment(Qt.AlignCenter)
        
        if completed and not active:
            circle_style = """
                background: #10b981;
                color: white;
                font-weight: 700;
                font-size: 16px;
                border-radius: 20px;
            """
        elif active:
            circle_style = """
                background: #3b82f6;
                color: white;
                font-weight: 700;
                font-size: 16px;
                border-radius: 20px;
                border: 3px solid #93c5fd;
            """
        else:
            circle_style = """
                background: #e5e7eb;
                color: #9ca3af;
                font-weight: 600;
                font-size: 16px;
                border-radius: 20px;
            """
        
        circle.setStyleSheet(f"QLabel {{ {circle_style} }}")
        
        # Step name
        name_label = QLabel(name)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        
        if active:
            name_style = "font-weight: 700; color: #1f2937; font-size: 11px;"
        elif completed:
            name_style = "font-weight: 600; color: #10b981; font-size: 11px;"
        else:
            name_style = "font-weight: 500; color: #9ca3af; font-size: 11px;"
        
        name_label.setStyleSheet(f"QLabel {{ {name_style} }}")
        
        layout.addWidget(circle)
        layout.addWidget(name_label)
        
        return widget
    
    def create_connector(self, completed: bool) -> QWidget:
        """Create connector line between steps"""
        connector = QFrame()
        connector.setFixedSize(40, 4)
        connector.setFrameShape(QFrame.HLine)
        
        if completed:
            connector.setStyleSheet("background: #10b981; border: none;")
        else:
            connector.setStyleSheet("background: #e5e7eb; border: none;")
        
        # Center vertically
        container = QWidget()
        container.setFixedHeight(80)
        layout = QVBoxLayout(container)
        layout.addStretch()
        layout.addWidget(connector)
        layout.addStretch()
        
        return container


class MockWelcomeStep(QWidget):
    """Welcome/introduction step"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome header
        welcome_label = QLabel("Welcome to PSF Analysis Wizard")
        welcome_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 16px;
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        
        # Description
        desc_label = QLabel(
            "This wizard will guide you through setting up and running a Point Spread Function analysis.\n\n"
            "We'll help you configure:\n"
            "• Electron beam parameters\n"
            "• Resist material properties\n" 
            "• Simulation settings\n"
            "• Analysis and visualization options"
        )
        desc_label.setStyleSheet("""
            font-size: 14px;
            color: #6b7280;
            line-height: 1.6;
            margin-bottom: 24px;
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        
        # Experience level selection
        level_group = QGroupBox("Select your experience level:")
        level_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                padding-top: 16px;
                margin-top: 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px 0 8px;
                background: white;
            }
        """)
        
        level_layout = QVBoxLayout(level_group)
        
        self.beginner_radio = QRadioButton("Beginner - Guide me through all options")
        self.intermediate_radio = QRadioButton("Intermediate - Show key settings with defaults")
        self.expert_radio = QRadioButton("Expert - Show all advanced options")
        
        self.beginner_radio.setChecked(True)  # Default
        
        for radio in [self.beginner_radio, self.intermediate_radio, self.expert_radio]:
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 12px;
                    color: #374151;
                    padding: 8px;
                    font-weight: 500;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)
        
        level_layout.addWidget(self.beginner_radio)
        level_layout.addWidget(self.intermediate_radio)
        level_layout.addWidget(self.expert_radio)
        
        # Quick start options
        quickstart_group = QGroupBox("Or use a preset configuration:")
        quickstart_group.setStyleSheet(level_group.styleSheet())
        
        quickstart_layout = QVBoxLayout(quickstart_group)
        
        presets = [
            ("Standard JEOL Setup", "30 keV, 1 nm beam, PMMA resist"),
            ("High Resolution", "30 keV, 0.5 nm beam, HSQ resist"),
            ("Alucone Research", "30 keV, 1 nm beam, Alucone_XPS resist")
        ]
        
        for preset_name, preset_desc in presets:
            preset_btn = QPushButton(f"{preset_name}\n{preset_desc}")
            preset_btn.setStyleSheet("""
                QPushButton {
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 11px;
                    color: #374151;
                }
                QPushButton:hover {
                    background: #f1f5f9;
                    border-color: #3b82f6;
                }
            """)
            quickstart_layout.addWidget(preset_btn)
        
        layout.addWidget(welcome_label)
        layout.addWidget(desc_label)
        layout.addWidget(level_group)
        layout.addWidget(quickstart_group)
        layout.addStretch()


class MockBeamConfigStep(QWidget):
    """Beam configuration step"""
    
    def __init__(self, experience_level: str = "beginner"):
        super().__init__()
        self.experience_level = experience_level
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(32)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Left side - configuration
        config_side = self.create_config_side()
        layout.addWidget(config_side, 1)
        
        # Right side - help and preview
        help_side = self.create_help_side()
        layout.addWidget(help_side, 1)
    
    def create_config_side(self) -> QWidget:
        """Create configuration controls"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Configure Electron Beam")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 24px;
        """)
        
        # Parameters
        params_group = QGroupBox("Beam Parameters")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                padding-top: 16px;
                margin-top: 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px 0 8px;
                background: white;
            }
        """)
        
        params_layout = QGridLayout(params_group)
        params_layout.setSpacing(16)
        
        # Energy
        params_layout.addWidget(QLabel("Accelerating Voltage:"), 0, 0)
        self.energy_spin = QDoubleSpinBox()
        self.energy_spin.setRange(1.0, 300.0)
        self.energy_spin.setValue(30.0)
        self.energy_spin.setSuffix(" keV")
        self.energy_spin.setStyleSheet("padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;")
        params_layout.addWidget(self.energy_spin, 0, 1)
        
        # Beam size
        params_layout.addWidget(QLabel("Beam Size (FWHM):"), 1, 0)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(0.1, 50.0)
        self.size_spin.setValue(1.0)
        self.size_spin.setSuffix(" nm")
        self.size_spin.setStyleSheet("padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;")
        params_layout.addWidget(self.size_spin, 1, 1)
        
        # Current
        params_layout.addWidget(QLabel("Beam Current:"), 2, 0)
        self.current_spin = QDoubleSpinBox()
        self.current_spin.setRange(0.1, 1000.0)
        self.current_spin.setValue(10.0)
        self.current_spin.setSuffix(" pA")
        self.current_spin.setStyleSheet("padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;")
        params_layout.addWidget(self.current_spin, 2, 1)
        
        # Advanced options (only for intermediate/expert)
        if self.experience_level in ["intermediate", "expert"]:
            advanced_group = QGroupBox("Advanced Options")
            advanced_group.setStyleSheet(params_group.styleSheet())
            
            advanced_layout = QGridLayout(advanced_group)
            
            # Convergence angle
            advanced_layout.addWidget(QLabel("Convergence Angle:"), 0, 0)
            conv_spin = QDoubleSpinBox()
            conv_spin.setRange(1.0, 50.0)
            conv_spin.setValue(10.0)
            conv_spin.setSuffix(" mrad")
            conv_spin.setStyleSheet(self.energy_spin.styleSheet())
            advanced_layout.addWidget(conv_spin, 0, 1)
            
            layout.addWidget(advanced_group)
        
        layout.addWidget(title)
        layout.addWidget(params_group)
        layout.addStretch()
        
        return widget
    
    def create_help_side(self) -> QWidget:
        """Create help and preview panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Help section
        help_group = QGroupBox("Parameter Guide")
        help_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                padding-top: 16px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
        """)
        
        help_layout = QVBoxLayout(help_group)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>Beam Parameter Guide</h3>
        <p><strong>Accelerating Voltage:</strong> Higher voltages provide better penetration but may cause more backscattering. Typical range: 10-100 keV.</p>
        <p><strong>Beam Size:</strong> Smaller beams provide higher resolution but lower current. Modern systems: 0.5-5 nm.</p>
        <p><strong>Beam Current:</strong> Higher current reduces exposure time but may cause sample damage. Balance with dose requirements.</p>
        <h3>Typical Settings:</h3>
        <ul>
            <li><strong>High Resolution:</strong> 30 keV, 0.5 nm, 5 pA</li>
            <li><strong>Standard:</strong> 30 keV, 1.0 nm, 10 pA</li>
            <li><strong>High Throughput:</strong> 30 keV, 2.0 nm, 50 pA</li>
        </ul>
        """)
        help_text.setStyleSheet("""
            QTextEdit {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 12px;
                font-size: 11px;
                line-height: 1.5;
            }
        """)
        
        help_layout.addWidget(help_text)
        
        # Preview section
        preview_group = QGroupBox("Current Settings Preview")
        preview_group.setStyleSheet(help_group.styleSheet())
        
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("30.0 keV • 1.0 nm FWHM • 10.0 pA")
        self.preview_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #1f2937;
            text-align: center;
            background: #dbeafe;
            padding: 16px;
            border-radius: 6px;
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)
        
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(help_group, 2)
        layout.addWidget(preview_group)
        
        return widget


class MockSummaryStep(QWidget):
    """Final summary and run step"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # Title
        title = QLabel("Review Configuration & Run Analysis")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 24px;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # Configuration summary
        summary_splitter = QSplitter(Qt.Horizontal)
        
        # Left - settings summary
        settings_widget = self.create_settings_summary()
        summary_splitter.addWidget(settings_widget)
        
        # Right - estimated results
        estimates_widget = self.create_estimates_panel()
        summary_splitter.addWidget(estimates_widget)
        
        # Run controls
        run_controls = self.create_run_controls()
        
        layout.addWidget(title)
        layout.addWidget(summary_splitter, 1)
        layout.addWidget(run_controls)
    
    def create_settings_summary(self) -> QWidget:
        """Create settings summary panel"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box)
        widget.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        
        title = QLabel("Configuration Summary")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 16px;
        """)
        
        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        summary_text.setMaximumHeight(300)
        summary_text.setHtml("""
        <h3>Beam Parameters</h3>
        <p>• Energy: <strong>30.0 keV</strong></p>
        <p>• Beam Size: <strong>1.0 nm FWHM</strong></p>
        <p>• Current: <strong>10.0 pA</strong></p>
        
        <h3>Resist Parameters</h3>
        <p>• Material: <strong>Alucone_XPS</strong></p>
        <p>• Thickness: <strong>30.0 nm</strong></p>
        <p>• Density: <strong>1.35 g/cm³</strong></p>
        
        <h3>Simulation Settings</h3>
        <p>• Primary Events: <strong>100,000</strong></p>
        <p>• Physics: <strong>Full (fluorescence, Auger)</strong></p>
        <p>• Grid Size: <strong>512 × 512</strong></p>
        <p>• Pixel Size: <strong>0.5 nm</strong></p>
        """)
        summary_text.setStyleSheet("""
            QTextEdit {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 12px;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(summary_text)
        
        return widget
    
    def create_estimates_panel(self) -> QWidget:
        """Create estimation panel"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box)
        widget.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        
        title = QLabel("Estimated Results")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 16px;
        """)
        
        estimates_text = QTextEdit()
        estimates_text.setReadOnly(True)
        estimates_text.setMaximumHeight(300)
        estimates_text.setHtml("""
        <h3>Expected PSF Characteristics</h3>
        <p>• <strong>FWHM:</strong> ~2.0-2.5 nm</p>
        <p>• <strong>Forward Scattering (α):</strong> ~0.8-0.9</p>
        <p>• <strong>Backscattering (β):</strong> ~0.1-0.2</p>
        <p>• <strong>Energy Efficiency:</strong> ~90-95%</p>
        
        <h3>Simulation Time</h3>
        <p>• <strong>Estimated Duration:</strong> 5-10 minutes</p>
        <p>• <strong>Memory Usage:</strong> ~2 GB</p>
        <p>• <strong>Output Size:</strong> ~50 MB</p>
        
        <h3>Analysis Features</h3>
        <p>• Real-time progress monitoring</p>
        <p>• Interactive visualization</p>
        <p>• Statistical analysis</p>
        <p>• BEAMER export compatibility</p>
        """)
        estimates_text.setStyleSheet("""
            QTextEdit {
                background: #f0f9ff;
                border: 1px solid #bae6fd;
                border-radius: 4px;
                padding: 12px;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(estimates_text)
        
        return widget
    
    def create_run_controls(self) -> QWidget:
        """Create run control panel"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box)
        widget.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(16)
        
        # Status indicator
        status_label = QLabel("● Ready to Run")
        status_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #10b981;
        """)
        
        # Run button
        run_button = QPushButton("Start PSF Analysis")
        run_button.setFixedHeight(50)
        run_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 32px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #047857);
            }
        """)
        
        # Save config button
        save_button = QPushButton("Save Configuration")
        save_button.setFixedHeight(40)
        save_button.setStyleSheet("""
            QPushButton {
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px 20px;
                color: #374151;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #e5e7eb;
            }
        """)
        
        layout.addWidget(status_label)
        layout.addStretch()
        layout.addWidget(save_button)
        layout.addWidget(run_button)
        
        return widget


class ScientificWizardMockup(QMainWindow):
    """
    Mockup #4: Wizard/Step-by-Step Design
    
    Features demonstrated:
    - Guided step-by-step workflow
    - Experience level adaptation
    - Progress indication
    - Help and guidance integration
    - Summary and review
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scientific GUI Mockup #4: Wizard/Step-by-Step Design")
        self.setMinimumSize(1200, 800)
        
        # Light theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
        """)
        
        self.current_step = 0
        self.steps = ["Welcome", "Beam Config", "Resist Setup", "Simulation", "Review & Run"]
        self.experience_level = "beginner"
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the wizard interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Step indicator
        self.step_indicator = MockStepIndicator(self.steps, self.current_step)
        layout.addWidget(self.step_indicator)
        
        # Main content area
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack, 1)
        
        # Create wizard steps
        self.welcome_step = MockWelcomeStep()
        self.beam_step = MockBeamConfigStep(self.experience_level)
        
        # Placeholder steps (would be fully implemented)
        self.resist_step = self.create_placeholder_step("Resist Configuration", 
            "Configure resist material properties and processing parameters.")
        self.simulation_step = self.create_placeholder_step("Simulation Settings",
            "Set up Monte Carlo simulation parameters and physics options.")
        self.summary_step = MockSummaryStep()
        
        # Add steps to stack
        for step in [self.welcome_step, self.beam_step, self.resist_step, 
                     self.simulation_step, self.summary_step]:
            self.content_stack.addWidget(step)
        
        # Navigation buttons
        nav_bar = self.create_navigation_bar()
        layout.addWidget(nav_bar)
    
    def create_placeholder_step(self, title: str, description: str) -> QWidget:
        """Create placeholder step for demo"""
        step = QWidget()
        layout = QVBoxLayout(step)
        layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 16px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 32px;
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        
        placeholder_label = QLabel("This step would contain the full configuration interface\nfor " + title.lower())
        placeholder_label.setStyleSheet("""
            background: #f3f4f6;
            border: 2px dashed #d1d5db;
            border-radius: 8px;
            padding: 60px;
            color: #9ca3af;
            font-size: 16px;
            text-align: center;
        """)
        placeholder_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(placeholder_label)
        layout.addStretch()
        
        return step
    
    def create_navigation_bar(self) -> QWidget:
        """Create navigation button bar"""
        nav_bar = QFrame()
        nav_bar.setFixedHeight(80)
        nav_bar.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border-top: 1px solid #e2e8f0;
                padding: 16px 32px;
            }
        """)
        
        layout = QHBoxLayout(nav_bar)
        
        # Previous button
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setEnabled(False)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 12px 24px;
                color: #374151;
                font-weight: 600;
            }
            QPushButton:hover:enabled {
                background: #e5e7eb;
            }
            QPushButton:disabled {
                background: #f9fafb;
                color: #9ca3af;
                border-color: #f3f4f6;
            }
        """)
        self.prev_button.clicked.connect(self.previous_step)
        
        # Progress info
        self.progress_label = QLabel(f"Step {self.current_step + 1} of {len(self.steps)}")
        self.progress_label.setStyleSheet("""
            color: #6b7280;
            font-size: 12px;
            font-weight: 500;
        """)
        
        # Next button
        self.next_button = QPushButton("Next →")
        self.next_button.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        self.next_button.clicked.connect(self.next_step)
        
        layout.addWidget(self.prev_button)
        layout.addWidget(self.progress_label)
        layout.addStretch()
        layout.addWidget(self.next_button)
        
        return nav_bar
    
    def next_step(self):
        """Go to next step"""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.update_step()
    
    def previous_step(self):
        """Go to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            self.update_step()
    
    def update_step(self):
        """Update the current step display"""
        # Update step indicator
        new_indicator = MockStepIndicator(self.steps, self.current_step)
        old_indicator = self.centralWidget().layout().itemAt(0).widget()
        self.centralWidget().layout().replaceWidget(old_indicator, new_indicator)
        old_indicator.deleteLater()
        self.step_indicator = new_indicator
        
        # Update content
        self.content_stack.setCurrentIndex(self.current_step)
        
        # Update navigation buttons
        self.prev_button.setEnabled(self.current_step > 0)
        
        if self.current_step == len(self.steps) - 1:
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Next →")
        
        # Update progress label
        self.progress_label.setText(f"Step {self.current_step + 1} of {len(self.steps)}")


def main():
    """Run wizard mockup"""
    app = QApplication(sys.argv)
    
    # High DPI support
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    
    # Set font for high DPI
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = ScientificWizardMockup()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()