from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from src.presentation.ui.components.workspace_table.rows import WorkspaceRow


class WorkspaceTableModel(QAbstractTableModel):
    """Virtualized Numeric Variables/Logs model with incremental notifications."""

    KEY_ROLE = int(Qt.ItemDataRole.UserRole) + 1

    def __init__(self, headers: tuple[str, ...], parent=None) -> None:
        super().__init__(parent)
        self._headers = headers
        self._rows: list[WorkspaceRow] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return row.values[index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        if role == self.KEY_ROLE:
            return row.key
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section] if 0 <= section < len(self._headers) else None
        return super().headerData(section, orientation, role)

    def replace_rows(self, rows: list[WorkspaceRow]) -> None:
        """Reconcile a snapshot using row insert/remove/dataChanged, never reset."""
        if [row.key for row in self._rows] == [row.key for row in rows]:
            changed = [index for index, row in enumerate(rows) if row != self._rows[index]]
            self._rows[:] = rows
            for first, last in _adjacent_ranges(changed):
                self.dataChanged.emit(
                    self.index(first, 0),
                    self.index(last, len(self._headers) - 1),
                    [Qt.ItemDataRole.DisplayRole],
                )
            return

        prefix = 0
        limit = min(len(self._rows), len(rows))
        while prefix < limit and self._rows[prefix] == rows[prefix]:
            prefix += 1
        if prefix < len(self._rows):
            self.beginRemoveRows(QModelIndex(), prefix, len(self._rows) - 1)
            del self._rows[prefix:]
            self.endRemoveRows()
        if prefix < len(rows):
            self.beginInsertRows(QModelIndex(), prefix, len(rows) - 1)
            self._rows.extend(rows[prefix:])
            self.endInsertRows()


class WorkspaceFilterProxyModel(QSortFilterProxyModel):
    """Case-insensitive all-column filter for Numeric workspace tables."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)
        self.setDynamicSortFilter(True)


def _adjacent_ranges(indices: list[int]) -> list[tuple[int, int]]:
    if not indices:
        return []
    ranges: list[tuple[int, int]] = []
    first = previous = indices[0]
    for index in indices[1:]:
        if index == previous + 1:
            previous = index
            continue
        ranges.append((first, previous))
        first = previous = index
    ranges.append((first, previous))
    return ranges
