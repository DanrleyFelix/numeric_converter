from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QListWidget, QPushButton

from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    finish_search_dialog,
    search_line_edit,
)
from src.presentation.ui.components.binary_workbench.search.go_to_offsets import (
    resolve_go_to_offsets,
)


class BinaryWorkbenchGoToDialog(QDialog):
    def __init__(self, context: BinaryWorkbenchTabContextDTO, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.GO_TO)
        layout = base_search_dialog_layout(self, BINARY_WORKBENCH_TEXT.GO_TO, BINARY_WORKBENCH_TEXT.GO_TO_SUBTITLE)
        self.target = QComboBox(self)
        self.target.setObjectName("binary-workbench-dialog-input")
        self.target.setCursor(Qt.PointingHandCursor)
        extra_offsets = [name for name in context.reference_offsets if name != "File"]
        self.target.addItems([
            BINARY_WORKBENCH_TEXT.FILE_OFFSET_TARGET,
            *extra_offsets,
            BINARY_WORKBENCH_TEXT.LBA_2048_TARGET,
            BINARY_WORKBENCH_TEXT.LBA_2334_TARGET,
            BINARY_WORKBENCH_TEXT.LBA_2352_TARGET,
            BINARY_WORKBENCH_TEXT.LABEL_TARGET,
            BINARY_WORKBENCH_TEXT.EQUATE_TARGET,
            BINARY_WORKBENCH_TEXT.VARIABLE_TARGET,
            BINARY_WORKBENCH_TEXT.INTERNAL_FILE_TARGET,
        ])
        self.value = search_line_edit(self, BINARY_WORKBENCH_TEXT.VALUE)
        self.results = QListWidget(self)
        self.results.setObjectName("binary-workbench-search-results")
        resolve = QPushButton(BINARY_WORKBENCH_TEXT.GO_TO, self)
        resolve.setObjectName("preferences-cancel")
        resolve.setFocusPolicy(Qt.NoFocus)
        resolve.setCursor(Qt.PointingHandCursor)
        resolve.clicked.connect(self.refresh_results)
        layout.addWidget(self.target)
        layout.addWidget(self.value)
        layout.addWidget(self.results)
        self.value.returnPressed.connect(self.refresh_results)
        self.results.itemDoubleClicked.connect(lambda _: self.accept())
        finish_search_dialog(layout, resolve, self.accept)

    def selected_offsets(self) -> list[int]:
        if self.results.currentRow() >= 0:
            return [int(self.results.currentItem().text(), 0)]
        if self.results.count() > 0:
            return [int(self.results.item(index).text(), 0) for index in range(self.results.count())]
        return self._resolve_offsets()

    def refresh_results(self) -> None:
        self.results.clear()
        for offset in self._resolve_offsets():
            self.results.addItem(f"0x{offset:08X}")

    def _resolve_offsets(self) -> list[int]:
        return resolve_go_to_offsets(
            self._context,
            self.target.currentText(),
            self.value.text().strip(),
        )
