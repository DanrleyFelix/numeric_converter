from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.search import (
    BinaryWorkbenchFindDialog,
    BinaryWorkbenchGoToDialog,
    BinaryWorkbenchSelectBlockDialog,
)


class BinaryWorkbenchWindowSearchMixin:
    def _open_go_to(self) -> None:
        self.tabs.commit_current_editor_text()
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchGoToDialog(current, self)
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
        dialog = BinaryWorkbenchFindDialog(self.tabs.find_offsets, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        offset = dialog.selected_offset()
        if offset is None:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NOT_FOUND, BINARY_WORKBENCH_TIMING.STATUS_MESSAGE_VISIBLE_MS)
            return
        self.tabs.go_to_offset(offset)

    def _open_select_block(self) -> None:
        dialog = BinaryWorkbenchSelectBlockDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        selected = dialog.selected_range()
        if selected is not None:
            self.tabs.select_block(*selected)
