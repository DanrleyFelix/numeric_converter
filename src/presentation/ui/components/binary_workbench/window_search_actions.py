from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.search import (
    BinaryWorkbenchFindDialog,
    BinaryWorkbenchGoToDialog,
    BinaryWorkbenchHazardsWindow,
    BinaryWorkbenchSelectBlockDialog,
    BinaryWorkbenchReplaceBytesDialog,
    confirm_nonzero_byte_replacement,
)


class BinaryWorkbenchWindowSearchMixin:
    def _open_go_to(self) -> None:
        self.tabs.commit_current_editor_text()
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchGoToDialog(
            current,
            self,
            symbol_offsets_provider=lambda name: self.tabs.symbol_offsets_for(
                current.tab_id,
                name,
            ),
        )
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        offsets = dialog.selected_offsets()
        if not offsets:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_TARGET_PENDING, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self.tabs.go_to_offset(offsets[0])
        if len(offsets) > 1:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_MULTIPLE_TARGETS, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)

    def _open_find(self) -> None:
        dialog = BinaryWorkbenchFindDialog(
            self.tabs.find_offsets,
            self.tabs.last_search_end_offset,
            self,
        )
        dialog.goToRequested.connect(self.tabs.go_to_offset)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        offset = dialog.selected_offset()
        if offset is None:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NOT_FOUND, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self.tabs.go_to_offset(offset)

    def _open_hazards(self) -> None:
        if getattr(self, "_hazards_window", None) is None:
            self._hazards_window = BinaryWorkbenchHazardsWindow(
                self.tabs.cached_hazards,
                self.tabs.refresh_hazards,
                self.tabs.last_search_end_offset,
                self,
            )
            self._hazards_window.goToRequested.connect(self.tabs.go_to_offset)
            self._hazards_window.destroyed.connect(lambda: setattr(self, "_hazards_window", None))
        self._hazards_window.refresh_cached_results()
        self._hazards_window.show()
        self._hazards_window.raise_()
        self._hazards_window.activateWindow()

    def _open_select_block(self) -> None:
        dialog = BinaryWorkbenchSelectBlockDialog(
            self,
            start_offset=self.tabs.current_cursor_offset(),
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        selected = dialog.selected_range()
        if selected is not None:
            self.tabs.select_block(*selected)

    def _open_replace_bytes(self) -> None:
        dialog = BinaryWorkbenchReplaceBytesDialog(
            self,
            start_offset=self.tabs.current_cursor_offset(),
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        request = dialog.replacement_request()
        if request is None:
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_REPLACE_BYTES_INVALID,
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
                error=True,
            )
            return
        existing = self.tabs.replacement_bytes_at(request.start_offset, len(request.data))
        if existing is None:
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_REPLACE_BYTES_OUT_OF_RANGE,
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
                error=True,
            )
            return
        if any(existing) and not confirm_nonzero_byte_replacement(self):
            return
        if not self.tabs.replace_bytes_at(request.start_offset, request.data):
            self._show_status(
                BINARY_WORKBENCH_TEXT.STATUS_REPLACE_BYTES_OUT_OF_RANGE,
                BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
                error=True,
            )
            return
        self._show_status(
            BINARY_WORKBENCH_TEXT.STATUS_REPLACE_BYTES_SUCCESS_TEMPLATE.format(
                length=len(request.data),
                offset=request.start_offset,
            ),
            BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS,
        )
