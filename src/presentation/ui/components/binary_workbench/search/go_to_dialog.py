from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QDialog, QPushButton

from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_hex_value_validator,
    set_python_identifier_validator,
)
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    configure_search_combo_popup,
    finish_search_dialog,
    search_line_edit,
)
from src.presentation.ui.components.binary_workbench.search.go_to_offsets import (
    resolve_go_to_offsets,
)
from src.presentation.ui.components.binary_workbench.search.results_list import SearchResultsList


class BinaryWorkbenchGoToDialog(QDialog):
    goToRequested = Signal(int)

    def __init__(self, context: BinaryWorkbenchTabContextDTO, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.GO_TO)
        self.setMaximumSize(
            BINARY_WORKBENCH_LAYOUT.SEARCH_DIALOG_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SEARCH_GO_TO_DIALOG_MAX_HEIGHT,
        )
        layout = base_search_dialog_layout(
            self,
            BINARY_WORKBENCH_TEXT.GO_TO,
            BINARY_WORKBENCH_TEXT.GO_TO_SUBTITLE,
            include_header=False,
        )
        self.target = QComboBox(self)
        self.target.setObjectName("binary-workbench-dialog-input")
        configure_search_combo_popup(self.target)
        self.target.setCursor(Qt.PointingHandCursor)
        extra_offsets = [
            name
            for name in context.reference_offset_bases
            if name != "File"
        ]
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
        self.results = SearchResultsList(self)
        resolve = QPushButton(BINARY_WORKBENCH_TEXT.GO_TO, self)
        resolve.setObjectName("preferences-cancel")
        resolve.setFocusPolicy(Qt.NoFocus)
        resolve.setCursor(Qt.PointingHandCursor)
        resolve.clicked.connect(self.refresh_results)
        layout.addWidget(self.target)
        layout.addWidget(self.value)
        layout.addWidget(self.results)
        self.target.currentTextChanged.connect(self._sync_value_validator)
        self.value.returnPressed.connect(self.refresh_results)
        self.results.offsetActivated.connect(self.goToRequested)
        finish_search_dialog(
            layout,
            resolve,
            self.accept,
            button_width=BINARY_WORKBENCH_LAYOUT.SEARCH_BUTTON_WIDTH,
            spread_actions=True,
        )
        self._sync_value_validator(self.target.currentText())

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

    def _sync_value_validator(self, target: str) -> None:
        if target == BINARY_WORKBENCH_TEXT.FILE_OFFSET_TARGET or target in self._context.reference_offset_bases:
            self._keep_value_characters("0123456789abcdefABCDEF")
            set_hex_value_validator(self.value)
            return
        if target in {
            BINARY_WORKBENCH_TEXT.LBA_2048_TARGET,
            BINARY_WORKBENCH_TEXT.LBA_2334_TARGET,
            BINARY_WORKBENCH_TEXT.LBA_2352_TARGET,
        }:
            self._keep_value_characters("0123456789")
            set_decimal_integer_validator(self.value)
            return
        self._keep_python_identifier()
        set_python_identifier_validator(self.value)

    def _keep_value_characters(self, allowed: str) -> None:
        value = "".join(character for character in self.value.text() if character in allowed)
        if value != self.value.text():
            self.value.setText(value)

    def _keep_python_identifier(self) -> None:
        value = "".join(
            character
            for character in self.value.text()
            if character == "_" or character.isascii() and character.isalnum()
        )
        while value and value[0].isdigit():
            value = value[1:]
        if value != self.value.text():
            self.value.setText(value)
