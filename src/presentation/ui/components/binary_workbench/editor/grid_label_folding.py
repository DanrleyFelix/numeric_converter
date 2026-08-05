from __future__ import annotations

from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.directive_folding import debugger_directive_fold_region
from src.core.binary_workbench.label_folding import LabelFoldRegion, label_fold_regions
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)


class GridLabelFoldingMixin:
    """Synchronize assembly label folding across every visible row surface."""

    def set_label_folding_enabled(self, enabled: bool) -> None:
        """Enable fold controls for assembly-style tabs only."""

        self._label_folding_enabled = enabled
        if not enabled:
            self._collapsed_labels.clear()
            self._directives_collapsed = False
        self.instructions.set_label_folding_enabled(enabled)
        self._refresh_label_folding()

    def toggle_label_fold(self, label: str) -> None:
        """Collapse or expand the rows owned by a label."""

        if not self._label_folding_enabled:
            return
        anchor_row = self._scroll_anchor_source_row()
        if label in self._collapsed_labels:
            self._collapsed_labels.remove(label)
        else:
            self._collapsed_labels.add(label)
        self._apply_label_visibility(anchor_row)
        self._schedule_layout_refresh()

    def toggle_directive_fold(self) -> None:
        """Collapse or expand every leading debugger directive as a visual group."""

        if not self._label_folding_enabled or self._directive_fold_region is None:
            return
        anchor_row = self._scroll_anchor_source_row()
        self._directives_collapsed = not self._directives_collapsed
        self._apply_label_visibility(anchor_row)
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
        self._apply_label_visibility()
        self._schedule_layout_refresh()
        return True

    def _refresh_label_folding(self, anchor_row: int | None = None) -> None:
        """Recalculate regions and apply one visibility mask to all columns."""

        previous_regions = self._label_fold_regions
        regions = label_fold_regions(self._rows) if self._label_folding_enabled else []
        self._label_fold_regions = regions
        self._directive_fold_region = (
            debugger_directive_fold_region(self._rows)
            if self._label_folding_enabled
            else None
        )
        if self._directive_fold_region is None:
            self._directives_collapsed = False
        self._expand_owners_of_removed_labels(previous_regions, regions)
        valid_labels = {region.label for region in regions}
        self._collapsed_labels.intersection_update(valid_labels)
        self._apply_label_visibility(anchor_row)

    def _apply_label_visibility(self, anchor_row: int | None = None) -> None:
        """Apply cached fold regions without preprocessing source labels."""

        regions = self._label_fold_regions
        self.instructions.set_label_fold_regions(
            {
                region.label_row: (region.label, region.label in self._collapsed_labels)
                for region in regions
            }
        )
        directive = self._directive_fold_region
        self.instructions.set_directive_fold_region(
            (directive.header_row, self._directives_collapsed)
            if directive is not None
            else None
        )
        hidden_rows = self._folded_hidden_rows()
        was_syncing = self._syncing_editor_scrollbars
        self._syncing_editor_scrollbars = True
        try:
            self._render_offsets()
            for editor in self._fold_editors():
                self._apply_hidden_rows(editor, hidden_rows)
        finally:
            self._syncing_editor_scrollbars = was_syncing
        if not self._virtual:
            if anchor_row in hidden_rows:
                directive = self._directive_fold_region
                if directive is not None and directive.contains(anchor_row):
                    anchor_row = directive.header_row
                else:
                    region = next(
                        (item for item in regions if item.contains(anchor_row)),
                        None,
                    )
                    anchor_row = region.label_row if region is not None else None
            if anchor_row is not None:
                self._visible_start_offset = (
                    self._visible_position_for_source_row(anchor_row) * ROW_BYTES
                )
            self._configure_scrollbar()

    def _folded_hidden_rows(self) -> set[int]:
        """Return the current source-row mask shared by every grid column."""

        hidden = {
            row
            for region in self._label_fold_regions
            if region.label in self._collapsed_labels
            for row in range(region.first_hidden_row, region.last_hidden_row + 1)
        }
        if self._directives_collapsed and self._directive_fold_region is not None:
            hidden.update(
                range(
                    self._directive_fold_region.first_hidden_row,
                    self._directive_fold_region.last_hidden_row + 1,
                )
            )
        return hidden

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
        refresh_dashes = getattr(editor, "refresh_dash_overlays", None)
        if refresh_dashes is not None:
            refresh_dashes()
        editor.viewport().update()
        if editor is self.instructions and (
            editor.textCursor().blockNumber() in hidden_rows
            or self._collapsed_label_cursor_region(editor) is not None
        ):
            self._move_instruction_cursor_to_visible_label(hidden_rows)

    def _move_instruction_cursor_to_visible_label(self, hidden_rows: set[int]) -> None:
        """Place a cursor touching folded content at the label declaration end."""

        current = self.instructions.textCursor().blockNumber()
        directive = self._directive_fold_region
        if self._directives_collapsed and directive is not None and directive.contains(current):
            block = self.instructions.document().findBlockByNumber(directive.header_row)
            self.instructions.setTextCursor(QTextCursor(block))
            return
        region = next(
            (
                item
                for item in self._label_fold_regions
                if item.label in self._collapsed_labels
                and (item.label_row == current or item.contains(current))
            ),
            None,
        )
        if region is None:
            return
        block = self.instructions.document().findBlockByNumber(region.label_row)
        cursor = QTextCursor(block)
        set_cursor_position(cursor, block.position() + len(block.text()))
        self.instructions.setTextCursor(cursor)

    def expand_collapsed_label_at_cursor(
        self,
        editor,
        move_cursor_to_end: bool = False,
    ) -> bool:
        """Expand the folded label currently being edited, if any."""

        if editor is not self.instructions or editor.isReadOnly():
            return False
        if self._collapsed_directive_cursor_region(editor) is not None:
            self._directives_collapsed = False
            self._apply_label_visibility()
            self._schedule_layout_refresh()
            return True
        region = self._collapsed_label_cursor_region(editor)
        if region is None:
            return False
        if (
            move_cursor_to_end
            and editor.textCursor().blockNumber() == region.label_row
        ):
            block = editor.document().findBlockByNumber(region.label_row)
            cursor = QTextCursor(block)
            set_cursor_position(cursor, block.position() + len(block.text()))
            editor.setTextCursor(cursor)
        self._collapsed_labels.remove(region.label)
        self._apply_label_visibility()
        self._schedule_layout_refresh()
        return True

    def _expand_owners_of_removed_labels(
        self,
        previous: list[LabelFoldRegion],
        current: list[LabelFoldRegion],
    ) -> None:
        """Reveal a preceding label when it inherits a removed label's rows."""

        current_labels = {region.label for region in current}
        for removed in previous:
            if removed.label in current_labels:
                continue
            owner = next(
                (
                    region
                    for region in reversed(current)
                    if region.label_row < removed.label_row
                    and region.contains(removed.label_row)
                ),
                None,
            )
            if owner is not None:
                self._collapsed_labels.discard(owner.label)

    def _collapsed_label_cursor_region(self, editor):
        """Return the collapsed region containing the instruction cursor."""

        if editor is not self.instructions:
            return None
        row = editor.textCursor().blockNumber()
        return next(
            (
                region
                for region in self._label_fold_regions
                if (region.label_row == row or region.contains(row))
                and region.label in self._collapsed_labels
            ),
            None,
        )

    def _collapsed_directive_cursor_region(self, editor):
        """Return the collapsed directive group touched by the source cursor."""

        if editor is not self.instructions or not self._directives_collapsed:
            return None
        region = self._directive_fold_region
        return region if region is not None and region.contains(editor.textCursor().blockNumber()) else None

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

    def _scrollable_total_size(self) -> int:
        """Return viewport size units without counting folded source rows."""

        if self._virtual or not self._label_folding_enabled:
            return self._total_size
        document = self.instructions.document()
        return sum(
            ROW_BYTES
            for index in range(document.blockCount())
            if document.findBlockByNumber(index).isVisible()
        )

    def _folded_scrollbar_maximum(self, maximum: int) -> int:
        """Clamp shared scrolling to the reachable range of visible columns."""

        if self._virtual or not (self._collapsed_labels or self._directives_collapsed):
            return maximum
        limits = [
            editor.verticalScrollBar().maximum() * ROW_BYTES
            for editor in self._fold_editors()
            if self._scroll_editor_enabled(editor)
        ]
        return min([maximum, *limits]) if limits else maximum

    def _ensure_static_editor_scroll_range(self, maximum: int) -> None:
        """Restore editor ranges left stale after expanding folded blocks."""

        if self._virtual:
            return
        target = self._visible_block_position(maximum // ROW_BYTES)
        for editor in self._fold_editors():
            if self._scroll_editor_enabled(editor):
                scrollbar = editor.verticalScrollBar()
                scrollbar.setMaximum(max(scrollbar.maximum(), target))

    def _scroll_anchor_source_row(self) -> int | None:
        """Resolve the current visual top line back to its source row."""

        document = self.instructions.document()
        visible_target = self.scrollbar.value() // ROW_BYTES
        visible_index = 0
        for source_row in range(document.blockCount()):
            if not document.findBlockByNumber(source_row).isVisible():
                continue
            if visible_index == visible_target:
                return source_row
            visible_index += 1
        return None

    def _visible_position_for_source_row(self, source_row: int) -> int:
        """Map a source row to its ordinal among currently visible rows."""

        document = self.instructions.document()
        return sum(
            1
            for index in range(min(source_row, document.blockCount()))
            if document.findBlockByNumber(index).isVisible()
        )

    def _visible_block_position(self, visible_row: int) -> int:
        """Clamp a shared visual-row position for the editor scrollbars."""

        last_visible = max(0, (self._scrollable_total_size() // ROW_BYTES) - 1)
        return min(max(0, visible_row), last_visible)

    def _folded_offset_text(self, row_index: int, column: str, text: str) -> str:
        """Project the first body offset onto a standalone collapsed label."""

        if text != "-":
            return text
        region = next(
            (
                item
                for item in self._label_fold_regions
                if item.label_row == row_index
                and item.label in self._collapsed_labels
            ),
            None,
        )
        if region is None:
            return text
        for index in range(region.first_hidden_row, region.last_hidden_row + 1):
            candidate = self._rows[index].offsets.get(column, "-")
            if candidate != "-":
                return candidate
        return text
