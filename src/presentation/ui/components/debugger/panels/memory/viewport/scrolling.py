"""Lazy scrolling across complete debugger memory ranges."""

from PySide6.QtCore import QTimer

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT


class DebuggerMemoryScrollingMixin:
    """Render only the small memory window currently visible in the table."""

    def _setup_memory_scrolling(self) -> None:
        """Bind coalesced viewport rendering to the table scrollbar."""

        self._rendered_rows: tuple[int, ...] = ()
        self._memory_scroll_timer = QTimer(self)
        self._memory_scroll_timer.setSingleShot(True)
        self._memory_scroll_timer.timeout.connect(self._refresh_memory_scroll)
        self.table.verticalScrollBar().valueChanged.connect(
            self._schedule_memory_scroll
        )

    def refresh(self) -> None:
        """Render the current mapped window without allocating cells for all rows."""

        access = self._latest_access()
        target = access.address if access is not None else self._start
        total_rows = self._image.row_count(DEBUGGER_LAYOUT.MEMORY_BYTES_PER_ROW)
        target_row = self._image.row_index(
            target,
            DEBUGGER_LAYOUT.MEMORY_BYTES_PER_ROW,
        )
        self._refreshing = True
        try:
            if self.table.rowCount() != total_rows:
                self.table.setRowCount(total_rows)
            self.table.verticalScrollBar().setValue(target_row or 0)
            self._render_memory_window(self.table.verticalScrollBar().value())
        finally:
            self._refreshing = False
        self.table.resize_columns()
        if access is not None:
            size = max(1, int(access.details.get("size", 1)))
            self._show_selection(access.address, access.address + size - 1)

    def _render_memory_window(self, first_row: int) -> None:
        """Replace items only in the fixed-size visible row window."""

        for row in self._rendered_rows:
            for column in range(self.table.columnCount()):
                self.table.takeItem(row, column)
        window_rows = max(
            DEBUGGER_LAYOUT.MEMORY_ROWS,
            self.table.verticalScrollBar().pageStep(),
        )
        last_row = min(
            self.table.rowCount(),
            first_row + window_rows,
        )
        rows = tuple(range(first_row, last_row))
        for row in rows:
            address = self._image.row_address(
                row,
                DEBUGGER_LAYOUT.MEMORY_BYTES_PER_ROW,
            )
            if address is not None:
                self._render_row(row, address)
        self._rendered_rows = rows
        address = self._image.row_address(
            first_row,
            DEBUGGER_LAYOUT.MEMORY_BYTES_PER_ROW,
        )
        if address is not None:
            self._start = address

    def _schedule_memory_scroll(self, value: int) -> None:
        """Coalesce rapid scrollbar changes into one small window refresh."""

        if self._refreshing:
            return
        address = self._image.row_address(
            value,
            DEBUGGER_LAYOUT.MEMORY_BYTES_PER_ROW,
        )
        if address is not None:
            self._start = address
            self._memory_scroll_timer.start(0)

    def _refresh_memory_scroll(self) -> None:
        """Render the final scrollbar position reached in the current event turn."""

        self.refresh()
