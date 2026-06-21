from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_action,
    configure_binary_workbench_line_edit,
)
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
        for name, lba, _, _ in self._rows:
            if name.text().strip() and lba.text().strip():
                rows.append(BinaryWorkbenchInternalFileDTO(name=name.text().strip(), start_lba=int(lba.text().strip(), 0)))
        return rows

    def _append_from_entry(self) -> None:
        self._append_row(self.name.text(), self.lba.text())
        self.name.clear()
        self.lba.clear()

    def _clear_rows(self) -> None:
        for _, _, row, remove_slot in self._rows:
            row.deleteLater()
            remove_slot.deleteLater()
        self._rows.clear()

    def _append_row(self, name: str, lba: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_FIELD_SPACING)
        name_edit = lba_input(
            BINARY_WORKBENCH_TEXT.LBA_FILE_NAME,
            row,
            name,
            BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_NAME_WIDTH,
            expanding=True,
        )
        lba_edit = lba_input(
            BINARY_WORKBENCH_TEXT.LBA_START,
            row,
            lba,
            BINARY_WORKBENCH_LAYOUT.LBA_FILESYSTEM_START_WIDTH,
            expanding=True,
        )
        configure_binary_workbench_line_edit(name_edit)
        configure_binary_workbench_line_edit(lba_edit)
        set_python_identifier_validator(name_edit)
        set_decimal_integer_validator(lba_edit)
        go_to = lba_button(BINARY_WORKBENCH_TEXT.GO_TO, "", row)
        configure_binary_workbench_action(go_to)
        go_to.clicked.connect(lambda: self._go_to_lba(lba_edit.text()))
        remove_slot = _remove_slot(self.remove_body)
        remove = LbaRemoveRowButton(remove_slot)
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row, remove_slot))
        layout.addWidget(name_edit, 1)
        layout.addWidget(lba_edit, 1)
        layout.addWidget(go_to, 1, Qt.AlignVCenter)
        remove_slot.layout().addWidget(remove, 0, Qt.AlignCenter)
        self._rows.append((name_edit, lba_edit, row, remove_slot))
        self.body_layout.addWidget(row, 0)
        self.remove_layout.addWidget(remove_slot, 0)

    def _go_to_lba(self, lba: str) -> None:
        try:
            self.goToRequested.emit(int(lba.strip(), 0) * self.selected_lba_sector_size())
        except ValueError:
            return

    def _remove_row(self, row: QWidget, remove_slot: QWidget) -> None:
        self._rows = [item for item in self._rows if item[2] is not row]
        row.deleteLater()
        remove_slot.deleteLater()


def _remove_slot(parent: QWidget) -> QWidget:
    slot = QWidget(parent)
    slot.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(0, 0, 0, 0)
    return slot
