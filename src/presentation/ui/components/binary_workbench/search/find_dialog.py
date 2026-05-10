from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QListWidget, QPushButton

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    finish_search_dialog,
    search_line_edit,
)


class BinaryWorkbenchFindDialog(QDialog):
    def __init__(self, search: Callable[[str, str], list[int]], parent=None) -> None:
        super().__init__(parent)
        self._search = search
        self._offsets: list[int] = []
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.FIND)
        layout = base_search_dialog_layout(self, BINARY_WORKBENCH_TEXT.FIND, BINARY_WORKBENCH_TEXT.FIND_SUBTITLE)
        self.mode = QComboBox(self)
        self.mode.setObjectName("binary-workbench-dialog-input")
        self.mode.setCursor(Qt.PointingHandCursor)
        self.mode.addItems([
            BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY,
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES,
            BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT,
        ])
        self.query = search_line_edit(self, BINARY_WORKBENCH_TEXT.VALUE)
        self.results = QListWidget(self)
        self.results.setObjectName("binary-workbench-search-results")
        layout.addWidget(self.mode)
        layout.addWidget(self.query)
        layout.addWidget(self.results)
        search_button = QPushButton(BINARY_WORKBENCH_TEXT.FIND, self)
        search_button.setObjectName("preferences-cancel")
        search_button.setFocusPolicy(Qt.NoFocus)
        search_button.setCursor(Qt.PointingHandCursor)
        search_button.clicked.connect(self.refresh_results)
        self.query.returnPressed.connect(self.refresh_results)
        self.results.itemDoubleClicked.connect(lambda _: self.accept())
        finish_search_dialog(layout, search_button, self.accept)

    def refresh_results(self) -> None:
        self._offsets = self._search(self.mode.currentText(), self.query.text().strip())
        self.results.clear()
        for offset in self._offsets:
            self.results.addItem(f"0x{offset:08X}")

    def selected_offset(self) -> int | None:
        if not self._offsets:
            self.refresh_results()
        if self.results.currentRow() >= 0:
            return self._offsets[self.results.currentRow()]
        return self._offsets[0] if self._offsets else None
