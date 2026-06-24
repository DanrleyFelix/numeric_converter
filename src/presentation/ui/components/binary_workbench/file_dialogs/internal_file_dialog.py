from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class BinaryWorkbenchInternalFileDialog(QDialog):
    def __init__(self, internal_files: list[BinaryWorkbenchInternalFileDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.INTERNAL_TITLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.DIALOG_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.SECTION_SPACING)
        self.items = QListWidget(self)
        self.items.setObjectName("binary-workbench-search-results")
        for item in internal_files:
            self.items.addItem(item.name)
        if self.items.count():
            self.items.setCurrentRow(0)
        self.items.itemDoubleClicked.connect(lambda _item: self.accept())
        footer = QWidget(self)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        cancel = QPushButton(BINARY_WORKBENCH_TEXT.CANCEL, footer)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        for button in (cancel, ok):
            configure_binary_workbench_dialog_action(button)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        ok.setEnabled(self.items.count() > 0)
        footer_layout.addWidget(cancel, 0, Qt.AlignLeft)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok, 0, Qt.AlignRight)
        layout.addWidget(self.items)
        layout.addWidget(footer)

    def selected_name(self) -> str | None:
        current = self.items.currentItem()
        return current.text() if current is not None else None
