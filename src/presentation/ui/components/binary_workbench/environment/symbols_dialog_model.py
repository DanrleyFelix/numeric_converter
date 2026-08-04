from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


@dataclass
class SymbolRecord:
    """Represent one symbol while its management dialog is open."""
    symbol_id: int
    name: str
    value: str


class SymbolsTableModel(QAbstractTableModel):
    """Expose symbol records without creating permanent row widgets."""
    NAME_COLUMN = 0
    VALUE_COLUMN = 1
    COLUMN_COUNT = 2
    SYMBOL_ID_ROLE = int(Qt.ItemDataRole.UserRole) + 1

    def __init__(self, symbols: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self._next_symbol_id = 0
        self._records = [self._new_record(str(name), str(value)) for name, value in symbols.items()]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of symbols for root model indexes."""
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the fixed Name and Value column count."""
        return 0 if parent.isValid() else self.COLUMN_COUNT

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Return display, edit, and stable-identity data for a cell."""
        if not index.isValid() or not 0 <= index.row() < len(self._records):
            return None
        record = self._records[index.row()]
        if role in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole}:
            return record.name if index.column() == self.NAME_COLUMN else record.value
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        if role == self.SYMBOL_ID_ROLE:
            return record.symbol_id
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Update only the edited field and notify views for that cell."""
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        record = self._records[index.row()]
        text = str(value)
        previous = record.name if index.column() == self.NAME_COLUMN else record.value
        if text == previous:
            return False
        if index.column() == self.NAME_COLUMN:
            record.name = text
        elif index.column() == self.VALUE_COLUMN:
            record.value = text
        else:
            return False
        roles = [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]
        self.dataChanged.emit(index, index, roles)
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Allow selecting and temporarily editing every valid cell."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        """Return the two visible column headers."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            headers = (BINARY_WORKBENCH_TEXT.SYMBOL_NAME, BINARY_WORKBENCH_TEXT.SYMBOL_VALUE)
            return headers[section] if 0 <= section < self.COLUMN_COUNT else None
        return super().headerData(section, orientation, role)

    def symbols(self) -> dict[str, str]:
        """Export non-empty records using the established prefix cleanup."""
        result: dict[str, str] = {}
        for record in self._records:
            name = record.name.strip()
            value = record.value.strip()
            if name and value:
                result[name.lstrip("_@")] = value
        return result

    def record_at(self, row: int) -> SymbolRecord | None:
        """Return a record by source-model row."""
        return self._records[row] if 0 <= row < len(self._records) else None

    def row_for_id(self, symbol_id: int) -> int:
        """Resolve a stable symbol identity back to its current source row."""
        return next((row for row, record in enumerate(self._records) if record.symbol_id == symbol_id), -1)

    def merge_symbols(self, symbols: dict[str, str]) -> int | None:
        """Merge a batch with grouped updates and one insertion range."""
        existing = {record.name.strip().lstrip("_@").casefold(): record for record in self._records}
        changed_rows: list[int] = []
        inserted: list[SymbolRecord] = []
        selected_id: int | None = None
        for raw_name, raw_value in symbols.items():
            name, value = str(raw_name), str(raw_value)
            record = existing.get(name.strip().lstrip("_@").casefold())
            if record is None:
                record = self._new_record(name, value)
                inserted.append(record)
                existing[name.strip().lstrip("_@").casefold()] = record
            else:
                record.value = value
                changed_rows.append(self.row_for_id(record.symbol_id))
            selected_id = record.symbol_id
        self._emit_changed_ranges(changed_rows)
        if inserted:
            first = len(self._records)
            self.beginInsertRows(QModelIndex(), first, first + len(inserted) - 1)
            self._records.extend(inserted)
            self.endInsertRows()
        return selected_id

    def remove_symbol(self, symbol_id: int) -> bool:
        """Remove exactly one record identified independently of view order."""
        row = self.row_for_id(symbol_id)
        if row < 0:
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        self._records.pop(row)
        self.endRemoveRows()
        return True

    def remove_symbols(self, symbol_ids: set[int]) -> bool:
        """Remove every selected symbol through its stable identity."""
        removed = False
        for symbol_id in tuple(symbol_ids):
            removed = self.remove_symbol(symbol_id) or removed
        return removed

    def _new_record(self, name: str, value: str) -> SymbolRecord:
        """Allocate the next dialog-local stable identity."""
        record = SymbolRecord(self._next_symbol_id, name, value)
        self._next_symbol_id += 1
        return record

    def _emit_changed_ranges(self, rows: list[int]) -> None:
        """Coalesce adjacent updates instead of notifying per imported symbol."""
        ordered = sorted({row for row in rows if row >= 0})
        if not ordered:
            return
        start = previous = ordered[0]
        for row in ordered[1:] + [ordered[-1] + 2]:
            if row == previous + 1:
                previous = row
                continue
            roles = [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]
            self.dataChanged.emit(
                self.index(start, self.VALUE_COLUMN), self.index(previous, self.VALUE_COLUMN), roles)
            start = previous = row
