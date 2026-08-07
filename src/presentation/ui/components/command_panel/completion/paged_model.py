from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from src.presentation.ui.components.command_panel.constants import COMMAND_COMPLETION


class PagedCompletionModel(QAbstractListModel):
    """Lazy list model that exposes large completion results in fixed pages."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: Sequence[str] = ()
        self._visible_count = 0

    @property
    def loaded_count(self) -> int:
        return self._visible_count

    def set_items(self, items: Sequence[str]) -> None:
        self.beginResetModel()
        self._items = items
        total = len(items)
        self._visible_count = (
            total
            if total < COMMAND_COMPLETION.LAZY_THRESHOLD
            else min(COMMAND_COMPLETION.PAGE_SIZE, total)
        )
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else self._visible_count

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or not index.isValid():
            return None
        row = index.row()
        if not 0 <= row < self._visible_count:
            return None
        return self._items[row]

    def canFetchMore(self, parent=QModelIndex()) -> bool:
        return not parent.isValid() and self._visible_count < len(self._items)

    def fetchMore(self, parent=QModelIndex()) -> None:
        if parent.isValid() or not self.canFetchMore(parent):
            return
        first = self._visible_count
        last = min(first + COMMAND_COMPLETION.PAGE_SIZE, len(self._items)) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self._visible_count = last + 1
        self.endInsertRows()
