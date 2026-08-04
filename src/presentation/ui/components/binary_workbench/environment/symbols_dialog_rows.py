from __future__ import annotations

from PySide6.QtCore import QModelIndex, QItemSelectionModel

from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.presentation.ui.components.binary_workbench.environment.symbol_offsets_dialog import (
    BinaryWorkbenchSymbolOffsetsDialog,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_model import (
    SymbolRecord,
)


class SymbolsDialogRowsMixin:
    """Coordinate incremental model operations and selection-based actions."""

    def values(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        """Return symbols using the public tuple shape retained for compatibility."""

        return self.symbols_model.symbols(), {}, {}

    def _merge_rows(self, symbols: dict[str, str]) -> None:
        """Merge one logical batch and refresh filtering only once."""

        selected_id = self._selected_symbol_id()
        affected_id = self.symbols_model.merge_symbols(merged_symbol_values(symbols))
        self._select_symbol(affected_id if affected_id is not None else selected_id)
        self.symbolsChanged.emit(self.values()[0])

    def _append_from_entry(self) -> None:
        """Merge the entry fields as one incremental operation."""

        self._merge_rows({self.name.text(): self.value.text()})
        self.name.clear()
        self.value.clear()

    def _remove_selected_symbol(self) -> None:
        """Remove the source record represented by the selected proxy row."""

        proxy_index = self._selected_proxy_index()
        record = self._selected_record()
        if record is None:
            return
        next_proxy_row = proxy_index.row()
        if not self.symbols_model.remove_symbol(record.symbol_id):
            return
        self.symbolsChanged.emit(self.values()[0])
        if self.symbols_proxy.rowCount() > 0:
            self.table.selectRow(min(next_proxy_row, self.symbols_proxy.rowCount() - 1))
        self._update_action_state()

    def _open_selected_symbol_offsets(self) -> None:
        """Request offsets for the stable symbol currently selected."""

        record = self._selected_record()
        if record is not None:
            self._open_symbol_offsets(record.name)

    def _open_symbol_offsets(self, name: str) -> None:
        """Open one offsets dialog using the current provider context."""

        clean_name = name.strip().lstrip("_@")
        context_id: str | None = None
        offsets = self._symbol_offsets.get(clean_name, [])
        if self._offsets_provider is not None:
            context_id, offsets = self._offsets_provider(clean_name)
        dialog = BinaryWorkbenchSymbolOffsetsDialog(clean_name or name.strip(), list(offsets), self)
        self._active_offsets_dialog = dialog
        self._active_offsets_context_id = context_id
        dialog.goToRequested.connect(self.goToRequested.emit)
        try:
            dialog.exec()
        finally:
            self._active_offsets_dialog = None
            self._active_offsets_context_id = None

    def invalidate_offsets_context(self, _index: int | None = None) -> None:
        """Mark an open Global Offsets result stale without recalculating it."""

        if (
            self._active_offsets_dialog is not None
            and self._active_offsets_context_id is not None
        ):
            self._active_offsets_dialog.mark_stale()

    def _apply_filter(self, text: str = "") -> None:
        """Forward one filter change to the proxy model."""

        self.symbols_proxy.set_filter_text(text)
        self._update_action_state()

    def _selected_proxy_index(self) -> QModelIndex:
        """Return the selected proxy row's first-column index."""

        rows = self.table.selectionModel().selectedRows()
        return rows[0] if len(rows) == 1 else QModelIndex()

    def _selected_record(self) -> SymbolRecord | None:
        """Map the visual selection to its source-model record."""

        proxy_index = self._selected_proxy_index()
        if not proxy_index.isValid():
            return None
        source_index = self.symbols_proxy.mapToSource(proxy_index)
        symbol_id = source_index.data(self.symbols_model.SYMBOL_ID_ROLE)
        if not isinstance(symbol_id, int):
            return None
        return self.symbols_model.record_at(self.symbols_model.row_for_id(symbol_id))

    def _selected_symbol_id(self) -> int | None:
        """Return the stable identity of the current selection."""

        record = self._selected_record()
        return record.symbol_id if record is not None else None

    def _select_symbol(self, symbol_id: int | None) -> None:
        """Restore selection by identity after filtering or sorting changes."""

        if symbol_id is None:
            self.table.clearSelection()
            self._update_action_state()
            return
        source_row = self.symbols_model.row_for_id(symbol_id)
        source_index = self.symbols_model.index(source_row, self.symbols_model.NAME_COLUMN)
        proxy_index = self.symbols_proxy.mapFromSource(source_index)
        if not proxy_index.isValid():
            self.table.clearSelection()
            self._update_action_state()
            return
        self.table.selectionModel().setCurrentIndex(
            proxy_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        self.table.scrollTo(proxy_index)

    def _update_action_state(self, *_args) -> None:
        """Enable row actions only for one valid visible selection."""

        enabled = self._selected_record() is not None
        self.offsets_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
