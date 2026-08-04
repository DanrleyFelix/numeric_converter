from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt


@dataclass
class EnvironmentRecord:
    """Store one table record without allocating row widgets."""

    record_id: int
    cells: list[str]
    payload: object | None = None
    search_extra: str = ""


class EnvironmentTableModel(QAbstractTableModel):
    """Provide incrementally editable records to environment tables."""

    RECORD_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 1

    def __init__(self, headers: tuple[str, ...], editable_columns: set[int], parent=None) -> None:
        super().__init__(parent)
        self._headers = headers
        self._editable_columns = editable_columns
        self._records: list[EnvironmentRecord] = []
        self._next_record_id = 0

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of root records."""
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the fixed header count."""
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Return cell content, alignment, or stable record identity."""
        if not index.isValid() or not 0 <= index.row() < len(self._records):
            return None
        record = self._records[index.row()]
        if role in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole}:
            return record.cells[index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        if role == self.RECORD_ID_ROLE:
            return record.record_id
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Update one editable cell and emit a local notification."""
        if (
            role != Qt.ItemDataRole.EditRole
            or not index.isValid()
            or not 0 <= index.row() < len(self._records)
            or not 0 <= index.column() < len(self._headers)
            or index.column() not in self._editable_columns
        ):
            return False
        text = str(value)
        record = self._records[index.row()]
        if record.cells[index.column()] == text:
            return False
        record.cells[index.column()] = text
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, role])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Expose selectable rows and editors only for configured columns."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return flags | Qt.ItemFlag.ItemIsEditable if index.column() in self._editable_columns else flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        """Return horizontal environment table headers."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section] if 0 <= section < len(self._headers) else None
        return super().headerData(section, orientation, role)

    def replace(self, rows: list[tuple[list[str], object | None, str]]) -> None:
        """Replace a loaded dataset with one model reset rather than per-row widgets."""
        self.beginResetModel()
        self._records = [self._new_record(cells, payload, extra) for cells, payload, extra in rows]
        self.endResetModel()

    def append(self, cells: list[str], payload: object | None = None, search_extra: str = "") -> int:
        """Insert one record and return its stable dialog-local identity."""
        row = len(self._records)
        self.beginInsertRows(QModelIndex(), row, row)
        record = self._new_record(cells, payload, search_extra)
        self._records.append(record)
        self.endInsertRows()
        return record.record_id

    def remove(self, record_id: int) -> bool:
        """Remove the record matching a stable identity."""

        row = self.row_for_id(record_id)
        if row < 0:
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        self._records.pop(row)
        self.endRemoveRows()
        return True

    def remove_many(self, record_ids: set[int]) -> bool:
        """Remove selected stable identities safely as source rows shift."""

        removed = False
        for record_id in tuple(record_ids):
            removed = self.remove(record_id) or removed
        return removed

    def record_at(self, row: int) -> EnvironmentRecord | None:
        """Return a source record by row."""

        return self._records[row] if 0 <= row < len(self._records) else None

    def row_for_id(self, record_id: int) -> int:
        """Resolve a stable identity after filtering or sorting."""

        return next((row for row, item in enumerate(self._records) if item.record_id == record_id), -1)

    def records(self) -> tuple[EnvironmentRecord, ...]:
        """Return an immutable view of current records."""

        return tuple(self._records)

    def notify_record(self, record_id: int) -> None:
        """Refresh every cell after payload-backed content changes."""

        row = self.row_for_id(record_id)
        if row >= 0:
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(self._headers) - 1))

    def _new_record(self, cells: list[str], payload: object | None, extra: str) -> EnvironmentRecord:
        record = EnvironmentRecord(self._next_record_id, list(cells), payload, extra)
        self._next_record_id += 1
        return record


class EnvironmentFilterProxyModel(QSortFilterProxyModel):
    """Filter all displayed cells plus optional non-visible searchable data."""

    def set_query(self, query: str) -> None:
        """Apply a case-insensitive query once per user change."""

        self.setFilterFixedString(query.strip())

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Match visible columns and the record's auxiliary search text."""

        query = self.filterRegularExpression().pattern().casefold()
        if not query:
            return True
        source = self.sourceModel()
        record = source.record_at(source_row)
        return record is not None and query in " ".join(record.cells + [record.search_extra]).casefold()
