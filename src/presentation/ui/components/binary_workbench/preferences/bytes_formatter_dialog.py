from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_BYTE_GROUP_OPTIONS
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_combo,
    configure_binary_workbench_control_height,
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT,
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
        layout.setContentsMargins(
            *(BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.MARGIN,) * 4
        )
        layout.setSpacing(BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.LAYOUT_SPACING)
        group_bytes_label = QLabel(BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.GROUP_BYTES_LABEL, self)
        group_bytes_label.setObjectName("preferences-section-title")
        self.group_bytes = QComboBox(self)
        self.group_bytes.setObjectName("advanced-config-dropdown")
        self.group_bytes.setCursor(Qt.PointingHandCursor)
        configure_binary_workbench_combo(
            self.group_bytes,
            BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.CONTROL_WIDTH,
        )
        self.group_bytes.addItems(
            [
                f"{value} byte" if value == 1 else f"{value} bytes"
                for value in BINARY_WORKBENCH_BYTE_GROUP_OPTIONS
            ]
        )
        current = (
            current_group_bytes
            if current_group_bytes in BINARY_WORKBENCH_BYTE_GROUP_OPTIONS
            else BINARY_WORKBENCH_BYTE_GROUP_OPTIONS[0]
        )
        self.group_bytes.setCurrentIndex(BINARY_WORKBENCH_BYTE_GROUP_OPTIONS.index(current))
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
        configure_binary_workbench_control_height(self.uppercase_bytes)
        configure_binary_workbench_control_height(self.uppercase_instructions)
        ok = QPushButton(BINARY_WORKBENCH_BYTES_FORMATTER_TEXT.CONFIRM, self)
        configure_binary_workbench_dialog_action(ok)
        ok.clicked.connect(self.accept)
        layout.addWidget(group_bytes_label)
        layout.addSpacing(BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.FIELD_SPACING)
        layout.addWidget(self.group_bytes)
        layout.addSpacing(BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.FIELD_SPACING)
        layout.addWidget(self.uppercase_bytes)
        layout.addSpacing(
            BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.IDENTICAL_ITEM_SPACING
        )
        layout.addWidget(self.uppercase_instructions)
        layout.addSpacing(BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT.CONFIRM_TOP_SPACING)
        layout.addWidget(ok, 0, Qt.AlignCenter)
        self.setFixedSize(self.sizeHint())

    def selected_group_bytes(self) -> int:
        return BINARY_WORKBENCH_BYTE_GROUP_OPTIONS[self.group_bytes.currentIndex()]

    def selected_uppercase_bytes(self) -> bool:
        return self.uppercase_bytes.isChecked()

    def selected_uppercase_instructions(self) -> bool:
        return self.uppercase_instructions.isChecked()
