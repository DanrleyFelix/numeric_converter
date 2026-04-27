from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QVBoxLayout,
)
from src.presentation.ui.components.command_panel.command_edit import CommandEdit


class CommandPanel(QFrame):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 0, 0, 0)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        self.show_variables_button = QPushButton("Variables")
        self.show_variables_button.setObjectName("command-header-button")
        self.show_variables_button.setCursor(Qt.PointingHandCursor)
        self.show_variables_button.setFocusPolicy(Qt.NoFocus)

        self.show_logs_button = QPushButton("Logs")
        self.show_logs_button.setObjectName("command-header-button")
        self.show_logs_button.setCursor(Qt.PointingHandCursor)
        self.show_logs_button.setFocusPolicy(Qt.NoFocus)

        self.convert_toggle = QPushButton("Convert")
        self.convert_toggle.setObjectName("command-convert-toggle")
        self.convert_toggle.setCheckable(True)
        self.convert_toggle.setChecked(False)
        self.convert_toggle.setCursor(Qt.PointingHandCursor)
        self.convert_toggle.setFocusPolicy(Qt.NoFocus)

        header_row.addWidget(self.show_variables_button)
        header_row.addWidget(self.show_logs_button)
        header_row.addWidget(self.convert_toggle)
        header_row.addStretch(1)

        feedback_row = QHBoxLayout()
        feedback_row.setContentsMargins(0, 0, 0, 0)
        feedback_row.setSpacing(0)
        self.feedback = QLabel("Type an expression and press Enter.")
        self.feedback.setObjectName("command-feedback")
        feedback_row.addWidget(self.feedback, 1)

        self.editor = CommandEdit()
        self.editor.setObjectName("command-editor")
        self.editor.setMinimumHeight(180)
        layout.addLayout(header_row)
        layout.addLayout(feedback_row)
        layout.addWidget(self.editor, 1)

    def set_input_text(self, value: str) -> None:
        self.editor.setPlainText(value)
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.editor.setTextCursor(cursor)

    def current_input(self) -> str:
        return self.editor.toPlainText()

    def set_completions(self, values: list[str]) -> None:
        self.editor.set_completions(values)

    def convert_enabled(self) -> bool:
        return self.convert_toggle.isChecked()

    def set_feedback(self, message: str, color: str) -> None:
        self.feedback.setText(message)
        self.feedback.setStyleSheet(f"color: {color};")
