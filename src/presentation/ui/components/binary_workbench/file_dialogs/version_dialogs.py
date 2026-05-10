from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout

from src.modules.dtos import BinaryWorkbenchVersionDTO
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class BinaryWorkbenchVersionNameDialog(QDialog):
    def __init__(self, title: str, initial_value: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        title_label = QLabel(title, self)
        title_label.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self.name_field = QLineEdit(initial_value, self)
        self.name_field.setObjectName("binary-workbench-dialog-input")
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        ok.setObjectName("preferences-ok")
        ok.setFocusPolicy(Qt.NoFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        layout.addWidget(title_label)
        layout.addWidget(subtitle)
        layout.addWidget(self.name_field)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def version_name(self) -> str:
        return self.name_field.text().strip()


class BinaryWorkbenchVersionPickerDialog(QDialog):
    def __init__(self, versions: list[BinaryWorkbenchVersionDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_TITLE)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self.items = QListWidget(self)
        self.items.setObjectName("binary-workbench-search-results")
        for version in versions:
            self.items.addItem(version.name)
        if self.items.count():
            self.items.setCurrentRow(0)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        ok.setObjectName("preferences-ok")
        ok.setFocusPolicy(Qt.NoFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.items)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def selected_name(self) -> str | None:
        current = self.items.currentItem()
        return current.text() if current is not None else None
