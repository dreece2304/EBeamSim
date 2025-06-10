"""
Output log widget
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QCheckBox, QLabel, QFileDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from datetime import datetime

class OutputWidget(QWidget):
    """Widget for displaying simulation output"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.message_count = 0
        self.max_lines = 10000
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Control bar
        control_layout = QHBoxLayout()
        
        self.timestamp_check = QCheckBox("Show Timestamps")
        self.timestamp_check.setChecked(True)
        control_layout.addWidget(self.timestamp_check)
        
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        control_layout.addWidget(self.autoscroll_check)
        
        self.wrap_check = QCheckBox("Word Wrap")
        self.wrap_check.setChecked(False)
        self.wrap_check.toggled.connect(self.toggle_word_wrap)
        control_layout.addWidget(self.wrap_check)
        
        control_layout.addStretch()
        
        self.line_count_label = QLabel("Lines: 0")
        control_layout.addWidget(self.line_count_label)
        
        # Buttons
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_output)
        control_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("Save Log")
        self.save_btn.clicked.connect(self.save_log)
        control_layout.addWidget(self.save_btn)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #555555;
            }
        """)
        
        # Add to layout
        layout.addLayout(control_layout)
        layout.addWidget(self.output_text)
        
        self.setLayout(layout)
        
        # Update timer for line count
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_line_count)
        self.update_timer.start(1000)
    
    def append_output(self, message: str, message_type: str = "info"):
        """Append message to output"""
        # Add timestamp if enabled
        if self.timestamp_check.isChecked():
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            formatted_message = f"[{timestamp}] {message}"
        else:
            formatted_message = message
        
        # Move cursor to end
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Apply formatting based on message type
        format = QTextCharFormat()
        
        if message_type == "error" or "ERROR" in message:
            format.setForeground(QColor("#f44336"))  # Red
        elif message_type == "warning" or "WARNING" in message:
            format.setForeground(QColor("#ff9800"))  # Orange
        elif message_type == "success" or "SUCCESS" in message:
            format.setForeground(QColor("#4caf50"))  # Green
        elif "Processing event" in message:
            format.setForeground(QColor("#2196f3"))  # Blue
        else:
            format.setForeground(QColor("#d4d4d4"))  # Default gray
        
        # Insert formatted text
        cursor.insertText(formatted_message + "\n", format)
        
        # Limit number of lines
        self.message_count += 1
        if self.message_count > self.max_lines:
            # Remove first line
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.message_count = self.max_lines
        
        # Auto-scroll if enabled
        if self.autoscroll_check.isChecked():
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_output(self):
        """Clear the output text"""
        reply = QMessageBox.question(
            self, "Clear Output",
            "Are you sure you want to clear the output log?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.output_text.clear()
            self.message_count = 0
            self.update_line_count()
    
    def save_log(self):
        """Save log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File",
            f"ebl_sim_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text files (*.txt);;All files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.output_text.toPlainText())
                
                QMessageBox.information(
                    self, "Success",
                    f"Log saved to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to save log:\n{str(e)}"
                )
    
    def toggle_word_wrap(self, checked):
        """Toggle word wrap in output"""
        if checked:
            self.output_text.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.output_text.setLineWrapMode(QTextEdit.NoWrap)
    
    def update_line_count(self):
        """Update line count label"""
        self.line_count_label.setText(f"Lines: {self.message_count:,}")
    
    def add_separator(self):
        """Add a separator line"""
        self.append_output("=" * 80, "info")
    
    def add_header(self, text: str):
        """Add a header line"""
        self.add_separator()
        self.append_output(text.center(80), "info")
        self.add_separator()