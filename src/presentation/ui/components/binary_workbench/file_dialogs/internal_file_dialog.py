from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QPushButton, QVBoxLayout

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class BinaryWorkbenchInternalFileDialog(QDialog):
    def __init__(self, internal_files: list[BinaryWorkbenchInternalFileDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.INTERNAL_TITLE)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.INTERNAL_TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.INTERNAL_SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self.items = QListWidget(self)
        for item in internal_files:
            self.items.addItem(item.name)
        if self.items.count():
            self.items.setCurrentRow(0)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        ok.setObjectName("preferences-ok")
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.items)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def selected_name(self) -> str | None:
        current = self.items.currentItem()
        return current.text() if current is not None else None
