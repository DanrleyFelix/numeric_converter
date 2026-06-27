from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QPushButton

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_FIND_DEFAULT_LENGTH_KB,
    BINARY_WORKBENCH_FIND_MAX_LENGTH_BYTES,
    BINARY_WORKBENCH_FIND_MAX_LENGTH_KB,
)
from src.modules.constants import HEX_DIGITS_LOWER
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_hex_bytes_validator,
    set_hex_value_validator,
)
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    configure_search_combo_popup,
    finish_search_dialog,
    search_line_edit,
)
from src.presentation.ui.components.binary_workbench.search.results_list import SearchResultsList


class BinaryWorkbenchFindDialog(QDialog):
    goToRequested = Signal(int)

    def __init__(
        self,
        search: Callable[[str, str, int | None, int | None, int | None], list[int]],
        last_search_end: Callable[[], int | None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._search = search
        self._last_search_end = last_search_end
        self._offsets: list[int] = []
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.FIND)
        self.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_DIALOG_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_DIALOG_HEIGHT,
        )
        layout = base_search_dialog_layout(
            self,
            BINARY_WORKBENCH_TEXT.FIND,
            BINARY_WORKBENCH_TEXT.FIND_SUBTITLE,
            include_header=False,
        )
        self.mode = QComboBox(self)
        self.mode.setObjectName("binary-workbench-dialog-input")
        configure_search_combo_popup(self.mode)
        self.mode.setCursor(Qt.PointingHandCursor)
        self.mode.addItems([
            BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY,
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES,
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES_BE,
            BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT,
        ])
        self.auto_fill_start = QCheckBox(BINARY_WORKBENCH_TEXT.FIND_AUTO_FILL_START_OFFSET, self)
        self.auto_fill_start.setCursor(Qt.PointingHandCursor)
        self.query = search_line_edit(self, BINARY_WORKBENCH_TEXT.VALUE)
        self.mode.currentTextChanged.connect(self._sync_query_validator)
        self.start = search_line_edit(self, BINARY_WORKBENCH_TEXT.START_OFFSET)
        self.end = search_line_edit(self, BINARY_WORKBENCH_TEXT.END_OFFSET)
        self.length = search_line_edit(self, BINARY_WORKBENCH_TEXT.FIND_LENGTH)
        set_hex_value_validator(self.start)
        set_hex_value_validator(self.end)
        set_decimal_integer_validator(self.length)
        self.results = SearchResultsList(self)
        layout.addWidget(self.auto_fill_start)
        layout.addSpacing(BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_AUTOFILL_TOP_SPACING)
        layout.addWidget(self.mode)
        layout.addWidget(self.query)
        layout.addWidget(self.start)
        layout.addWidget(self.end)
        layout.addWidget(self.length)
        layout.addWidget(self.results)
        search_button = QPushButton(BINARY_WORKBENCH_TEXT.FIND, self)
        search_button.clicked.connect(self.refresh_results)
        self.query.returnPressed.connect(self.refresh_results)
        self.start.returnPressed.connect(self.refresh_results)
        self.end.returnPressed.connect(self.refresh_results)
        self.length.returnPressed.connect(self.refresh_results)
        self.results.offsetActivated.connect(self.goToRequested)
        finish_search_dialog(
            layout,
            search_button,
            self.accept,
            spread_actions=True,
        )
        self._sync_query_validator(self.mode.currentText())

    def refresh_results(self) -> None:
        try:
            start_offset, end_offset = self._offset_range()
        except ValueError:
            self._offsets = []
        else:
            self._offsets = self._search(
                self.mode.currentText(),
                self.query.text().strip(),
                start_offset,
                end_offset,
                None,
            )
            self._fill_next_start_offset()
        self.results.clear()
        for offset in self._offsets:
            self.results.addItem(f"0x{offset:08X}")

    def selected_offset(self) -> int | None:
        if not self._offsets:
            self.refresh_results()
        row = self.results.currentRow()
        if 0 <= row < len(self._offsets):
            return self._offsets[row]
        return self._offsets[0] if self._offsets else None

    def _offset_range(self) -> tuple[int | None, int | None]:
        start = self.start.text().strip()
        end = self.end.text().strip()
        length = self.length.text().strip()
        start_offset = int(start, 16) if start else None
        end_offset = int(end, 16) if end else None
        raw_length_kb = int(length, 10) if length else BINARY_WORKBENCH_FIND_DEFAULT_LENGTH_KB
        length_kb = max(1, min(raw_length_kb, BINARY_WORKBENCH_FIND_MAX_LENGTH_KB))
        if length and raw_length_kb != length_kb:
            self.length.setText(str(length_kb))
        length_value = min(length_kb * 1024, BINARY_WORKBENCH_FIND_MAX_LENGTH_BYTES)
        if start_offset is not None and end_offset is not None:
            return start_offset, min(end_offset, start_offset + length_value - 1)
        if start_offset is not None:
            return start_offset, start_offset + length_value - 1
        if end_offset is not None:
            return max(0, end_offset - length_value + 1), end_offset
        return 0, length_value - 1

    def _fill_next_start_offset(self) -> None:
        if not self.auto_fill_start.isChecked():
            return
        if self._last_search_end is None:
            return
        end_offset = self._last_search_end()
        if end_offset is not None:
            self.start.setText(f"0x{end_offset:08X}")

    def _sync_query_validator(self, mode: str) -> None:
        if mode not in {
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES,
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES_BE,
        }:
            self.query.setValidator(None)
            return
        clean = "".join(character for character in self.query.text().lower() if character in HEX_DIGITS_LOWER)
        if clean != self.query.text():
            self.query.setText(clean)
        set_hex_bytes_validator(self.query)
