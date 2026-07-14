from PySide6.QtWidgets import QDialog, QPlainTextEdit, QPushButton

from src.core.binary_workbench.byte_replacement import (
    ReplaceBytesRequest,
    parse_replace_bytes_request,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.dialog_context_menu import (
    configure_dialog_text_context_menu,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_hex_offset_validator,
    set_integer_or_hex_validator,
)
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    finish_search_dialog,
    search_line_edit,
)


class BinaryWorkbenchReplaceBytesDialog(QDialog):
    def __init__(self, parent=None, start_offset: int | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.REPLACE_BYTES)
        self.setMaximumSize(
            BINARY_WORKBENCH_LAYOUT.SEARCH_DIALOG_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SEARCH_REPLACE_BYTES_DIALOG_MAX_HEIGHT,
        )
        layout = base_search_dialog_layout(
            self,
            BINARY_WORKBENCH_TEXT.REPLACE_BYTES,
            BINARY_WORKBENCH_TEXT.REPLACE_BYTES_SUBTITLE,
            include_header=False,
            spacing=BINARY_WORKBENCH_LAYOUT.SEARCH_SELECT_BLOCK_SPACING,
        )
        self.start = search_line_edit(self, BINARY_WORKBENCH_TEXT.START_OFFSET)
        self.end = search_line_edit(self, BINARY_WORKBENCH_TEXT.END_OFFSET)
        self.length = search_line_edit(self, BINARY_WORKBENCH_TEXT.LENGTH_BYTES)
        self.bytes_input = QPlainTextEdit(self)
        self.bytes_input.setObjectName("binary-workbench-dialog-input")
        self.bytes_input.setPlaceholderText(BINARY_WORKBENCH_TEXT.REPLACEMENT_BYTES)
        self.bytes_input.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.bytes_input.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SEARCH_REPLACE_BYTES_INPUT_HEIGHT)
        configure_dialog_text_context_menu(self.bytes_input)
        set_hex_offset_validator(self.start)
        set_hex_offset_validator(self.end)
        set_integer_or_hex_validator(self.length)
        if start_offset is not None:
            self.start.setText(f"0x{max(0, start_offset):08X}")
        finish_search_dialog(
            layout,
            self.start,
            self.end,
            self.length,
            self.bytes_input,
            self.accept,
            confirm_text=BINARY_WORKBENCH_TEXT.CONFIRM,
            center_confirm=True,
        )

    def replacement_request(self) -> ReplaceBytesRequest | None:
        """Return validated replacement data from the dialog inputs."""

        return parse_replace_bytes_request(
            self.start.text(),
            self.end.text(),
            self.length.text(),
            self.bytes_input.toPlainText(),
        )


def confirm_nonzero_byte_replacement(parent=None) -> bool:
    """Ask for styled confirmation before overwriting non-zero bytes."""

    dialog = QDialog(parent)
    dialog.setObjectName("preferences-dialog")
    dialog.setWindowTitle(BINARY_WORKBENCH_TEXT.REPLACE_BYTES)
    layout = base_search_dialog_layout(
        dialog,
        BINARY_WORKBENCH_TEXT.REPLACE_BYTES,
        BINARY_WORKBENCH_TEXT.REPLACE_BYTES_CONFIRM_SUBTITLE,
    )
    cancel = QPushButton(BINARY_WORKBENCH_TEXT.CANCEL, dialog)
    cancel.clicked.connect(dialog.reject)
    finish_search_dialog(
        layout,
        cancel,
        dialog.accept,
        confirm_text=BINARY_WORKBENCH_TEXT.CONFIRM,
        spread_actions=True,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted
