"""
Modern UI Components Library for EBL Simulation GUI
=================================================

Material Design 3 inspired components optimized for scientific applications.
"""

import sys
from pathlib import Path
from typing import Optional, Callable, List, Any, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QRadioButton, QSlider, QTextEdit, QScrollArea, QGroupBox,
    QTabWidget, QTableWidget, QTreeWidget, QListWidget, QSplitter
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QTimer,
    QParallelAnimationGroup, QSequentialAnimationGroup, Property
)
from PySide6.QtGui import (
    QFont, QPalette, QColor, QPixmap, QPainter, QLinearGradient,
    QRadialGradient, QPainterPath, QBrush, QPen, QIcon
)


class MaterialCard(QFrame):
    """Material Design card with elevation and hover effects"""
    
    clicked = Signal()
    
    def __init__(self, title: str = "", subtitle: str = "", elevation: int = 1, parent=None):
        super().__init__(parent)
        self.elevation = elevation
        self.hover_elevation = elevation + 2
        self.is_hovered = False
        
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)
        
        # Animation setup - use geometry instead of custom property
        self.shadow_animation = QPropertyAnimation(self, b"geometry")
        self.shadow_animation.setDuration(200)
        self.shadow_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.setup_ui(title, subtitle)
        self.apply_styling()
    
    def setup_ui(self, title: str, subtitle: str):
        """Setup the card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)  # Reduced margins
        layout.setSpacing(6)  # Reduced spacing
        
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("card_title")
            layout.addWidget(self.title_label)
        
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("card_subtitle")
            layout.addWidget(self.subtitle_label)
    
    def apply_styling(self):
        """Apply card styling"""
        self.setStyleSheet(f"""
            MaterialCard {{
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 16px;
                margin: 4px;
            }}
            MaterialCard:hover {{
                border-color: #6366f1;
                background-color: #1e293b;
            }}
            QLabel#card_title {{
                font-size: 14px;
                font-weight: 700;
                color: #f9fafb;
                margin-bottom: 3px;
            }}
            QLabel#card_subtitle {{
                font-size: 11px;
                font-weight: 400;
                color: #9ca3af;
                line-height: 1.4;
            }}
        """)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        self.is_hovered = True
        # Simple hover effect without animation for now
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self.is_hovered = False
        # Simple hover effect without animation for now
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ModernButton(QPushButton):
    """Modern button with Material Design styling and animations"""
    
    def __init__(self, text: str, variant: str = "primary", icon: Optional[QIcon] = None, parent=None):
        super().__init__(text, parent)
        
        self.variant = variant
        if icon:
            self.setIcon(icon)
        
        self.setMinimumHeight(36)  # Reduced from 44
        self.setMinimumWidth(100)   # Reduced from 120
        
        # Remove animations for now to fix errors
        # self.geometry_animation = QPropertyAnimation(self, b"geometry")
        # self.geometry_animation.setDuration(150)
        # self.geometry_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # self.original_geometry = None
        self.apply_variant_styling()
    
    def apply_variant_styling(self):
        """Apply styling based on variant"""
        base_style = """
            ModernButton {
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
                text-align: center;
            }
        """
        
        variant_styles = {
            "primary": """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: white;
            """,
            "secondary": """
                background: #374151;
                border: 1px solid #6b7280;
                color: #f9fafb;
            """,
            "success": """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
            """,
            "danger": """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white;
            """,
            "ghost": """
                background: transparent;
                border: 1px solid #6b7280;
                color: #d1d5db;
            """
        }
        
        hover_styles = {
            "primary": "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);",
            "secondary": "background: #4b5563; border-color: #9ca3af;",
            "success": "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);",
            "danger": "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #b91c1c);",
            "ghost": "background: rgba(107, 114, 128, 0.1); border-color: #9ca3af;"
        }
        
        style = base_style + variant_styles.get(self.variant, variant_styles["primary"])
        style += f"""
            ModernButton:hover {{
                {hover_styles.get(self.variant, hover_styles["primary"])}
            }}
            ModernButton:pressed {{
                transform: scale(0.98);
            }}
            ModernButton:disabled {{
                background: #374151;
                color: #6b7280;
                border-color: #4b5563;
            }}
        """
        
        self.setStyleSheet(style)


class ModernInput(QLineEdit):
    """Modern input field with floating label and validation states"""
    
    def __init__(self, placeholder: str = "", label: str = "", parent=None):
        super().__init__(parent)
        
        self.label_text = label
        self.is_focused = False
        self.has_content = False
        
        if placeholder:
            self.setPlaceholderText(placeholder)
        
        self.textChanged.connect(self._on_text_changed)
        self.apply_styling()
    
    def apply_styling(self):
        """Apply modern input styling"""
        self.setStyleSheet("""
            ModernInput {
                background: #374151;
                border: 2px solid #6b7280;
                border-radius: 8px;
                padding: 16px 16px;
                font-size: 14px;
                color: #f9fafb;
                min-height: 24px;
            }
            ModernInput:focus {
                border-color: #6366f1;
                background: #1f2937;
                outline: none;
            }
            ModernInput::placeholder {
                color: #9ca3af;
            }
        """)
    
    def _on_text_changed(self, text: str):
        """Handle text change"""
        self.has_content = bool(text.strip())
    
    def focusInEvent(self, event):
        """Handle focus in"""
        self.is_focused = True
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Handle focus out"""
        self.is_focused = False
        super().focusOutEvent(event)


class ModernSlider(QSlider):
    """Modern slider with enhanced styling"""
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setMinimumHeight(32) if orientation == Qt.Horizontal else self.setMinimumWidth(32)
        self.apply_styling()
    
    def apply_styling(self):
        """Apply modern slider styling"""
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #6b7280;
                height: 6px;
                background: #374151;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #6366f1;
                border: 2px solid #4f46e5;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #8b5cf6;
                border-color: #7c3aed;
            }
            QSlider::handle:horizontal:pressed {
                background: #4f46e5;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                border: 1px solid #4f46e5;
                height: 6px;
                border-radius: 3px;
            }
        """)


class ModernProgressBar(QProgressBar):
    """Modern progress bar with smooth animations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(8)
        self.setTextVisible(False)
        
        # Animation for smooth progress updates
        self.progress_animation = QPropertyAnimation(self, b"value")
        self.progress_animation.setDuration(300)
        self.progress_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.apply_styling()
    
    def apply_styling(self):
        """Apply modern progress bar styling"""
        self.setStyleSheet("""
            QProgressBar {
                background: #374151;
                border: none;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                border-radius: 4px;
            }
        """)
    
    def setValueAnimated(self, value: int):
        """Set value with animation"""
        self.progress_animation.setStartValue(self.value())
        self.progress_animation.setEndValue(value)
        self.progress_animation.start()


class ModernTabWidget(QTabWidget):
    """Modern tab widget with enhanced styling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.apply_styling()
    
    def apply_styling(self):
        """Apply modern tab styling"""
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
                top: -1px;
            }
            QTabWidget::tab-bar {
                left: 0;
            }
            QTabBar::tab {
                background: #374151;
                color: #9ca3af;
                padding: 16px 32px;
                margin-right: 4px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                min-width: 120px;
                font-weight: 500;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: #6366f1;
                color: white;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #4b5563;
                color: #d1d5db;
            }
        """)


class ModernStatusIndicator(QWidget):
    """Modern status indicator with color coding"""
    
    def __init__(self, label: str, status: str, color: str = "#10b981", parent=None):
        super().__init__(parent)
        self.status_color = color
        self.setup_ui(label, status)
    
    def setup_ui(self, label: str, status: str):
        """Setup the indicator UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Status dot
        dot = QLabel("●")
        dot.setStyleSheet(f"""
            QLabel {{
                color: {self.status_color};
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        
        # Labels
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        
        status_widget = QLabel(status)
        status_widget.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.status_color};
        """)
        
        layout.addWidget(dot)
        layout.addWidget(label_widget)
        layout.addWidget(status_widget)
        layout.addStretch()
        
        # Background styling
        self.setStyleSheet("""
            ModernStatusIndicator {
                background: #1f2937;
                border: 1px solid #374151;
                border-radius: 8px;
            }
        """)


class ModernMetricCard(MaterialCard):
    """Card specifically for displaying metrics"""
    
    def __init__(self, title: str, value: str, unit: str = "", trend: Optional[str] = None, parent=None):
        super().__init__(parent=parent)
        self.setup_metric_ui(title, value, unit, trend)
    
    def setup_metric_ui(self, title: str, value: str, unit: str, trend: Optional[str]):
        """Setup metric display"""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        
        # Value container
        value_container = QHBoxLayout()
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #f9fafb;
            line-height: 1;
        """)
        
        if unit:
            unit_label = QLabel(unit)
            unit_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 500;
                color: #6b7280;
                margin-left: 4px;
            """)
            value_container.addWidget(value_label)
            value_container.addWidget(unit_label)
            value_container.addStretch()
        else:
            value_container.addWidget(value_label)
            value_container.addStretch()
        
        # Trend indicator
        if trend:
            trend_label = QLabel(trend)
            trend_color = "#10b981" if trend.startswith("+") else "#ef4444" if trend.startswith("-") else "#6b7280"
            trend_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: 600;
                color: {trend_color};
            """)
            layout.addWidget(trend_label)
        
        layout.addWidget(title_label)
        
        value_widget = QWidget()
        value_widget.setLayout(value_container)
        layout.addWidget(value_widget)
        
        # Add to main card layout
        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.layout().addWidget(main_widget)


# Factory functions for easy component creation
def create_primary_button(text: str, callback: Callable = None) -> ModernButton:
    """Create a primary button"""
    btn = ModernButton(text, "primary")
    if callback:
        btn.clicked.connect(callback)
    return btn


def create_card_grid(cards: List[MaterialCard], columns: int = 3) -> QWidget:
    """Create a responsive grid of cards"""
    container = QWidget()
    layout = QGridLayout(container)
    layout.setSpacing(16)
    
    for i, card in enumerate(cards):
        row = i // columns
        col = i % columns
        layout.addWidget(card, row, col)
    
    return container


def create_metric_dashboard(metrics: List[Dict[str, Any]]) -> QWidget:
    """Create a metrics dashboard"""
    container = QWidget()
    layout = QGridLayout(container)
    layout.setSpacing(16)
    
    for i, metric in enumerate(metrics):
        card = ModernMetricCard(
            title=metric.get("title", ""),
            value=metric.get("value", "0"),
            unit=metric.get("unit", ""),
            trend=metric.get("trend")
        )
        
        row = i // 4
        col = i % 4
        layout.addWidget(card, row, col)
    
    return container