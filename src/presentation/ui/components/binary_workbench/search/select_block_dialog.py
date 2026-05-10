from PySide6.QtWidgets import QDialog

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    finish_search_dialog,
    search_line_edit,
)


class BinaryWorkbenchSelectBlockDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SELECT_BLOCK)
        layout = base_search_dialog_layout(
            self,
            BINARY_WORKBENCH_TEXT.SELECT_BLOCK,
            BINARY_WORKBENCH_TEXT.SELECT_BLOCK_SUBTITLE,
        )
        self.start = search_line_edit(self, BINARY_WORKBENCH_TEXT.START_OFFSET)
        self.end = search_line_edit(self, BINARY_WORKBENCH_TEXT.END_OFFSET)
        self.length = search_line_edit(self, BINARY_WORKBENCH_TEXT.LENGTH_BYTES)
        finish_search_dialog(layout, self.start, self.end, self.length, self.accept)

    def selected_range(self) -> tuple[int, int] | None:
        try:
            if not self.start.text().strip():
                return None
            start = int(self.start.text().strip(), 0)
            if self.length.text().strip():
                return start, start + max(0, int(self.length.text().strip(), 0) - 1)
            return (start, int(self.end.text().strip(), 0)) if self.end.text().strip() else None
        except ValueError:
            return None
