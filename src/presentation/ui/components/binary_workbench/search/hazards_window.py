from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton

from src.core.binary_workbench.hazard_cache import HazardCacheItem
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_HAZARDS_DEFAULT_LENGTH_KB,
    BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_BYTES,
    BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_KB,
)
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_hex_value_validator,
)
from src.presentation.ui.components.binary_workbench.search.dialog_layout import (
    base_search_dialog_layout,
    search_line_edit,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET


class BinaryWorkbenchHazardsWindow(QDialog):
    goToRequested = Signal(int)

    def __init__(
        self,
        cached_hazards: Callable[[int | None, int | None], list[HazardCacheItem]],
        find_hazards: Callable[[int | None, int | None], list[HazardCacheItem]],
        last_search_end: Callable[[], int | None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self._cached_hazards = cached_hazards
        self._find_hazards = find_hazards
        self._last_search_end = last_search_end
        self.setObjectName("preferences-dialog")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.HAZARDS)
        self.setStyleSheet(STYLESHEET)
        self.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_DIALOG_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_DIALOG_HEIGHT,
        )
        layout = base_search_dialog_layout(
            self,
            BINARY_WORKBENCH_TEXT.HAZARDS,
            "",
            include_header=False,
        )
        self.auto_fill_start = QCheckBox(BINARY_WORKBENCH_TEXT.FIND_AUTO_FILL_START_OFFSET, self)
        self.auto_fill_start.setCursor(Qt.PointingHandCursor)
        self.start = search_line_edit(self, BINARY_WORKBENCH_TEXT.START_OFFSET)
        self.end = search_line_edit(self, BINARY_WORKBENCH_TEXT.END_OFFSET)
        self.length = search_line_edit(self, BINARY_WORKBENCH_TEXT.FIND_LENGTH)
        set_hex_value_validator(self.start)
        set_hex_value_validator(self.end)
        set_decimal_integer_validator(self.length)
        self.results = QListWidget(self)
        self.results.setObjectName("binary-workbench-search-results")
        self.results.setFocusPolicy(Qt.NoFocus)
        self.results.setMouseTracking(True)
        self.results.viewport().setMouseTracking(True)
        self.results.setCursor(Qt.PointingHandCursor)
        self.results.itemClicked.connect(self._navigate_to_item)
        layout.addWidget(self.auto_fill_start)
        layout.addSpacing(BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_AUTOFILL_TOP_SPACING)
        layout.addWidget(self.start)
        layout.addWidget(self.end)
        layout.addWidget(self.length)
        layout.addWidget(self.results)
        self.cancel_button = QPushButton(BINARY_WORKBENCH_TEXT.CANCEL, self)
        configure_binary_workbench_dialog_action(self.cancel_button)
        self.cancel_button.clicked.connect(self.close)
        self.find_button = QPushButton(BINARY_WORKBENCH_TEXT.FIND_HAZARDS, self)
        configure_binary_workbench_dialog_action(self.find_button)
        self.find_button.clicked.connect(self.refresh_results)
        self.start.returnPressed.connect(self.refresh_results)
        self.end.returnPressed.connect(self.refresh_results)
        self.length.returnPressed.connect(self.refresh_results)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.find_button, 0, Qt.AlignLeft)
        row.addStretch(1)
        row.addWidget(self.cancel_button, 0, Qt.AlignRight)
        layout.addLayout(row)
        self.refresh_cached_results()

    def refresh_cached_results(self) -> None:
        try:
            start_offset, end_offset = self._offset_range()
        except ValueError:
            self._set_results([])
            return
        self._set_results(self._cached_hazards(start_offset, end_offset))

    def refresh_results(self) -> None:
        try:
            start_offset, end_offset = self._offset_range()
        except ValueError:
            self._set_results([])
            return
        self._set_results(self._find_hazards(start_offset, end_offset))
        self._fill_next_start_offset()

    def _offset_range(self) -> tuple[int | None, int | None]:
        start = self.start.text().strip()
        end = self.end.text().strip()
        length = self.length.text().strip()
        start_offset = int(start, 16) if start else None
        end_offset = int(end, 16) if end else None
        raw_length_kb = int(length, 10) if length else BINARY_WORKBENCH_HAZARDS_DEFAULT_LENGTH_KB
        length_kb = max(1, min(raw_length_kb, BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_KB))
        if length and raw_length_kb != length_kb:
            self.length.setText(str(length_kb))
        length_value = min(length_kb * 1024, BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_BYTES)
        if start_offset is not None and end_offset is not None:
            return start_offset, min(end_offset, start_offset + length_value - 1)
        if start_offset is not None:
            return start_offset, start_offset + length_value - 1
        if end_offset is not None:
            return max(0, end_offset - length_value + 1), end_offset
        return 0, length_value - 1

    def _fill_next_start_offset(self) -> None:
        if not self.auto_fill_start.isChecked() or self._last_search_end is None:
            return
        end_offset = self._last_search_end()
        if end_offset is not None:
            self.start.setText(f"0x{end_offset:08X}")

    def _set_results(self, items: list[HazardCacheItem]) -> None:
        self.results.clear()
        for item in items:
            row = QListWidgetItem(f"0x{item.offset:08X}    {item.instruction}")
            row.setData(Qt.ItemDataRole.UserRole, item.offset)
            self.results.addItem(row)

    def _navigate_to_item(self, item: QListWidgetItem) -> None:
        offset = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(offset, int):
            self.goToRequested.emit(offset)