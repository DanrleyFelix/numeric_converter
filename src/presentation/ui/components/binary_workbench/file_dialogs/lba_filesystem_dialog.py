from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class BinaryWorkbenchLbaFilesystemDialog(QDialog):
    def __init__(self, internal_files: list[BinaryWorkbenchInternalFileDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self.editor = QPlainTextEdit(self)
        self.editor.setPlainText(_serialize_internal_files(internal_files))
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        ok.setObjectName("preferences-ok")
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.editor)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def mappings(self) -> list[BinaryWorkbenchInternalFileDTO]:
        rows: list[BinaryWorkbenchInternalFileDTO] = []
        for line in self.editor.toPlainText().splitlines():
            if "=" not in line:
                continue
            name, raw_value = [chunk.strip() for chunk in line.split("=", 1)]
            if not name or not raw_value:
                continue
            rows.append(BinaryWorkbenchInternalFileDTO(name=name, start_lba=int(raw_value, 0)))
        return rows


def _serialize_internal_files(internal_files: list[BinaryWorkbenchInternalFileDTO]) -> str:
    return "\n".join(f"{item.name} = {item.start_lba}" for item in internal_files)
