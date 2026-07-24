"""Compensated column sizing for debugger tables."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT


class CompensatedColumnLayout:
    """Keep interactive columns inside the usable table viewport."""

    def __init__(
        self,
        table: QTableWidget,
        minimums: Sequence[int],
        maximums: Sequence[int],
        growth_columns: Sequence[int],
        compensation_columns: Sequence[int],
    ) -> None:
        """Bind per-column limits and compensation priorities to one table."""

        if not (
            table.columnCount() == len(minimums) == len(maximums)
        ):
            raise ValueError("Column limits must match the table column count.")
        self._table = table
        self._minimums = tuple(minimums)
        self._maximums = tuple(maximums)
        self._growth_columns = tuple(growth_columns)
        self._compensation_columns = tuple(compensation_columns)
        self._updating = False
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(min(self._minimums))
        header.sectionResized.connect(self._section_resized)
        self._set_standard_cursors()

    def fit(self) -> None:
        """Fit current widths to the viewport while preserving their proportions."""

        widths = self._bounded_widths()
        delta = self.usable_width - sum(widths)
        self._distribute(widths, delta, self._growth_columns)
        self._apply(widths)

    @property
    def usable_width(self) -> int:
        """Return the width that must be occupied by table columns."""

        minimum = sum(self._minimums)
        viewport = self._table.viewport().width() - DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
        return max(minimum, viewport)

    def _section_resized(self, column: int, _old: int, new: int) -> None:
        """Compensate a user resize without moving the table or scrollbar."""

        if self._updating:
            return
        widths = self._bounded_widths()
        widths[column] = min(
            self._maximums[column],
            max(self._minimums[column], new),
        )
        delta = self.usable_width - sum(widths)
        candidates = tuple(
            candidate
            for candidate in self._compensation_columns
            if candidate != column
        )
        delta = self._distribute(widths, delta, candidates, sequential=True)
        self._distribute(widths, delta, (column,), sequential=True)
        self._apply(widths)

    def _bounded_widths(self) -> list[int]:
        """Return current widths clamped to their per-column limits."""

        return [
            min(maximum, max(minimum, self._table.columnWidth(column)))
            for column, (minimum, maximum) in enumerate(
                zip(self._minimums, self._maximums)
            )
        ]

    def _distribute(
        self,
        widths: list[int],
        delta: int,
        columns: Sequence[int],
        *,
        sequential: bool = False,
    ) -> int:
        """Apply a signed width delta and return any unavailable remainder."""

        active = list(columns)
        while delta and active:
            share = abs(delta) if sequential else (abs(delta) + len(active) - 1) // len(active)
            for column in tuple(active):
                capacity = (
                    self._maximums[column] - widths[column]
                    if delta > 0
                    else widths[column] - self._minimums[column]
                )
                change = min(abs(delta), share, capacity)
                widths[column] += change if delta > 0 else -change
                delta += -change if delta > 0 else change
                if change == capacity:
                    active.remove(column)
                if not delta:
                    break
        return delta

    def _apply(self, widths: Sequence[int]) -> None:
        """Apply one complete width set without recursive section callbacks."""

        self._updating = True
        try:
            for column, width in enumerate(widths):
                self._table.setColumnWidth(column, width)
        finally:
            self._updating = False

    def _set_standard_cursors(self) -> None:
        """Keep pointer cursors restricted to actual controls."""

        widgets = (
            self._table,
            self._table.viewport(),
            self._table.horizontalHeader(),
            self._table.verticalScrollBar(),
            self._table.horizontalScrollBar(),
        )
        for widget in widgets:
            widget.setCursor(Qt.ArrowCursor)
