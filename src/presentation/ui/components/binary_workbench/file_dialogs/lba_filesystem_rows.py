from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO


class LbaFilesystemRowsMixin:
    """Manage LBA records incrementally through the shared table model."""

    def mappings(self) -> list[BinaryWorkbenchInternalFileDTO]:
        """Export valid records using the existing DTO contract."""

        rows: list[BinaryWorkbenchInternalFileDTO] = []
        for record in self.lba_model.records():
            try:
                start_lba = int(record.cells[1].strip(), 0)
            except ValueError:
                continue
            if record.cells[0].strip():
                rows.append(BinaryWorkbenchInternalFileDTO(record.cells[0].strip(), start_lba))
        return rows

    def _replace_rows(self, files: list[BinaryWorkbenchInternalFileDTO]) -> None:
        """Load a complete mapping with one model reset."""

        self.lba_model.replace([([item.name, str(item.start_lba)], None, "") for item in files])

    def _append_from_entry(self) -> None:
        """Append one mapping from the fixed entry controls."""

        record_id = self.lba_model.append([self.name.text(), self.lba.text()])
        self.name.clear()
        self.lba.clear()
        self._select_record(record_id)

    def _append_row(self, name: str, lba: str) -> None:
        """Retain the legacy insertion hook used by JSON loading."""

        self.lba_model.append([name, lba])

    def _clear_rows(self) -> None:
        """Clear mappings without deleting widgets per record."""

        self.lba_model.replace([])

    def _apply_filter(self) -> None:
        """Filter both visible columns through the proxy."""

        self.lba_proxy.set_query(self.filter_input.text())
        self._update_action_state()

    def _selected_record(self):
        """Map the selected proxy index back to its source record."""

        index = self.table.currentIndex()
        if not index.isValid():
            return None
        return self.lba_model.record_at(self.lba_proxy.mapToSource(index).row())

    def _select_record(self, record_id: int) -> None:
        """Select a newly inserted record independently of sorting."""

        row = self.lba_model.row_for_id(record_id)
        proxy_index = self.lba_proxy.mapFromSource(self.lba_model.index(row, 0))
        if proxy_index.isValid():
            self.table.selectRow(proxy_index.row())

    def _remove_selected(self) -> None:
        """Remove the selected record and refresh fixed action states."""

        record = self._selected_record()
        if record is not None:
            self.lba_model.remove(record.record_id)
        self._update_action_state()

    def _go_to_selected(self) -> None:
        """Navigate to the selected LBA converted to its byte offset."""

        record = self._selected_record()
        if record is None:
            return
        try:
            self.goToRequested.emit(int(record.cells[1].strip(), 0) * self.selected_lba_sector_size())
        except ValueError:
            return

    def _update_action_state(self, *args) -> None:
        """Enable record actions only for a visible valid selection."""

        enabled = self._selected_record() is not None
        self.remove_button.setEnabled(enabled)
        self.go_to_button.setEnabled(enabled)
