from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from src.modules.dtos import BinaryWorkbenchMemoryRegionDTO
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    LbaRemoveRowButton,
    lba_input,
)
from src.presentation.ui.components.workspace_table.constants.layout import (
    WORKSPACE_TABLE_SIZE,
)


class MemoryRegionsRowsMixin:
    def regions(self) -> list[BinaryWorkbenchMemoryRegionDTO]:
        values: list[BinaryWorkbenchMemoryRegionDTO] = []
        for name, start, end, _ in self._rows:
            if name.text().strip() and start.text().strip() and end.text().strip():
                values.append(
                    BinaryWorkbenchMemoryRegionDTO(
                        name=name.text().strip(),
                        start_offset=int(start.text().strip(), 0),
                        end_offset=int(end.text().strip(), 0),
                    )
                )
        return values

    def _append_from_entry(self) -> None:
        self._append_row(self.name.text(), self.start.text(), self.end.text())
        self.name.clear()
        self.start.clear()
        self.end.clear()

    def _append_row(self, name: str, start: str, end: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        edits = [
            lba_input(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_NAME_LABEL, row, name),
            lba_input(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_START_LABEL, row, start),
            lba_input(BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGION_END_LABEL, row, end),
        ]
        remove = LbaRemoveRowButton(row)
        remove.setFixedSize(
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH,
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT,
        )
        remove.clicked.connect(lambda: self._remove_row(row))
        for edit in edits:
            layout.addWidget(edit, 0)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        self._rows.append((edits[0], edits[1], edits[2], row))
        self.body_layout.addWidget(row, 0, Qt.AlignLeft)

    def _clear_rows(self) -> None:
        for _, _, _, row in self._rows:
            row.deleteLater()
        self._rows.clear()

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[3] is not row]
        row.deleteLater()
