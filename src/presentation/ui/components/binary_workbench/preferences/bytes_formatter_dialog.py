from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_BYTES_FORMATTER_TEXT,
)


class BinaryWorkbenchBytesFormatterDialog(QDialog):
    def __init__(
        self,
        current_group_bytes: int,
        uppercase_bytes: bool = True,
        uppercase_instructions: bool = True,
        parent=None,
    ) -> None:
        if parent is None and not isinstance(uppercase_bytes, bool):
            parent = uppercase_bytes
            uppercase_bytes = True
        if parent is None and not isinstance(uppercase_instructions, bool):
            parent = uppercase_instructions
            uppercase_instructions = True
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.TITLE)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        label = QLabel(BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.GROUP_BYTES_LABEL, self)
        label.setObjectName("preferences-section-title")
        self.group_bytes = QComboBox(self)
        self.group_bytes.setCursor(Qt.PointingHandCursor)
        self.group_bytes.addItems(["1 byte", "2 bytes", "4 bytes"])
        current = current_group_bytes if current_group_bytes in {1, 2, 4} else 1
        self.group_bytes.setCurrentIndex({1: 0, 2: 1, 4: 2}[current])
        self.uppercase_bytes = QCheckBox(
            BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.UPPERCASE_BYTES_LABEL,
            self,
        )
        self.uppercase_bytes.setObjectName("binary-workbench-dialog-check")
        self.uppercase_bytes.setChecked(uppercase_bytes)
        self.uppercase_bytes.setCursor(Qt.PointingHandCursor)
        self.uppercase_instructions = QCheckBox(
            BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.UPPERCASE_INSTRUCTIONS_LABEL,
            self,
        )
        self.uppercase_instructions.setObjectName("binary-workbench-dialog-check")
        self.uppercase_instructions.setChecked(uppercase_instructions)
        self.uppercase_instructions.setCursor(Qt.PointingHandCursor)
        ok = QPushButton("OK", self)
        ok.setObjectName("preferences-ok")
        ok.setFocusPolicy(Qt.NoFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(label)
        layout.addWidget(self.group_bytes)
        layout.addWidget(self.uppercase_bytes)
        layout.addWidget(self.uppercase_instructions)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def selected_group_bytes(self) -> int:
        return (1, 2, 4)[self.group_bytes.currentIndex()]

    def selected_uppercase_bytes(self) -> bool:
        return self.uppercase_bytes.isChecked()

    def selected_uppercase_instructions(self) -> bool:
        return self.uppercase_instructions.isChecked()
