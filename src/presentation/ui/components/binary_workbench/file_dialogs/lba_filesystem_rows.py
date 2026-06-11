from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    LbaRemoveRowButton,
    lba_button,
    lba_input,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_python_identifier_validator,
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
        name_edit = lba_input(
            BINARY_WORKBENCH_TEXT.LBA_FILE_NAME,
            row,
            name,
            BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_NAME_WIDTH,
        )
        lba_edit = lba_input(
            BINARY_WORKBENCH_TEXT.LBA_START,
            row,
            lba,
            BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_START_WIDTH,
        )
        set_python_identifier_validator(name_edit)
        set_decimal_integer_validator(lba_edit)
        go_to = lba_button(BINARY_WORKBENCH_TEXT.GO_TO, "binary-workbench-lba-action", row)
        go_to.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_ACTION_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT,
        )
        go_to.clicked.connect(lambda: self._go_to_lba(lba_edit.text()))
        remove = LbaRemoveRowButton(row)
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(name_edit, 0)
        layout.addWidget(lba_edit, 0)
        layout.addWidget(go_to, 0, Qt.AlignVCenter)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        self._rows.append((name_edit, lba_edit, row))
        self.body_layout.addWidget(row, 0, Qt.AlignLeft)

    def _go_to_lba(self, lba: str) -> None:
        try:
            self.goToRequested.emit(int(lba.strip(), 0) * self.selected_lba_sector_size())
        except ValueError:
            return

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[2] is not row]
        row.deleteLater()
