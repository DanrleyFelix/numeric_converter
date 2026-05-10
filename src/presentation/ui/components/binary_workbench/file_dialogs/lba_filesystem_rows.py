from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    LbaRemoveRowButton,
    lba_input,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class LbaFilesystemRowsMixin:
    def mappings(self) -> list[BinaryWorkbenchInternalFileDTO]:
        rows: list[BinaryWorkbenchInternalFileDTO] = []
        for name, lba, _ in self._rows:
            if name.text().strip() and lba.text().strip():
                rows.append(BinaryWorkbenchInternalFileDTO(name=name.text().strip(), start_lba=int(lba.text().strip(), 0)))
        return rows

    def _append_from_entry(self) -> None:
        self._append_row(self.name.text(), self.lba.text())
        self.name.clear()
        self.lba.clear()

    def _clear_rows(self) -> None:
        for _, _, row in self._rows:
            row.deleteLater()
        self._rows.clear()

    def _append_row(self, name: str, lba: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        name_edit = lba_input(BINARY_WORKBENCH_TEXT.LBA_FILE_NAME, row, name)
        lba_edit = lba_input(BINARY_WORKBENCH_TEXT.LBA_START, row, lba)
        remove = LbaRemoveRowButton(row)
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(name_edit, 0)
        layout.addWidget(lba_edit, 0)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        self._rows.append((name_edit, lba_edit, row))
        self.body_layout.addWidget(row, 0, Qt.AlignLeft)

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[2] is not row]
        row.deleteLater()
