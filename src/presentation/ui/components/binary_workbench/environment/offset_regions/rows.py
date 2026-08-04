from dataclasses import dataclass

from PySide6.QtWidgets import QDialog

from src.modules.binary_workbench_dtos import BinaryWorkbenchOffsetRegionDTO
from src.presentation.ui.components.binary_workbench.environment.offset_regions.details_dialog import OffsetRegionDetailsDialog


@dataclass
class OffsetRegionState:
    """Keep lazy details metadata independently of table cell widgets."""

    details: str
    details_loaded: bool
    source_name: str | None
    source_offset: int | None


class OffsetRegionsRowsMixin:
    """Manage offset records and lazy details through stable model identities."""

    def mappings(self) -> list[BinaryWorkbenchOffsetRegionDTO]:
        """Export valid regions using the established DTO fields."""

        regions = []
        for record in self.regions_model.records():
            state = record.payload
            try:
                offset = int(record.cells[1].strip(), 16)
            except ValueError:
                continue
            if record.cells[0].strip() and isinstance(state, OffsetRegionState):
                details = state.details if state.details_loaded else ""
                regions.append(BinaryWorkbenchOffsetRegionDTO(record.cells[0].strip(), offset, details, state.details_loaded, state.source_name, state.source_offset))
        return regions

    def _replace_regions(self, regions: list[BinaryWorkbenchOffsetRegionDTO]) -> None:
        """Replace a loaded collection with one model reset."""

        rows = []
        for region in regions:
            state = OffsetRegionState(region.details, region.details_loaded, region.details_source_name, region.details_source_offset)
            extra = region.details if region.details_loaded else ""
            rows.append(([region.name, f"{region.offset:X}"], state, extra))
        self.regions_model.replace(rows)
        self._apply_filter()

    def _append_from_entry(self) -> None:
        """Append one region from the fixed entry controls."""

        state = OffsetRegionState("", True, None, None)
        record_id = self.regions_model.append([self.name.text(), self.offset.text()], state)
        self.name.clear()
        self.offset.clear()
        self._select_record(record_id)

    def _selected_record(self):
        """Return one record only when exactly one row is selected."""

        records = self._selected_records()
        return records[0] if len(records) == 1 else None

    def _selected_records(self):
        """Return all source records selected through Ctrl or Shift."""

        records = []
        for index in self.table.selectionModel().selectedRows():
            record = self.regions_model.record_at(self.regions_proxy.mapToSource(index).row())
            if record is not None:
                records.append(record)
        return records

    def _select_record(self, record_id: int) -> None:
        row = self.regions_model.row_for_id(record_id)
        index = self.regions_proxy.mapFromSource(self.regions_model.index(row, 0))
        if index.isValid():
            self.table.selectRow(index.row())

    def _remove_selected(self) -> None:
        """Remove every selected region by stable record identity."""

        records = self._selected_records()
        self.regions_model.remove_many({record.record_id for record in records})
        self._update_action_state()

    def _apply_filter(self) -> None:
        """Filter visible fields and already-loaded details."""

        self.regions_proxy.set_query(self.filter_input.text())
        self._update_action_state()

    def _go_to_selected(self) -> None:
        """Navigate to the selected hexadecimal offset."""

        record = self._selected_record()
        if record is None:
            return
        try:
            self.goToRequested.emit(int(record.cells[1].strip(), 16))
        except ValueError:
            return

    def _edit_selected_details(self) -> None:
        """Load and edit details only for the selected region."""

        record = self._selected_record()
        if record is None or not isinstance(record.payload, OffsetRegionState):
            return
        state = record.payload
        details = self._load_details(record.cells, state)
        dialog = OffsetRegionDetailsDialog(details, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            state.details = dialog.details()
            state.details_loaded = True
            record.search_extra = state.details
            self.regions_model.notify_record(record.record_id)
            self._apply_filter()

    def _load_details(self, cells: list[str], state: OffsetRegionState) -> str:
        if state.details_loaded:
            return state.details
        try:
            offset = int(cells[1].strip(), 16)
        except ValueError:
            return ""
        loader = getattr(self, "_details_loader", None)
        source_name = state.source_name or cells[0].strip()
        source_offset = state.source_offset if state.source_offset is not None else offset
        state.details = loader(source_name, source_offset) if loader is not None else state.details
        state.details_loaded = True
        return state.details

    def _update_action_state(self, *args) -> None:
        records = self._selected_records()
        self.remove_button.setEnabled(bool(records))
        self.details_button.setEnabled(len(records) == 1)
        self.go_to_button.setEnabled(len(records) == 1)
