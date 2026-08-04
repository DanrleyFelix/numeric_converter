from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTableView


class SymbolsTableView(QTableView):
    """Track row-wide hover without changing cell-specific editing."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hovered_row = -1
        self.setMouseTracking(True)

    @property
    def hovered_row(self) -> int:
        """Return the proxy row currently under the pointer."""

        return self._hovered_row

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update the complete hovered row before normal view handling."""

        self._set_hovered_row(self.indexAt(event.position().toPoint()).row())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        """Clear row hover when the pointer exits the table viewport."""

        self._set_hovered_row(-1)
        super().leaveEvent(event)

    def _set_hovered_row(self, row: int) -> None:
        if row == self._hovered_row:
            return
        self._hovered_row = row
        self.viewport().update()
