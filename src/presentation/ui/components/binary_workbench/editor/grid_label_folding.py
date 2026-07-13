from __future__ import annotations

from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.label_folding import label_fold_regions


class GridLabelFoldingMixin:
    """Synchronize assembly label folding across every visible row surface."""

    def set_label_folding_enabled(self, enabled: bool) -> None:
        """Enable fold controls for assembly-style tabs only."""

        self._label_folding_enabled = enabled
        if not enabled:
            self._collapsed_labels.clear()
        self.instructions.set_label_folding_enabled(enabled)
        self._refresh_label_folding()

    def toggle_label_fold(self, label: str) -> None:
        """Collapse or expand the rows owned by a label."""

        if not self._label_folding_enabled:
            return
        if label in self._collapsed_labels:
            self._collapsed_labels.remove(label)
        else:
            self._collapsed_labels.add(label)
        self._refresh_label_folding()
        self._schedule_layout_refresh()

    def expand_label_for_offset(self, offset: int) -> bool:
        """Expand a collapsed label reached by branch or jump navigation."""

        target_row = self._row_for_offset(offset)
        expanded = {
            region.label
            for region in self._label_fold_regions
            if region.label in self._collapsed_labels
            and (
                self._label_offset(region.label) == offset
                or (target_row is not None and region.contains(target_row))
            )
        }
        if not expanded:
            return False
        self._collapsed_labels.difference_update(expanded)
        self._refresh_label_folding()
        self._schedule_layout_refresh()
        return True

    def _refresh_label_folding(self) -> None:
        """Recalculate regions and apply one visibility mask to all columns."""

        regions = label_fold_regions(self._rows) if self._label_folding_enabled else []
        self._label_fold_regions = regions
        valid_labels = {region.label for region in regions}
        self._collapsed_labels.intersection_update(valid_labels)
        self.instructions.set_label_fold_regions(
            {
                region.label_row: (region.label, region.label in self._collapsed_labels)
                for region in regions
            }
        )
        hidden_rows = {
            row
            for region in regions
            if region.label in self._collapsed_labels
            for row in range(region.first_hidden_row, region.last_hidden_row + 1)
        }
        for editor in self._fold_editors():
            self._apply_hidden_rows(editor, hidden_rows)
        if not self._virtual:
            self._scroll_static_document(self.scrollbar.value())

    def _fold_editors(self):
        """Return every editor whose blocks represent complete grid rows."""

        return (
            *self._offset_editors.values(),
            self.raw_instructions,
            self.bytes,
            self.decoded_text,
            self.instructions,
        )

    def _apply_hidden_rows(self, editor, hidden_rows: set[int]) -> None:
        """Apply row visibility without changing text or the undo document."""

        document = editor.document()
        block = document.firstBlock()
        while block.isValid():
            visible = block.blockNumber() not in hidden_rows
            block.setVisible(visible)
            block.setLineCount(1 if visible else 0)
            block = block.next()
        document.markContentsDirty(0, document.characterCount())
        editor.viewport().update()
        if editor is self.instructions and editor.textCursor().blockNumber() in hidden_rows:
            self._move_instruction_cursor_to_visible_label(hidden_rows)

    def _move_instruction_cursor_to_visible_label(self, hidden_rows: set[int]) -> None:
        """Move an instruction cursor out of a block that has just been hidden."""

        current = self.instructions.textCursor().blockNumber()
        region = next((item for item in self._label_fold_regions if item.contains(current)), None)
        if region is None:
            return
        cursor = QTextCursor(self.instructions.document().findBlockByNumber(region.label_row))
        self.instructions.setTextCursor(cursor)

    def _label_offset(self, label: str) -> int | None:
        """Resolve a label name to its current file offset."""

        value = next(
            (offset for name, offset in self._labels.items() if name.lower() == label.lower()),
            None,
        )
        try:
            return int(value, 0) if value is not None else None
        except ValueError:
            return None

    def _visible_block_position(self, row_index: int) -> int:
        """Map a logical row index to the visible document line index."""

        document = self.instructions.document()
        return sum(
            1
            for index in range(min(row_index, document.blockCount()))
            if document.findBlockByNumber(index).isVisible()
        )
