"""
Enhanced button with status awareness and working state visualization
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QTimer
from typing import Optional


class StatusButton(QPushButton):
    """Enhanced button with status awareness and working state visualization"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.default_text = text
        self.is_working = False
        self._working_timer = QTimer()
        self._working_dots = 0
        self._working_message = ""
        
        # Setup timer for animated working state
        self._working_timer.timeout.connect(self._update_working_animation)
        self._working_timer.setInterval(500)  # Update every 500ms

    def set_status(self, enabled: bool, tooltip_message: str = "") -> None:
        """Set button status with helpful tooltip"""
        self.setEnabled(enabled)
        if not enabled and tooltip_message:
            self.setToolTip(f"⚠️ {tooltip_message}")
        else:
            self.setToolTip("")

    def set_working(self, working: bool, message: str = "Processing") -> None:
        """Show working state with animated dots"""
        self.is_working = working
        if working:
            self._working_message = message
            self._working_dots = 0
            self.setEnabled(False)  
            self._working_timer.start()
            self._update_working_animation()
        else:
            self._working_timer.stop()
            self.setText(self.default_text)
            self.setEnabled(True)
            self.setToolTip("")

    def _update_working_animation(self) -> None:
        """Update the animated working state"""
        if self.is_working:
            dots = "." * (self._working_dots % 4)  # 0 to 3 dots
            self.setText(f"{self._working_message}{dots}")
            self._working_dots += 1

    def set_success_state(self, message: str = "Success!", duration_ms: int = 2000) -> None:
        """Temporarily show success state"""
        if not self.is_working:
            original_text = self.text()
            self.setText(f"✅ {message}")
            self.setStyleSheet("QPushButton { color: green; font-weight: bold; }")
            self.repaint()  # Force immediate visual update

            # Reset after duration
            QTimer.singleShot(duration_ms, lambda: self._reset_to_normal(original_text))

    def set_error_state(self, message: str = "Error!", duration_ms: int = 3000) -> None:
        """Temporarily show error state"""
        if not self.is_working:
            original_text = self.text()
            self.setText(f"❌ {message}")
            self.setStyleSheet("QPushButton { color: red; font-weight: bold; }")
            self.repaint()  # Force immediate visual update

            # Reset after duration
            QTimer.singleShot(duration_ms, lambda: self._reset_to_normal(original_text))

    def _reset_to_normal(self, original_text: str) -> None:
        """Reset button to normal appearance"""
        self.setText(original_text)
        self.setStyleSheet("")  # Clear custom styling
        self.repaint()  # Force immediate visual update