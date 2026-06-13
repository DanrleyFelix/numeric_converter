from PySide6.QtWidgets import QDialog

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_hex_value_validator,
)
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
        self.setMaximumSize(
            BINARY_WORKBENCH_LAYOUT.SEARCH_DIALOG_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SEARCH_SELECT_BLOCK_DIALOG_MAX_HEIGHT,
        )
        layout = base_search_dialog_layout(
            self,
            BINARY_WORKBENCH_TEXT.SELECT_BLOCK,
            BINARY_WORKBENCH_TEXT.SELECT_BLOCK_SUBTITLE,
            include_header=False,
            spacing=BINARY_WORKBENCH_LAYOUT.SEARCH_SELECT_BLOCK_SPACING,
        )
        self.start = search_line_edit(self, BINARY_WORKBENCH_TEXT.START_OFFSET)
        self.end = search_line_edit(self, BINARY_WORKBENCH_TEXT.END_OFFSET)
        self.length = search_line_edit(self, BINARY_WORKBENCH_TEXT.LENGTH_BYTES)
        set_hex_value_validator(self.start)
        set_hex_value_validator(self.end)
        set_decimal_integer_validator(self.length)
        ok = finish_search_dialog(
            layout,
            self.start,
            self.end,
            self.length,
            self.accept,
            confirm_text=BINARY_WORKBENCH_TEXT.CONFIRM,
            confirm_object_name="preferences-confirm",
            center_confirm=True,
        )
        ok.setFixedWidth(BINARY_WORKBENCH_LAYOUT.SEARCH_FIELD_WIDTH)

    def selected_range(self) -> tuple[int, int] | None:
        try:
            if not self.start.text().strip():
                return None
            start = int(self.start.text().strip(), 16)
            if self.length.text().strip():
                return start, start + max(0, int(self.length.text().strip(), 10) - 1)
            return (start, int(self.end.text().strip(), 16)) if self.end.text().strip() else None
        except ValueError:
            return None
