from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt


class SymbolsFilterProxyModel(QSortFilterProxyModel):
    """Filter Name and Value while preserving source-model identities."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._query = ""
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_filter_text(self, text: str) -> None:
        """Apply one case-insensitive query to both symbol columns."""

        query = text.strip().casefold()
        if query == self._query:
            return
        self.beginFilterChange()
        self._query = query
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Match the current query against both displayed fields."""

        if not self._query:
            return True
        model = self.sourceModel()
        if model is None:
            return False
        values = (
            model.index(source_row, column, source_parent).data(Qt.ItemDataRole.DisplayRole)
            for column in range(model.columnCount(source_parent))
        )
        return any(self._query in str(value or "").casefold() for value in values)
