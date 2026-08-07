from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.directive_folding import debugger_directive_fold_region
from src.core.binary_workbench.editor_consistency.classification.service import (
    declared_label,
)
from src.core.binary_workbench.label_folding import LabelFoldRegion, label_fold_regions
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TIMING,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.consistency.projection import (
    apply_offset_values,
)
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
        self._refresh_fold_viewport()
        self._schedule_layout_refresh()

    def toggle_directive_fold(self) -> None:
        """Collapse or expand every leading debugger directive as a visual group."""

        if not self._label_folding_enabled or self._directive_fold_region is None:
            return
        anchor_row = self._scroll_anchor_source_row()
        self._directives_collapsed = not self._directives_collapsed
        self._apply_label_visibility(anchor_row)
        self._refresh_fold_viewport()
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
        self._refresh_fold_viewport()
        self._schedule_layout_refresh()
        return True

    def _refresh_fold_viewport(self) -> None:
        """Coalesce folding and refresh only the final revealed viewport.

        Qt computes visible blocks after the fold visibility mask is applied.
        Refreshing in the same event used the previous viewport and left newly
        exposed Raw/Bytes/Symbol formatting stale. A short generation-guarded
        delay avoids duplicate work when users fold several labels quickly.
        """

        generation = getattr(self, "_fold_viewport_generation", 0) + 1
        self._fold_viewport_generation = generation
        QTimer.singleShot(
            BINARY_WORKBENCH_TIMING.CONSISTENCY_FOLD_VIEWPORT_MS,
            lambda: self._commit_fold_viewport(generation),
        )

    def _commit_fold_viewport(self, generation: int) -> None:
        """Refresh the post-layout viewport if no newer fold superseded it."""

        if generation != getattr(self, "_fold_viewport_generation", 0):
            return
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None:
            coordinator.prioritize_viewport("label-fold")
        self._refresh_visible_highlighter_projection()

    def _refresh_label_folding(self, anchor_row: int | None = None) -> None:
        """Recalculate regions and apply one visibility mask to all columns."""

        previous_regions = self._label_fold_regions
        previously_collapsed = bool(self._collapsed_labels or self._directives_collapsed)
        regions = label_fold_regions(self._rows) if self._label_folding_enabled else []
        self._label_fold_regions = regions
        self._label_fold_regions_by_row = {
            region.label_row: region for region in regions
        }
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
        self._apply_label_visibility(
            anchor_row,
            refresh_offsets=previously_collapsed or bool(self._collapsed_labels),
            normalize_all=True,
        )

    def _preview_label_fold_marker(self, row: int, source: str) -> None:
        """Keep a cached fold marker attached during a local label rename."""

        if not self._label_folding_enabled:
            return
        current = self._label_fold_regions_by_row.get(row)
        if current is None:
            return
        name = declared_label(source)
        if name == current.label:
            return
        # Keep the old region until the coalesced structural commit removes it;
        # that commit needs the previous owner to expand inherited rows.
        if not name:
            return
        regions = list(self._label_fold_regions)
        replacement = LabelFoldRegion(
            name,
            current.label_row,
            current.first_hidden_row,
            current.last_hidden_row,
        )
        regions = [
            replacement if region.label_row == row else region
            for region in regions
        ]
        if current.label in self._collapsed_labels:
            self._collapsed_labels.remove(current.label)
            self._collapsed_labels.add(name)
        self._label_fold_regions = regions
        self._label_fold_regions_by_row = {
            region.label_row: region for region in regions
        }
        self.instructions.set_label_fold_regions({
            region.label_row: (
                region.label,
                region.label in self._collapsed_labels,
            )
            for region in regions
        })

    def _splice_cached_label_folding(
        self,
        first: int,
        removed: int,
        inserted: int,
    ) -> None:
        """Shift known fold coordinates after a non-label structural edit.

        Re-parsing every label after deleting one ordinary instruction made a
        single Backspace proportional to the complete file.  Label-changing
        edits still use the full refresh path.
        """

        delta = inserted - removed
        removed_end = first + removed
        regions: list[LabelFoldRegion] = []
        for region in self._label_fold_regions:
            if first <= region.label_row < removed_end:
                continue
            label_row = region.label_row + (delta if region.label_row >= removed_end else 0)
            last_hidden = region.last_hidden_row
            if first <= last_hidden:
                last_hidden = max(label_row, last_hidden + delta)
            first_hidden = label_row + 1
            if first_hidden <= last_hidden:
                regions.append(LabelFoldRegion(
                    region.label,
                    label_row,
                    first_hidden,
                    last_hidden,
                ))
        self._label_fold_regions = regions
        self._label_fold_regions_by_row = {
            region.label_row: region for region in regions
        }
        self.instructions.set_label_fold_regions({
            region.label_row: (
                region.label,
                region.label in self._collapsed_labels,
            )
            for region in regions
        })
        if self._collapsed_labels or self._directives_collapsed:
            self._apply_label_visibility(refresh_offsets=False)

    def _apply_label_visibility(
        self,
        anchor_row: int | None = None,
        *,
        refresh_offsets: bool = True,
        normalize_all: bool = False,
    ) -> None:
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
        previous_hidden = getattr(self, "_last_fold_hidden_rows", set())
        changed_rows = hidden_rows.symmetric_difference(previous_hidden)
        was_syncing = self._syncing_editor_scrollbars
        self._syncing_editor_scrollbars = True
        try:
            if refresh_offsets:
                self._refresh_changed_fold_offsets(changed_rows, normalize_all)
            if normalize_all or hidden_rows or getattr(self, "_last_fold_hidden_rows", set()):
                for editor in self._fold_editors():
                    self._apply_hidden_rows(
                        editor,
                        hidden_rows,
                        None if normalize_all else changed_rows,
                    )
            self._last_fold_hidden_rows = set(hidden_rows)
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
        """Return materialized editors whose blocks represent complete rows."""

        content = tuple(
            editor
            for name, editor in (
                (BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, self.raw_instructions),
                (BINARY_WORKBENCH_TEXT.BYTES, self.bytes),
                (BINARY_WORKBENCH_TEXT.DECODED_TEXT, self.decoded_text),
            )
            if name in self._configured_columns
        )
        return (
            *self._offset_editors.values(),
            *content,
            self.instructions,
        )

    def _refresh_changed_fold_offsets(
        self,
        changed_rows: set[int],
        normalize_all: bool,
    ) -> None:
        """Refresh only label headers whose folded body changed visibility."""

        if normalize_all:
            self._render_offsets()
            return
        affected = {
            region.label_row
            for region in self._label_fold_regions
            if not changed_rows.isdisjoint(
                range(region.first_hidden_row, region.last_hidden_row + 1)
            )
        }
        directive = self._directive_fold_region
        if directive is not None and not changed_rows.isdisjoint(
            range(directive.first_hidden_row, directive.last_hidden_row + 1)
        ):
            affected.add(directive.header_row)
        if affected:
            apply_offset_values(
                self,
                tuple((index, self._rows[index].offsets) for index in sorted(affected)),
            )

    def _apply_hidden_rows(
        self,
        editor,
        hidden_rows: set[int],
        changed_rows: set[int] | None = None,
    ) -> None:
        """Apply a fold delta without changing text or the undo document."""

        document = editor.document()
        changed = False
        if changed_rows is None:
            blocks = []
            block = document.firstBlock()
            while block.isValid():
                blocks.append(block)
                block = block.next()
        else:
            blocks = [
                document.findBlockByNumber(index)
                for index in sorted(changed_rows)
            ]
        dirty_start: int | None = None
        dirty_end = 0
        for block in blocks:
            if not block.isValid():
                continue
            visible = block.blockNumber() not in hidden_rows
            line_count = 1 if visible else 0
            if block.isVisible() != visible or block.lineCount() != line_count:
                block.setVisible(visible)
                block.setLineCount(line_count)
                changed = True
                dirty_start = (
                    block.position()
                    if dirty_start is None
                    else min(dirty_start, block.position())
                )
                dirty_end = max(dirty_end, block.position() + block.length())
        if changed:
            document.markContentsDirty(
                dirty_start or 0,
                max(1, dirty_end - (dirty_start or 0)),
            )
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
        visible_rows = max(0, len(self._rows) - len(self._last_fold_hidden_rows))
        return visible_rows * ROW_BYTES

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

        block = self.instructions.firstVisibleBlock()
        return block.blockNumber() if block.isValid() else None

    def _visible_position_for_source_row(self, source_row: int) -> int:
        """Map a source row to its ordinal among currently visible rows."""

        bounded = min(source_row, self.instructions.document().blockCount())
        hidden_before = sum(
            1 for index in self._last_fold_hidden_rows if index < bounded
        )
        return max(0, bounded - hidden_before)

    def _visible_block_position(self, visible_row: int) -> int:
        """Clamp a shared visual-row position for the editor scrollbars."""

        last_visible = max(0, (self._scrollable_total_size() // ROW_BYTES) - 1)
        return min(max(0, visible_row), last_visible)

    def _folded_offset_text(self, row_index: int, column: str, text: str) -> str:
        """Project the first body offset onto a standalone collapsed label."""

        if text != "-":
            return text
        region = self._label_fold_regions_by_row.get(row_index)
        if region is None or region.label not in self._collapsed_labels:
            return text
        for index in range(region.first_hidden_row, region.last_hidden_row + 1):
            candidate = self._rows[index].offsets.get(column, "-")
            if candidate != "-":
                return candidate
        return text
