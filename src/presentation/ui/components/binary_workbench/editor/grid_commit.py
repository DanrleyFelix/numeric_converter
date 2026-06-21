from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES


class GridCommitMixin:
    def commit_current_editor_text(self) -> None:
        if self._dirty_editor_kind is None:
            return
        if self._dirty_editor_kind == BINARY_WORKBENCH_TEXT.BYTES:
            rows = self._byte_rows_from_lines(self.bytes.toPlainText().splitlines())
            self._commit_origin_rows(rows, BINARY_WORKBENCH_TEXT.BYTES, True)
            return
        rows = self._instruction_rows_from_lines(self.instructions.toPlainText().splitlines())
        self._commit_origin_rows(rows, BINARY_WORKBENCH_TEXT.INSTRUCTION, False)

    def _commit_origin_rows(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None,
        origin: str,
        editing_bytes: bool,
    ) -> None:
        self._edit_origin_kind = origin
        try:
            self._commit_visible_rows(rows, editing_bytes)
        finally:
            self._edit_origin_kind = None

    def _commit_visible_rows(self, rows: list[BinaryWorkbenchRowDTO] | None, editing_bytes: bool) -> None:
        if rows is None:
            self._restore_editor_after_rejected_change(editing_bytes)
            return
        if not self._editor_change_allowed(editing_bytes) or not self._rows_change_allowed(rows, editing_bytes):
            self._restore_editor_after_rejected_change(editing_bytes)
            return
        self._rows = rows
        if not editing_bytes:
            labels = labels_from_rows(rows)
            self._set_editing_labels(labels)
        self._commit_rows_to_context(rows)
        self._render_raw_instructions()
        self._dirty_editor_kind = None

    def _commit_rows_to_context(self, rows: list[BinaryWorkbenchRowDTO]) -> None:
        if not self._virtual:
            self._all_rows = list(rows)
            self._rows = list(rows)
            self._total_size = len(self._all_rows) * ROW_BYTES
            self._configure_scrollbar()
            self._render_offsets()
            self._scroll_static_document(self.scrollbar.value())
            self.rowsChanged.emit(self.export_rows())
            return
        self._render_offsets()
        self.rowsChanged.emit(self._rows)
