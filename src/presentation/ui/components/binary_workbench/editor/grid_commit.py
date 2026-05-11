from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES


class GridCommitMixin:
    def commit_current_editor_text(self) -> None:
        if self._dirty_editor_kind is None:
            return
        if self._dirty_editor_kind == BINARY_WORKBENCH_TEXT.BYTES:
            rows = self._byte_rows_from_lines(self.bytes.toPlainText().splitlines())
            self._commit_visible_rows(rows, True)
            return
        rows = self._instruction_rows_from_lines(self.instructions.toPlainText().splitlines())
        self._commit_visible_rows(rows, False)

    def _commit_visible_rows(self, rows: list[BinaryWorkbenchRowDTO] | None, editing_bytes: bool) -> None:
        if rows is None:
            return
        old_count = len(self._rows)
        self._rows = rows
        if not editing_bytes:
            labels = labels_from_rows(rows)
            self._set_editing_labels(labels)
        self._commit_rows_to_context(rows, old_count)
        self._render_raw_instructions()
        self._dirty_editor_kind = None

    def _commit_rows_to_context(self, rows: list[BinaryWorkbenchRowDTO], old_count: int) -> None:
        if not self._virtual:
            start = self._aligned_scroll_offset(self.scrollbar.value()) // ROW_BYTES
            self._all_rows[start : start + old_count] = rows
            self.rowsChanged.emit(self.export_rows())
            return
        self.rowsChanged.emit(self._rows)
