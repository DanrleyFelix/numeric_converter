from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4
import re

from PySide6.QtCore import QObject, QTimer

from src.core.binary_workbench.editor_consistency import (
    ChangeKind,
    ConsistencyBarrierResult,
    ConsistencyState,
    ConsistentEditorSnapshot,
    DerivedCategory,
    DerivedCopySnapshot,
    DirtyRange,
    EditorOwner,
    LineContentBatch,
)
from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.classification import (
    classify_line_change,
    declared_label,
    merge_dirty_ranges,
)
from src.core.binary_workbench.editor_consistency.constants import (
    OFFSET_BATCH_SIZE,
    VIEWPORT_MARGIN_LINES,
)
from src.core.binary_workbench.editor_consistency.distribution import (
    LineContributionIndex,
    RangeConsistencyIndex,
    incremental_offset_values,
)
from src.core.binary_workbench.codec_registry import binary_workbench_worker_codec_for
from src.core.binary_workbench.mips_r3000a.source_line_rows import labels_from_source_rows
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constant_groups.timing import (
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.consistency.projection import (
    apply_bytes_line_contents,
    apply_bytes_structure_splice,
    apply_full_projection,
    apply_line_contents,
    apply_offset_values,
    apply_requested_column_contents,
    apply_structure_splice,
)
from src.presentation.ui.components.binary_workbench.editor.consistency.workers import (
    DerivedCopyWorker,
    EditorConsistencyWorkerPool,
)


class EditorConsistencyCoordinator(QObject):
    """Prioritize immediate viewport consistency without global per-key work."""

    def __init__(self, grid) -> None:
        super().__init__(grid)
        self.grid = grid
        self.owner = EditorOwner("unbound", uuid4().hex, 0)
        self.source_revision = 0
        self.structural_revision = 0
        self.visual_generation = 0
        self.semantic_generation = 0
        self.visual_revision_applied = 0
        self.semantic_revision_applied = 0
        self.viewport_epoch = 0
        self._owner_states: dict[str, tuple[int, int, int, int, int, int]] = {}
        self._forgotten_owner_ids: set[str] = set()
        self.state = ConsistencyState.CLEAN
        self._model_rows: list[BinaryWorkbenchRowDTO] = []
        self._line_revisions: list[int] = []
        self._contributions = LineContributionIndex()
        self._dependency_index: dict[str, set[int]] = {}
        self._dirty_ranges: tuple[DirtyRange, ...] = ()
        self._dirty_from_line: int | None = None
        self._pending_first: int | None = None
        self._pending_last: int | None = None
        self._explicit_dirty_lines: set[int] = set()
        self._operation_depth = 0
        self._history_steps_before: int | None = None
        self._collector_scheduled = False
        self._viewport_restart_scheduled = False
        self._requested_viewport: DirtyRange | None = None
        self._requested_viewport_ranges: tuple[DirtyRange, ...] = ()
        self._recompute_viewport_on_commit = False
        self._last_viewport_origin = "initial"
        self._pending_bytes_content_batches: list[LineContentBatch] = []
        self._pending_symbol_lines: set[int] = set()
        self._range_consistency = RangeConsistencyIndex()
        self._symbol_consistency = RangeConsistencyIndex()
        self._bulk_symbols_pending = False
        self._copy_semantic_pending = False
        self._barrier_active = False
        self._visual_token: CancellationToken | None = None
        self._semantic_token: CancellationToken | None = None
        self._broad_copy_token: CancellationToken | None = None
        self._broad_copy_worker = None
        self._broad_copy_generation = 0
        self._pool = EditorConsistencyWorkerPool(self)
        self._viewport_timer = self._timer(
            BINARY_WORKBENCH_TIMING.CONSISTENCY_SCROLL_FRAME_MS,
            self._prioritize_coalesced_viewport,
        )
        self._bytes_content_timer = self._timer(0, self._flush_bytes_content_batch)
        grid.instructions.document().contentsChange.connect(self.collect_contents_change)
        grid.bytes.document().contentsChange.connect(
            lambda *_change: self._defer_eventual_for_user_input()
        )
        for editor in grid._popup_editors():
            editor.cursorPositionChanged.connect(self._defer_eventual_for_user_input)
            editor.selectionChanged.connect(self._defer_eventual_for_user_input)
        grid.scrollbar.valueChanged.connect(
            lambda _value: (
                self._defer_eventual_for_user_input(),
                self.prioritize_viewport("scrollbar"),
            )
        )

    def _timer(self, interval: int, callback) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer

    def _defer_eventual_for_user_input(self) -> None:
        """Restart idle deadlines and cancel only obsolete semantic CPU work."""

        if self.grid._updating:
            return
        if self._semantic_token is not None and not self._semantic_token.is_cancelled():
            self._semantic_token.cancel()
            self.semantic_generation += 1
            self.state &= ~ConsistencyState.RECALCULATING_SEMANTIC

    def enabled(self) -> bool:
        """Return whether this source grid can use incremental consistency.

        The user byte-shifting preference controls which structural edits are
        accepted; it must not disable proportional derivation for ordinary
        character edits in an existing row.
        """

        return not self.grid._virtual

    def has_pending_source_changes(self) -> bool:
        """Check unpublished edits without exporting or scanning the document."""

        return bool(
            self._pending_first is not None
            or self._collector_scheduled
            or self._operation_depth
            or self._explicit_dirty_lines
        )

    def offset_before_line(self, index: int) -> int:
        """Return the indexed logical offset without scanning neighboring rows."""

        return self.grid._source_rows_start_offset() + self._contributions.prefix_bytes(index)

    def emitted_bytes_between(self, first: int, last_exclusive: int) -> int:
        """Count emitted bytes in a selected range without visiting its rows."""

        start = max(0, first)
        end = max(start, last_exclusive)
        return (
            self._contributions.prefix_bytes(end)
            - self._contributions.prefix_bytes(start)
        )

    def supports_derived_updates(self) -> bool:
        """Return whether this static grid can refresh derived viewport data.

        Symbol projection is independent from the user's byte-shifting rule;
        coupling both states left Bytes and offsets stale in locked editors.
        """

        return not self.grid._virtual

    def activate_owner(self, tab_id: str, version_id: str) -> None:
        """Bind future work to a new tab/version activation epoch."""

        self.cancel_pending()
        if (
            self.owner.tab_id != "unbound"
            and self.owner.version_id not in self._forgotten_owner_ids
        ):
            self._owner_states[self.owner.version_id] = (
                self.source_revision,
                self.structural_revision,
                self.visual_generation,
                self.semantic_generation,
                self.visual_revision_applied,
                self.semantic_revision_applied,
            )
        epoch = self.owner.activation_epoch + 1
        self.owner = EditorOwner(tab_id, version_id, epoch)
        (
            self.source_revision,
            self.structural_revision,
            self.visual_generation,
            self.semantic_generation,
            self.visual_revision_applied,
            self.semantic_revision_applied,
        ) = self._owner_states.get(version_id, (0, 0, 0, 0, 0, 0))
        self._forgotten_owner_ids.discard(version_id)

    def forget_owner(self, version_id: str) -> None:
        """Discard the runtime consistency state of a deleted version."""

        self._owner_states.pop(version_id, None)
        self._forgotten_owner_ids.add(version_id)

    def reset(self, rows: list[BinaryWorkbenchRowDTO]) -> None:
        """Reset derived metadata after an authoritative context load."""

        self.cancel_pending()
        self._model_rows = list(rows)
        self._line_revisions = [self.source_revision] * len(rows)
        self._contributions = LineContributionIndex([_row_size(row) for row in rows])
        self._dependency_index = _dependency_index(rows)
        self._dirty_ranges = ()
        self._dirty_from_line = None
        self._range_consistency.reset(len(rows), self.structural_revision)
        self._symbol_consistency.reset(len(rows), self.source_revision)
        self._pending_symbol_lines.clear()
        self._bulk_symbols_pending = False
        self._copy_semantic_pending = False
        self._clear_collector()
        self.visual_revision_applied = self.structural_revision
        self.semantic_revision_applied = self.source_revision
        self.state = ConsistencyState.CLEAN

    def accept_synchronous_rows(self, rows: list[BinaryWorkbenchRowDTO]) -> None:
        """Adopt a complete Bytes-origin projection as the current revision."""

        previous_sizes = tuple(_row_size(row) for row in self._model_rows)
        current_sizes = tuple(_row_size(row) for row in rows)
        self.cancel_pending()
        self.source_revision += 1
        if previous_sizes != current_sizes:
            self.structural_revision += 1
        self._model_rows = list(rows)
        self._line_revisions = [self.source_revision] * len(rows)
        self._contributions = LineContributionIndex(current_sizes)
        self._dependency_index = _dependency_index(rows)
        self._dirty_ranges = ()
        self._dirty_from_line = None
        self._range_consistency.reset(len(rows), self.structural_revision)
        self._clear_collector()
        self.visual_revision_applied = self.structural_revision
        self.semantic_revision_applied = self.source_revision
        self._copy_semantic_pending = False
        self.state = ConsistencyState.CLEAN

    def accept_bytes_line(self, index: int, row: BinaryWorkbenchRowDTO) -> None:
        """Adopt and project one complete Bytes-origin row proportionally."""

        if not 0 <= index < len(self._model_rows):
            return
        previous = self._model_rows[index]
        previous_size = _row_size(previous)
        current_size = _row_size(row)
        self.cancel_pending()
        self.source_revision += 1
        self._model_rows[index] = row
        self._line_revisions[index] = self.source_revision
        self._contributions.splice(index, 1, [current_size])
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        self.grid._set_editor_line(
            self.grid.instructions,
            index,
            self.grid._display_instruction(row.instruction),
        )
        # Bytes is the authoritative editor for this transaction. Keep the
        # user's configured casing/grouping and patch only its derived peers.
        self.grid._set_editor_line(
            self.grid.decoded_text,
            index,
            self.grid._display_decoded_row(row),
        )
        self.grid._set_editor_line(
            self.grid.raw_instructions,
            index,
            self.grid._display_raw_row(row),
        )
        self._clear_collector()
        self._refresh_dependency_range(index, 1)
        if previous_size != current_size:
            self.structural_revision += 1
            self._range_consistency.invalidate_from(
                index,
                len(self._model_rows),
                self.structural_revision,
            )
            immediate_last = self._apply_immediate_offsets(index)
            if immediate_last < len(self._model_rows) - 1:
                self._dirty_ranges = merge_dirty_ranges(
                    self._dirty_ranges,
                    DirtyRange(index, len(self._model_rows) - 1),
                )
                self._dirty_from_line = index
                self._schedule_visual()
            else:
                self.visual_revision_applied = self.structural_revision
        else:
            self.visual_revision_applied = self.structural_revision
        if previous_size != current_size and index < len(self._model_rows) - 1:
            self._invalidate_semantic()
            self._schedule_semantic()
        else:
            self.semantic_revision_applied = self.source_revision
            self.state &= ~ConsistencyState.DIRTY_SEMANTIC
            self.state &= ~ConsistencyState.RECALCULATING_SEMANTIC
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self.grid._emit_selection_summary()
        self.grid._dirty_editor_kind = None

    def accept_bytes_lines(
        self,
        rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
    ) -> None:
        """Adopt many Bytes rows and commit the active viewport first."""

        changed = tuple(
            (index, row)
            for index, row in rows
            if 0 <= index < len(self._model_rows)
        )
        if not changed:
            return
        self.cancel_pending()
        self.source_revision += 1
        structural_from: int | None = None
        for index, row in changed:
            previous_size = _row_size(self._model_rows[index])
            current_size = _row_size(row)
            self._model_rows[index] = row
            self._line_revisions[index] = self.source_revision
            self._contributions.splice(index, 1, [current_size])
            if previous_size != current_size:
                structural_from = (
                    index
                    if structural_from is None
                    else min(structural_from, index)
                )
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        self._clear_collector()
        viewport = self._viewport_range()
        immediate, deferred = _viewport_first_rows(changed, viewport, OFFSET_BATCH_SIZE)
        apply_bytes_line_contents(self.grid, immediate)
        self._queue_bytes_content(deferred)
        for index, _row in changed:
            self._refresh_dependency_range(index, 1)
        if structural_from is not None:
            self.structural_revision += 1
            self._range_consistency.invalidate_from(
                structural_from,
                len(self._model_rows),
                self.structural_revision,
            )
            self._invalidate_visual()
            self._invalidate_semantic()
            immediate_last = self._apply_immediate_offsets(structural_from)
            if not (
                structural_from <= viewport.first
                and viewport.last <= immediate_last
            ):
                self._apply_offset_window(
                    viewport.first,
                    viewport.last - viewport.first + 1,
                )
            if immediate_last < len(self._model_rows) - 1:
                self._dirty_ranges = merge_dirty_ranges(
                    self._dirty_ranges,
                    DirtyRange(structural_from, len(self._model_rows) - 1),
                )
                self._dirty_from_line = structural_from
                self._schedule_visual()
            else:
                self.visual_revision_applied = self.structural_revision
            self._schedule_semantic()
        else:
            self.visual_revision_applied = self.structural_revision
            self.semantic_revision_applied = self.source_revision
            self.state &= ~ConsistencyState.DIRTY_SEMANTIC
            self.state &= ~ConsistencyState.RECALCULATING_SEMANTIC
        if not self._pending_bytes_content_batches:
            self._finish_bytes_content_projection()

    def _queue_bytes_content(
        self,
        rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
    ) -> None:
        for first in range(0, len(rows), OFFSET_BATCH_SIZE):
            self._pending_bytes_content_batches.append(LineContentBatch(
                self.owner,
                self.source_revision,
                self.visual_generation,
                rows[first : first + OFFSET_BATCH_SIZE],
            ))
        if self._pending_bytes_content_batches:
            self._bytes_content_timer.start()

    def _flush_bytes_content_batch(self) -> None:
        if not self._pending_bytes_content_batches:
            return
        batch = self._pending_bytes_content_batches.pop(0)
        if (
            batch.owner == self.owner
            and batch.source_revision == self.source_revision
            and batch.generation == self.visual_generation
        ):
            apply_bytes_line_contents(self.grid, batch.rows)
        if self._pending_bytes_content_batches:
            self._bytes_content_timer.start()
        else:
            self._finish_bytes_content_projection()

    def _finish_bytes_content_projection(self) -> None:
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self.grid._emit_selection_summary()
        self.grid._dirty_editor_kind = None

    def accept_bytes_structure_splice(
        self,
        first: int,
        removed: int,
        inserted: list[BinaryWorkbenchRowDTO],
    ) -> None:
        """Commit one Bytes-origin row splice and defer only its shifted suffix."""

        first = min(max(0, first), len(self._model_rows))
        removed = min(max(0, removed), len(self._model_rows) - first)
        self.cancel_pending()
        self.source_revision += 1
        self.structural_revision += 1
        self._model_rows[first : first + removed] = inserted
        self._line_revisions[first : first + removed] = [self.source_revision] * len(inserted)
        self._contributions.splice(
            first,
            removed,
            [_row_size(row) for row in inserted],
        )
        self._dependency_index = {}
        self._range_consistency.invalidate_from(
            first,
            len(self._model_rows),
            self.structural_revision,
        )
        self._invalidate_visual()
        self._invalidate_semantic()
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        apply_bytes_structure_splice(self.grid, first, removed, inserted)
        immediate_last = self._apply_immediate_offsets(first)
        viewport = self._viewport_range()
        if not (first <= viewport.first and viewport.last <= immediate_last):
            self._apply_offset_window(
                viewport.first,
                viewport.last - viewport.first + 1,
            )
        if immediate_last < len(self._model_rows) - 1:
            self._dirty_ranges = merge_dirty_ranges(
                self._dirty_ranges,
                DirtyRange(first, len(self._model_rows) - 1),
            )
            self._dirty_from_line = first
            self._schedule_visual()
        else:
            self._dirty_ranges = ()
            self._dirty_from_line = None
            self.visual_revision_applied = self.structural_revision
            self.state &= ~ConsistencyState.DIRTY_VISUAL
            self.state &= ~ConsistencyState.RECALCULATING_VISUAL
        self._schedule_semantic()
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self.grid._emit_selection_summary()
        self.grid._dirty_editor_kind = None

    def begin_edit_operation(self, _kind: str = "edit") -> None:
        """Begin one explicit multi-signal logical edit operation."""

        self._operation_depth += 1

    def end_edit_operation(self) -> None:
        """Close an explicit operation and flush its one aggregated region."""

        self._operation_depth = max(0, self._operation_depth - 1)
        if self._operation_depth == 0 and self._pending_first is not None:
            self.flush_collected_changes()
        elif self._operation_depth == 0:
            self._history_steps_before = None

    def begin_user_event(self, kind: str = "key") -> None:
        """Aggregate all document signals emitted by one Qt input event."""

        if self._operation_depth == 0:
            self._history_steps_before = (
                self.grid.instructions.document().availableUndoSteps()
            )
            self.begin_edit_operation(kind)
            QTimer.singleShot(0, self.end_edit_operation)

    def collect_contents_change(self, position: int, removed: int, added: int) -> None:
        """Record only the approximate block range changed by QTextDocument."""

        if self.grid._updating or self._barrier_active or not self.enabled():
            return
        self._defer_eventual_for_user_input()
        document = self.grid.instructions.document()
        first = max(0, document.findBlock(max(0, position)).blockNumber())
        end_position = max(0, position + max(0, added) - 1)
        last_block = document.findBlock(end_position)
        last = first if not last_block.isValid() else max(first, last_block.blockNumber())
        self._pending_first = first if self._pending_first is None else min(self._pending_first, first)
        self._pending_last = last if self._pending_last is None else max(self._pending_last, last)
        if not self._collector_scheduled and self._operation_depth == 0:
            self._collector_scheduled = True
            QTimer.singleShot(0, self.flush_collected_changes)

    def register_source_edit_ranges(
        self,
        ranges: list[tuple[int, int]],
    ) -> None:
        """Capture exact Assembly blocks before one native edit mutates positions."""

        document = self.grid.instructions.document()
        for start, end in ranges:
            first_block = document.findBlock(max(0, start))
            last_position = max(start, end - 1)
            last_block = document.findBlock(max(0, last_position))
            if not first_block.isValid():
                continue
            first = first_block.blockNumber()
            last = first if not last_block.isValid() else last_block.blockNumber()
            self._explicit_dirty_lines.update(range(first, last + 1))

    def note_text_changed(self) -> None:
        """Mark the authoritative editor dirty without reading its full text."""

        self.grid._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION)
        self.grid._dirty_editor_kind = BINARY_WORKBENCH_TEXT.INSTRUCTION
        block = self.grid.instructions.textCursor().block()
        if block.isValid():
            self.grid._preview_label_fold_marker(block.blockNumber(), block.text())

    def flush_collected_changes(self) -> None:
        """Classify and apply one coalesced source edit."""

        if self._operation_depth or self._pending_first is None or not self.enabled():
            return
        first, last = self._pending_first, self._pending_last or self._pending_first
        explicit_lines = tuple(sorted(self._explicit_dirty_lines))
        history_steps_before = self._history_steps_before
        self._history_steps_before = None
        self._clear_collector()
        self.source_revision += 1
        # This signal now means "one coalesced Assembly operation committed".
        # It is deliberately absent from QTextDocument.textChanged; the
        # autosave scheduler only snapshots after its quiet/rate-limit timers.
        self.grid.assemblyTextChanged.emit()
        old_count = len(self._model_rows)
        new_count = self.grid.instructions.document().blockCount()
        if self._bulk_symbols_pending:
            self._symbol_consistency.invalidate_from(
                0,
                new_count,
                self.source_revision,
            )
        delta = new_count - old_count
        if delta == 0 and len(explicit_lines) > 1:
            self._apply_exact_source_lines(explicit_lines)
            return
        new_span = max(1, last - first + 1, delta + 1)
        new_span = min(new_span, max(0, new_count - first))
        old_span = min(max(0, new_span - delta), max(0, old_count - first))
        lines = self._block_lines(first, new_span)
        rows = None
        if delta == 0 and old_span == 1 and new_span == 1:
            single = self.grid._single_instruction_row(first, lines[0])
            rows = None if single is None else [single]
        if rows is None:
            rows = self._derive_lines(first, lines)
        if rows is None or len(rows) != len(lines):
            rows = [BinaryWorkbenchRowDTO({}, line, "") for line in lines]
        if delta == 0 and old_span == new_span:
            rows = self._preserve_locked_line_contributions(first, rows)
        if delta == 0 and old_span == 1 and new_span == 1:
            if self._apply_single_line(first, rows[0]):
                return
        previous_sizes = [
            _row_size(row)
            for row in self._model_rows[first : first + old_span]
        ]
        current_sizes = [_row_size(row) for row in rows]
        label_changed = self._labels_changed(first, old_span, rows)
        fold_structure_changed = (
            label_changed
            or self._directive_folding_changed(first, old_span, rows)
        )
        previous_label_names = tuple(
            declared_label(row.instruction)
            for row in self._model_rows[first : first + old_span]
            if declared_label(row.instruction)
        )
        structural = delta != 0 or previous_sizes != current_sizes
        kind = (
            ChangeKind.STRUCTURAL
            if structural
            else classify_line_change(
                sum(previous_sizes),
                sum(current_sizes),
                label_changed=label_changed,
            ).kind
        )
        if kind != ChangeKind.STRUCTURAL and old_span == new_span:
            self._apply_local_range(first, rows, label_changed)
            return
        self._model_rows[first : first + old_span] = rows
        self._line_revisions[first : first + old_span] = [self.source_revision] * len(rows)
        self._contributions.splice(first, old_span, current_sizes)
        if label_changed:
            rows = self._apply_structural_label_delta(
                first,
                previous_label_names,
                lines,
                rows,
            )
            current_sizes = [_row_size(row) for row in rows]
        self.structural_revision += 1
        self._range_consistency.invalidate_from(
            first,
            len(self._model_rows),
            self.structural_revision,
        )
        self._invalidate_visual()
        self._invalidate_semantic()
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        if delta:
            apply_structure_splice(
                self.grid,
                first,
                old_span,
                list(rows),
                refresh_folding=fold_structure_changed,
            )
            self.grid.instructions.remember_structural_undo_cursor(
                first,
                0,
                requires_byte_shift=(
                    delta < 0 and sum(previous_sizes) != sum(current_sizes)
                ),
                undo_steps_before=history_steps_before,
            )
        elif rows:
            apply_line_contents(
                self.grid,
                tuple((first + index, row) for index, row in enumerate(rows)),
            )
            if label_changed:
                self.grid._refresh_label_folding()
        immediate_last = self._apply_immediate_offsets(first)
        self._ensure_viewport_offsets_projected(first, immediate_last)
        self._refresh_edited_viewport_projection()
        has_pending_visual = bool(self._dirty_ranges)
        needs_deferred_visual = (
            has_pending_visual or immediate_last < len(self._model_rows) - 1
        )
        if needs_deferred_visual:
            self._dirty_ranges = merge_dirty_ranges(
                self._dirty_ranges,
                DirtyRange(first, max(first, len(self._model_rows) - 1)),
            )
            self._dirty_from_line = (
                first if self._dirty_from_line is None else min(first, self._dirty_from_line)
            )
            self._schedule_visual()
        else:
            self._dirty_ranges = ()
            self._dirty_from_line = None
            self.visual_revision_applied = self.structural_revision
            self.state &= ~ConsistencyState.DIRTY_VISUAL
            self.state &= ~ConsistencyState.RECALCULATING_VISUAL
            # The immediate bounded projection is the complete visual commit
            # for short documents.  Without this notification, the editors
            # show the new rows while the owning tab keeps its previous model.
            self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
            self.grid._dirty_editor_kind = None
        self._schedule_semantic()

    def _apply_exact_source_lines(self, indices: tuple[int, ...]) -> None:
        """Project non-contiguous Assembly edits without rebuilding their span."""

        changed: list[tuple[int, BinaryWorkbenchRowDTO]] = []
        structural_from: int | None = None
        labels_changed = False
        for index in indices:
            if not 0 <= index < len(self._model_rows):
                continue
            block = self.grid.instructions.document().findBlockByNumber(index)
            if not block.isValid():
                continue
            previous = self._model_rows[index]
            rebuilt = self._derive_lines(index, [block.text()])
            row = (
                rebuilt[0]
                if rebuilt and len(rebuilt) == 1
                else BinaryWorkbenchRowDTO({}, block.text(), "")
            )
            row = self._preserve_locked_line_contributions(index, [row])[0]
            previous_size = _row_size(previous)
            current_size = _row_size(row)
            labels_changed = labels_changed or (
                declared_label(previous.instruction)
                != declared_label(row.instruction)
            )
            self._model_rows[index] = row
            self._line_revisions[index] = self.source_revision
            self._contributions.splice(index, 1, [current_size])
            self._refresh_dependency_range(index, 1)
            changed.append((index, row))
            if previous_size != current_size:
                structural_from = (
                    index
                    if structural_from is None
                    else min(structural_from, index)
                )
        if not changed:
            return
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        apply_line_contents(self.grid, tuple(changed))
        self._refresh_edited_viewport_projection()
        if labels_changed:
            self.grid._set_editing_labels(labels_from_source_rows(self._model_rows))
            self.grid._refresh_label_folding()
        if structural_from is not None:
            self.structural_revision += 1
            self._range_consistency.invalidate_from(
                structural_from,
                len(self._model_rows),
                self.structural_revision,
            )
            self._invalidate_visual()
            immediate_last = self._apply_immediate_offsets(structural_from)
            viewport = self._viewport_range()
            if not (
                structural_from <= viewport.first
                and viewport.last <= immediate_last
            ):
                self._apply_offset_window(
                    viewport.first,
                    viewport.last - viewport.first + 1,
                )
            if immediate_last < len(self._model_rows) - 1:
                self._dirty_ranges = merge_dirty_ranges(
                    self._dirty_ranges,
                    DirtyRange(structural_from, len(self._model_rows) - 1),
                )
                self._dirty_from_line = structural_from
                self._schedule_visual()
        else:
            self.visual_revision_applied = self.structural_revision
        if structural_from is not None or labels_changed:
            self._invalidate_semantic()
            self._schedule_semantic()
        else:
            self.semantic_revision_applied = self.source_revision
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self.grid._dirty_editor_kind = None

    def _refresh_edited_viewport_projection(self) -> None:
        """Commit pasted visible rows and formatting without a global rebuild."""

        for viewport in self._viewport_ranges():
            first = max(0, viewport.first)
            last = min(len(self._model_rows) - 1, viewport.last)
            if first > last:
                continue
            apply_line_contents(
                self.grid,
                tuple(
                    (index, self._model_rows[index])
                    for index in range(first, last + 1)
                ),
            )
            self.grid._refresh_highlighter_projection((first, last))

    def _apply_immediate_offsets(self, first: int) -> int:
        """Update one model batch but paint only the edited row and viewport."""

        values = incremental_offset_values(
            self._contributions.snapshot(),
            first,
            OFFSET_BATCH_SIZE,
            tuple(self.grid._columns or [BINARY_WORKBENCH_TEXT.FILE]),
            self.grid._offset_base_text(),
        )
        if not values:
            return first - 1
        for index, offsets in values:
            row = self._model_rows[index]
            self._model_rows[index] = BinaryWorkbenchRowDTO(
                offsets,
                row.instruction,
                row.bytes_text,
                row.original_instruction,
                row.original_bytes_text,
            )
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        viewport = self._viewport_range()
        priority = tuple(
            item
            for item in values
            if item[0] == first or viewport.first <= item[0] <= viewport.last
        )
        apply_offset_values(self.grid, priority)
        self._range_consistency.mark(
            tuple(index for index, _offsets in priority),
            self.structural_revision,
        )
        return values[-1][0]

    def _apply_offset_window(
        self,
        first: int,
        count: int,
    ) -> tuple[tuple[int, dict[str, str]], ...]:
        """Project one bounded offset window from the indexed prefix base."""

        values = incremental_offset_values(
            self._contributions.snapshot(),
            first,
            count,
            tuple(self.grid._columns or [BINARY_WORKBENCH_TEXT.FILE]),
            self.grid._offset_base_text(),
        )
        if not values:
            return ()
        for index, offsets in values:
            row = self._model_rows[index]
            self._model_rows[index] = BinaryWorkbenchRowDTO(
                offsets,
                row.instruction,
                row.bytes_text,
                row.original_instruction,
                row.original_bytes_text,
            )
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        apply_offset_values(self.grid, values)
        self._range_consistency.mark(
            tuple(index for index, _offsets in values),
            self.structural_revision,
        )
        return values

    def _ensure_viewport_offsets_projected(
        self,
        immediate_first: int,
        immediate_last: int,
    ) -> None:
        """Synchronously repair a viewport outside the first offset batch."""

        viewport = self._viewport_range()
        if (
            immediate_first <= viewport.first
            and viewport.last <= immediate_last
        ):
            return
        self._apply_offset_window(
            viewport.first,
            viewport.last - viewport.first + 1,
        )

    def _apply_structural_label_delta(
        self,
        first: int,
        previous_label_names: tuple[str, ...],
        lines: list[str],
        rows: list[BinaryWorkbenchRowDTO],
    ) -> list[BinaryWorkbenchRowDTO]:
        """Publish edited labels immediately without rebuilding global semantics."""

        previous_names = {name.casefold() for name in previous_label_names}
        current_names = {
            declared_label(row.instruction).casefold()
            for row in rows
            if declared_label(row.instruction)
        }
        labels = {
            name: value
            for name, value in self.grid._labels.items()
            if name.casefold() not in previous_names - current_names
        }
        for local, row in enumerate(rows):
            name = declared_label(row.instruction)
            if name:
                labels[name] = (
                    f"0x{self._contributions.prefix_bytes(first + local):08X}"
                )
        block_range = (first, first + len(rows))
        if len(rows) > OFFSET_BATCH_SIZE:
            viewport = self._viewport_range()
            block_range = (viewport.first, viewport.last)
        self.grid._set_editing_labels(labels, block_range)
        self._refresh_dependency_range(first, len(rows))
        return rows

    def _apply_single_line(self, index: int, row: BinaryWorkbenchRowDTO) -> bool:
        previous = self._model_rows[index]
        label_changed = declared_label(previous.instruction) != declared_label(row.instruction)
        change = classify_line_change(
            _row_size(previous),
            _row_size(row),
            label_changed=label_changed,
        )
        if change.kind == ChangeKind.STRUCTURAL:
            return False
        self._apply_local_range(index, [row], label_changed)
        return True

    def _apply_local_range(self, first: int, rows: list[BinaryWorkbenchRowDTO], label_changed: bool) -> None:
        semantic_pending = bool(
            self.state
            & (ConsistencyState.DIRTY_SEMANTIC | ConsistencyState.RECALCULATING_SEMANTIC)
        )
        previous_labels = dict(self.grid._labels)
        self._model_rows[first : first + len(rows)] = rows
        self._line_revisions[first : first + len(rows)] = [self.source_revision] * len(rows)
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        batch = LineContentBatch(
            self.owner,
            self.source_revision,
            self.visual_generation,
            tuple((first + index, row) for index, row in enumerate(rows)),
        )
        self._apply_line_content_batch(batch)
        if label_changed:
            labels = labels_from_source_rows(self._model_rows)
            self.grid._set_editing_labels(labels, (first, first + len(rows)))
            self.grid._refresh_label_folding()
            changed_names = {
                name.casefold()
                for name in {*previous_labels, *labels}
                if previous_labels.get(name) != labels.get(name)
            }
            dependants = sorted(
                {
                    index
                    for name in changed_names
                    for index in self._dependency_index.get(name, set())
                }
            )
            dependent_rows: list[tuple[int, BinaryWorkbenchRowDTO]] = []
            for index in dependants:
                if not 0 <= index < len(self._model_rows):
                    continue
                rebuilt = self._derive_lines(index, [self._model_rows[index].instruction])
                if not rebuilt:
                    continue
                self._model_rows[index] = rebuilt[0]
                dependent_rows.append((index, rebuilt[0]))
            if dependent_rows:
                self.grid._rows = list(self._model_rows)
                self.grid._all_rows = list(self._model_rows)
                dependent_batch = LineContentBatch(
                    self.owner,
                    self.source_revision,
                    self.visual_generation,
                    tuple(dependent_rows),
                )
                self._apply_line_content_batch(dependent_batch)
            self._invalidate_semantic()
            self._schedule_semantic()
        elif semantic_pending:
            # Preserve a semantic rebuild already required by an earlier structural edit.
            self._invalidate_semantic()
            self._schedule_semantic()
        self._refresh_dependency_range(first, len(rows))
        self.grid._emit_rows_changed(deferred=True)
        self.grid._dirty_editor_kind = None

    def _preserve_locked_line_contributions(
        self,
        first: int,
        rows: list[BinaryWorkbenchRowDTO],
    ) -> list[BinaryWorkbenchRowDTO]:
        """Keep existing bytes while a locked source row is temporarily invalid.

        This is the proportional replacement for the legacy whole-document
        reconciliation that previously ran after every Backspace.
        """

        if self.grid._edit_rules.allow_byte_shift:
            return rows
        preserved: list[BinaryWorkbenchRowDTO] = []
        for relative, row in enumerate(rows):
            index = first + relative
            if not 0 <= index < len(self._model_rows):
                preserved.append(row)
                continue
            previous = self._model_rows[index]
            if not previous.bytes_text or row.bytes_text:
                preserved.append(row)
                continue
            preserved.append(BinaryWorkbenchRowDTO(
                previous.offsets,
                row.instruction,
                previous.bytes_text,
                previous.original_instruction,
                previous.original_bytes_text,
            ))
        return preserved

    def ensure_broad_copy_consistent(
        self,
        first_line: int | None = None,
        last_line: int | None = None,
    ) -> bool:
        """Report whether a broad copy can use its current projection.

        The former implementation rebuilt every derived QTextDocument on the
        GUI thread before Ctrl+C.  The check remains constant-time, while stale
        copy data is now prepared separately by :meth:`request_broad_copy`.
        """

        self.flush_collected_changes()
        # Clipboard text needs a current Assembly/control-flow projection, not
        # pending paint, hazard or catalog-wide highlight maintenance.  Symbol
        # fidelity remains the explicit F1 barrier; importing a large catalog
        # must not turn Ctrl+C into an unrelated whole-document calculation.
        if self._copy_semantic_pending:
            return False
        if first_line is None or last_line is None or not self._model_rows:
            return True
        first = max(0, min(first_line, len(self._model_rows) - 1))
        last = max(first, min(last_line, len(self._model_rows) - 1))
        required = (
            DerivedCategory.ASSEMBLY
            | DerivedCategory.BYTES
            | DerivedCategory.RAW
            | DerivedCategory.SYMBOLS
            | DerivedCategory.BRANCHES
        )
        return not self._pending_categories(DirtyRange(first, last)) & required

    def request_broad_copy(
        self,
        first_line: int,
        last_line: int,
        callback: Callable[[int, tuple[BinaryWorkbenchRowDTO, ...]], None],
    ) -> bool:
        """Prepare only a stale copied range without reprojecting the UI.

        ``True`` tells the caller to copy its current document immediately.
        Otherwise copied lines are assembled with user-request priority and
        delivered to ``callback`` only if their source revision survives.
        """

        if self.ensure_broad_copy_consistent(first_line, last_line):
            return True
        # An explicit clipboard request outranks eventual semantic maintenance.
        # The active worker exits cooperatively at its next bounded check.
        if self._semantic_token is not None:
            self._semantic_token.cancel()
        self._broad_copy_generation += 1
        generation = self._broad_copy_generation
        if self._broad_copy_token is not None:
            self._broad_copy_token.cancel()
        self._broad_copy_token = CancellationToken()
        snapshot = DerivedCopySnapshot(
            self.owner,
            self.source_revision,
            generation,
            binary_workbench_worker_codec_for(self.grid._codec.display_name),
            tuple(row.instruction for row in self._model_rows),
            first_line,
            last_line,
            self._contributions.snapshot(),
            tuple(self.grid._columns or [BINARY_WORKBENCH_TEXT.FILE]),
            self.grid._offset_base_text(),
            dict(self.grid._variables),
            dict(self.grid._equates),
            self.grid._jump_reference_offset,
        )
        worker = DerivedCopyWorker(snapshot, self._broad_copy_token)
        worker.signals.semanticReady.connect(
            lambda result: self._complete_broad_copy(result, generation, callback)
        )
        worker.signals.failed.connect(self._broad_copy_failed)
        self._broad_copy_worker = worker
        self.grid.commandStatusRequested.emit(BINARY_WORKBENCH_TEXT.STATUS_COPY_PREPARING)
        self._pool.start_immediate(worker)
        return False

    def _complete_broad_copy(self, result, generation: int, callback) -> None:
        """Deliver prepared copy rows only for the still-current snapshot."""

        if (
            result.owner != self.owner
            or result.source_revision != self.source_revision
            or result.generation != generation
            or generation != self._broad_copy_generation
        ):
            self._broad_copy_worker = None
            self._broad_copy_token = None
            self.grid.commandWarningRequested.emit(
                BINARY_WORKBENCH_TEXT.STATUS_COPY_CANCELLED
            )
            return
        try:
            callback(result.first_line, tuple(result.rows))
        except Exception as error:
            self.grid.commandWarningRequested.emit(str(error))
        else:
            self.grid.commandStatusRequested.emit(BINARY_WORKBENCH_TEXT.STATUS_COPY_READY)
        finally:
            self._broad_copy_worker = None
            self._broad_copy_token = None

    def _broad_copy_failed(self, message: str) -> None:
        """Surface copy preparation errors without mutating editor state."""

        self._broad_copy_worker = None
        self._broad_copy_token = None
        self.grid.commandWarningRequested.emit(message)

    def _schedule_visual(self) -> None:
        """Mark non-visible offsets stale without scheduling global propagation.

        The edited line and current viewport are projected synchronously by
        their callers. Other ranges stay revision-marked and are repaired only
        when navigation requests them or an explicit consistency barrier runs.
        """

        self.state |= ConsistencyState.DIRTY_VISUAL

    def _schedule_semantic(self, *, copy_required: bool = True) -> None:
        """Mark global semantics stale without launching idle CPU work."""

        if copy_required:
            self._copy_semantic_pending = True
        self.state |= ConsistencyState.DIRTY_SEMANTIC

    def ensure_consistent(self, _reason: str) -> ConsistencyBarrierResult:
        """Synchronously derive and project one complete atomic editor revision."""

        if self._barrier_active:
            return ConsistencyBarrierResult(False, error="A consistency barrier is already running.")
        self.flush_collected_changes()
        self._barrier_active = True
        previous_state = self.state
        self.cancel_pending()
        self.state = ConsistencyState.RECALCULATING_IMMEDIATE
        editor = self.grid.instructions
        was_read_only = editor.isReadOnly()
        editor.setReadOnly(True)
        previous_rows = list(self._model_rows)
        previous_grid_rows = self.grid._rows
        previous_all_rows = self.grid._all_rows
        previous_labels = dict(self.grid._labels)
        previous_structural_revision = self.structural_revision
        previous_applied_revisions = (
            self.visual_revision_applied,
            self.semantic_revision_applied,
        )
        previous_copy_pending = self._copy_semantic_pending
        try:
            lines = self._document_lines()
            rows = self.grid._instruction_rows_from_lines(lines)
            if rows is None or len(rows) != len(lines):
                raise ValueError("Unable to derive the current Assembly source.")
            labels = labels_from_source_rows(rows)
            previous_sizes = tuple(_row_size(row) for row in self._model_rows)
            current_sizes = tuple(_row_size(row) for row in rows)
            self.grid._rows = list(rows)
            self.grid._all_rows = list(rows)
            apply_full_projection(self.grid, list(rows))
            self.grid._set_editing_labels(labels)
            self.grid._refresh_instruction_hazards()
            if previous_sizes != current_sizes:
                self.structural_revision += 1
            self._model_rows = list(rows)
            self._line_revisions = [self.source_revision] * len(rows)
            self._contributions = LineContributionIndex(current_sizes)
            self._range_consistency.reset(len(rows), self.structural_revision)
            self._dependency_index = _dependency_index(rows)
            self._dirty_ranges = ()
            self._dirty_from_line = None
            self.visual_revision_applied = self.structural_revision
            self.semantic_revision_applied = self.source_revision
            self._copy_semantic_pending = False
            self.grid._emit_rows_changed(self.grid.export_rows())
            snapshot = ConsistentEditorSnapshot(
                self.owner,
                self.source_revision,
                self.structural_revision,
                tuple(rows),
                labels,
            )
            self.state = ConsistencyState.CLEAN
            self.grid._dirty_editor_kind = None
            return ConsistencyBarrierResult(True, snapshot)
        except Exception as error:
            self.structural_revision = previous_structural_revision
            (
                self.visual_revision_applied,
                self.semantic_revision_applied,
            ) = previous_applied_revisions
            self._model_rows = previous_rows
            self._copy_semantic_pending = previous_copy_pending
            self.grid._rows = previous_grid_rows
            self.grid._all_rows = previous_all_rows
            try:
                apply_full_projection(self.grid, previous_rows)
                self.grid._set_editing_labels(previous_labels)
            except Exception:
                pass
            self.state = previous_state | ConsistencyState.DIRTY_VISUAL | ConsistencyState.DIRTY_SEMANTIC
            return ConsistencyBarrierResult(False, error=str(error))
        finally:
            editor.setReadOnly(was_read_only)
            self._barrier_active = False

    def force_refresh(self) -> ConsistencyBarrierResult:
        """Use F1 as an explicit synchronous full-consistency boundary."""

        return self.ensure_consistent("f1")

    def prioritize_viewport(self, origin: str = "navigation") -> None:
        """Debounce typed stale work for the final scroll/navigation viewport."""

        ranges = self._viewport_ranges()
        if not ranges:
            return
        recompute = origin in {"scrollbar", "label-fold", "direct-navigation"}
        self._queue_viewport_ranges(ranges, origin, recompute)

    def request_viewport(
        self,
        first_line: int,
        last_line: int,
        origin: str = "navigation",
    ) -> None:
        """Prioritize one reached range regardless of its navigation source."""

        if not self._model_rows:
            return
        viewport = DirtyRange(
            max(0, first_line),
            min(len(self._model_rows) - 1, max(first_line, last_line)),
        )
        self._queue_viewport_ranges((viewport,), origin, False)

    def materialize_selected_projection(
        self,
        column: str,
        first_line: int,
        last_line: int,
    ) -> None:
        """Refresh only stale data requested by a settled line selection."""

        if not self._model_rows:
            return
        first = max(0, first_line)
        last = min(len(self._model_rows) - 1, max(first, last_line))
        if last - first + 1 > OFFSET_BATCH_SIZE:
            return
        viewport = DirtyRange(first, last)
        categories = self._pending_categories(viewport)
        relevant = {
            BINARY_WORKBENCH_TEXT.BYTES: (
                DerivedCategory.ASSEMBLY
                | DerivedCategory.BYTES
                | DerivedCategory.SYMBOLS
                | DerivedCategory.BRANCHES
            ),
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: (
                DerivedCategory.ASSEMBLY
                | DerivedCategory.RAW
                | DerivedCategory.SYMBOLS
                | DerivedCategory.BRANCHES
            ),
            BINARY_WORKBENCH_TEXT.DECODED_TEXT: (
                DerivedCategory.ASSEMBLY
                | DerivedCategory.BYTES
                | DerivedCategory.SYMBOLS
            ),
        }.get(column, DerivedCategory.NONE)
        if relevant == DerivedCategory.NONE or not categories & relevant:
            return
        source = [
            self.grid.instructions.document().findBlockByNumber(index).text()
            for index in range(first, last + 1)
        ]
        rebuilt = self._derive_lines(first, source)
        if rebuilt is None or len(rebuilt) != len(source):
            return
        indexed = tuple((first + offset, row) for offset, row in enumerate(rebuilt))
        apply_requested_column_contents(self.grid, column, indexed)

    def _queue_viewport_ranges(
        self,
        ranges: tuple[DirtyRange, ...],
        origin: str,
        recompute_on_commit: bool,
    ) -> None:
        """Coalesce one navigation while retaining folded visible source ranges."""

        categories = DerivedCategory.NONE
        for viewport in ranges:
            categories |= self._pending_categories(viewport)
        if categories == DerivedCategory.NONE and not recompute_on_commit:
            return
        self.viewport_epoch += 1
        self._last_viewport_origin = origin
        self._requested_viewport_ranges = ranges
        self._requested_viewport = DirtyRange(ranges[0].first, ranges[-1].last)
        self._recompute_viewport_on_commit = recompute_on_commit
        if (
            categories != DerivedCategory.NONE
            and self.state & ConsistencyState.RECALCULATING_VISUAL
            and self._visual_token is not None
        ):
            self._invalidate_visual()
            self.visual_generation += 1
        # Scrollbar drags collapse to one frame; direct navigations take the
        # same path and therefore also observe the current typed dirty flags.
        self._viewport_timer.start()

    def _pending_categories(self, viewport: DirtyRange) -> DerivedCategory:
        """Return only derived categories stale inside one requested range."""

        categories = DerivedCategory.NONE
        offsets_current = self._range_consistency.is_current(
            viewport.first,
            viewport.last,
            self.structural_revision,
        )
        if not offsets_current:
            categories |= DerivedCategory.OFFSETS
        content_pending = self._bytes_content_pending_in(viewport)
        if content_pending:
            categories |= (
                DerivedCategory.ASSEMBLY
                | DerivedCategory.BYTES
                | DerivedCategory.RAW
            )
        symbols_pending = any(
            viewport.first <= index <= viewport.last
            for index in self._pending_symbol_lines
        ) or (
            self._bulk_symbols_pending
            and not self._symbol_consistency.is_current(
                viewport.first,
                viewport.last,
                self.source_revision,
            )
        )
        if symbols_pending:
            categories |= DerivedCategory.SYMBOLS | DerivedCategory.HIGHLIGHT
        if self.state & (
            ConsistencyState.DIRTY_SEMANTIC
            | ConsistencyState.RECALCULATING_SEMANTIC
        ):
            categories |= (
                DerivedCategory.LABELS
                | DerivedCategory.BRANCHES
                | DerivedCategory.HAZARDS
            )
        return categories

    def prime_loaded_symbol_viewport(self) -> None:
        """Flag a loaded catalog cheaply and resolve its viewport first.

        The flag covers every row without parsing source text. This lets any
        later navigation request the reached viewport immediately while the
        semantic worker reconciles the complete document eventually.
        """

        sample = self._model_rows[:OFFSET_BATCH_SIZE]
        source_projection_pending = (
            any(row.instruction.strip() for row in sample)
            and not any(row.bytes_text.strip() for row in sample)
        )
        if not (
            self.grid._variables
            or self.grid._equates
            or source_projection_pending
        ):
            return
        # Do not scan the document merely to prove that a catalog is unused.
        # A viewport request is cheaper than the former O(document) probe and
        # becomes a no-op naturally when its bounded rows contain no Symbols.
        self.rederive_all_symbol_lines()

    def rederive_all_symbol_lines(self) -> None:
        """Flag a bulk catalog lazily and repair only viewport plus margin."""

        if not self._model_rows or not self.supports_derived_updates():
            return
        self.source_revision += 1
        self._invalidate_semantic()
        self._bulk_symbols_pending = True
        self._symbol_consistency.invalidate_from(
            0,
            len(self._model_rows),
            self.source_revision,
        )
        viewport = self._requested_viewport or self._viewport_range()
        self._requested_viewport = None
        self._requested_viewport_ranges = ()
        self._recompute_viewport_on_commit = False
        priority = DirtyRange(
            max(0, viewport.first - VIEWPORT_MARGIN_LINES),
            min(len(self._model_rows) - 1, viewport.last + VIEWPORT_MARGIN_LINES),
        )
        self._apply_pending_symbol_viewport(priority)
        self._schedule_semantic(copy_required=False)

    def rederive_symbol_lines(self, indices: Iterable[int]) -> None:
        """Rebuild only rows depending on changed Symbol definitions."""

        active = tuple(sorted({
            index for index in indices
            if 0 <= index < len(self._model_rows)
        }))
        if not active or not self.supports_derived_updates():
            return
        self.source_revision += 1
        self._invalidate_semantic()
        self._pending_symbol_lines.update(active)
        viewport = self._viewport_range()
        if len(active) <= VIEWPORT_MARGIN_LINES:
            # Small catalog edits are ordinary work and stay fully immediate.
            immediate = list(active)
        else:
            # A bulk import must never spend the UI budget assembling rows that
            # the user cannot currently see.  Remaining rows keep a typed
            # pending flag and are resolved by viewport demand or semantics.
            immediate = [
                index
                for index in active
                if viewport.first <= index <= viewport.last
            ][:OFFSET_BATCH_SIZE]
        changed, structural_from = self._derive_symbol_indices(immediate)
        self._pending_symbol_lines.difference_update(immediate)
        if structural_from is not None:
            self.structural_revision += 1
            self.visual_generation += 1
            self._invalidate_visual()
            self._range_consistency.invalidate_from(
                structural_from,
                len(self._model_rows),
                self.structural_revision,
            )
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        if changed:
            self._apply_line_content_batch(LineContentBatch(
                self.owner,
                self.source_revision,
                self.visual_generation,
                tuple(changed),
            ))
        if structural_from is not None:
            dirty = DirtyRange(structural_from, len(self._model_rows) - 1)
            self._dirty_ranges = merge_dirty_ranges(self._dirty_ranges, dirty)
            self._dirty_from_line = (
                structural_from
                if self._dirty_from_line is None
                else min(self._dirty_from_line, structural_from)
            )
            self._apply_offset_window(
                viewport.first,
                viewport.last - viewport.first + 1,
            )
            self._schedule_visual()
        if changed:
            self.grid._refresh_visible_instruction_hazards(
                viewport.first,
                viewport.last,
            )
            if structural_from is not None:
                self._refresh_symbol_labels(viewport)
        self._schedule_semantic(copy_required=False)
        if self._pending_symbol_lines or self._bulk_symbols_pending:
            self.prioritize_viewport()
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)

    def _prioritize_coalesced_viewport(self) -> None:
        """Commit stale visible rows before restarting deferred propagation."""

        ranges = (
            self._viewport_ranges()
            if self._recompute_viewport_on_commit
            else self._requested_viewport_ranges
        )
        if not ranges:
            ranges = (self._requested_viewport or self._viewport_range(),)
        self._requested_viewport = None
        self._requested_viewport_ranges = ()
        self._recompute_viewport_on_commit = False
        for viewport in ranges:
            categories = self._pending_categories(viewport)
            if categories == DerivedCategory.NONE:
                continue
            self._apply_pending_symbol_viewport(viewport)
            self._apply_pending_bytes_viewport(viewport)
            if not self._range_consistency.is_current(
                viewport.first,
                viewport.last,
                self.structural_revision,
            ):
                self._apply_offset_window(
                    viewport.first,
                    viewport.last - viewport.first + 1,
                )
        self._viewport_restart_scheduled = False

    def _apply_pending_symbol_viewport(self, viewport: DirtyRange) -> None:
        """Resolve only stale Symbol rows that just entered the viewport."""

        requested = {
            index
            for index in self._pending_symbol_lines
            if viewport.first <= index <= viewport.last
        }
        if self._bulk_symbols_pending and not self._symbol_consistency.is_current(
            viewport.first,
            viewport.last,
            self.source_revision,
        ):
            requested.update(range(
                max(0, viewport.first),
                min(len(self._model_rows), viewport.last + 1),
            ))
        indices = sorted(requested)[:OFFSET_BATCH_SIZE]
        if not indices:
            return
        changed, structural_from = self._derive_symbol_indices(indices)
        self._pending_symbol_lines.difference_update(indices)
        if self._bulk_symbols_pending:
            self._symbol_consistency.mark(tuple(indices), self.source_revision)
        if structural_from is not None:
            self.structural_revision += 1
            self.visual_generation += 1
            self._invalidate_visual()
            self._range_consistency.invalidate_from(
                structural_from,
                len(self._model_rows),
                self.structural_revision,
            )
            self._dirty_ranges = merge_dirty_ranges(
                self._dirty_ranges,
                DirtyRange(structural_from, len(self._model_rows) - 1),
            )
            self._dirty_from_line = (
                structural_from
                if self._dirty_from_line is None
                else min(self._dirty_from_line, structural_from)
            )
        self.grid._rows = list(self._model_rows)
        self.grid._all_rows = list(self._model_rows)
        if changed:
            self._apply_line_content_batch(LineContentBatch(
                self.owner,
                self.source_revision,
                self.visual_generation,
                tuple(changed),
            ))
        if structural_from is not None:
            self._apply_offset_window(
                viewport.first,
                viewport.last - viewport.first + 1,
            )
            self._schedule_visual()
        if changed:
            self.grid._refresh_visible_instruction_hazards(
                viewport.first,
                viewport.last,
            )
            if structural_from is not None:
                self._refresh_symbol_labels(viewport)
            self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)

    def _bytes_content_pending_in(self, viewport: DirtyRange) -> bool:
        """Return whether a deferred Bytes batch intersects the viewport."""

        return any(
            batch.rows
            and batch.rows[0][0] <= viewport.last
            and batch.rows[-1][0] >= viewport.first
            for batch in self._pending_bytes_content_batches
        )

    def _apply_pending_bytes_viewport(self, viewport: DirtyRange) -> None:
        """Project deferred Bytes peers intersecting the visible source rows."""

        visible: list[tuple[int, BinaryWorkbenchRowDTO]] = []
        remaining: list[LineContentBatch] = []
        for batch in self._pending_bytes_content_batches:
            if (
                batch.owner != self.owner
                or batch.source_revision != self.source_revision
                or batch.generation != self.visual_generation
            ):
                continue
            if (
                not batch.rows
                or batch.rows[0][0] > viewport.last
                or batch.rows[-1][0] < viewport.first
            ):
                remaining.append(batch)
                continue
            deferred = tuple(
                item
                for item in batch.rows
                if not viewport.first <= item[0] <= viewport.last
            )
            visible.extend(
                item
                for item in batch.rows
                if viewport.first <= item[0] <= viewport.last
            )
            if deferred:
                remaining.append(LineContentBatch(
                    batch.owner,
                    batch.source_revision,
                    batch.generation,
                    deferred,
                ))
        self._pending_bytes_content_batches = remaining
        if visible:
            apply_bytes_line_contents(self.grid, tuple(visible))
        if not remaining:
            self._bytes_content_timer.stop()
            self._finish_bytes_content_projection()

    def cancel_pending(self) -> None:
        """Invalidate timers and cooperative workers without terminating threads."""

        self._viewport_timer.stop()
        self._bytes_content_timer.stop()
        self._pending_bytes_content_batches.clear()
        self._requested_viewport = None
        self._requested_viewport_ranges = ()
        self._recompute_viewport_on_commit = False
        self.visual_generation += 1
        self.semantic_generation += 1
        if self._visual_token is not None:
            self._visual_token.cancel()
        if self._semantic_token is not None:
            self._semantic_token.cancel()
        if self._broad_copy_token is not None:
            self._broad_copy_token.cancel()
            self._broad_copy_generation += 1
            self._broad_copy_worker = None
            self._broad_copy_token = None
        self._pool.clear()

    def suspend_eventual_work(self) -> tuple[bool, bool]:
        """Keep native modal dialogs responsive by pausing CPU-bound work."""

        visual_pending = bool(
            self._dirty_ranges
            or self.state & ConsistencyState.DIRTY_VISUAL
        )
        semantic_pending = bool(self.state & ConsistencyState.DIRTY_SEMANTIC)
        pending_bytes = list(self._pending_bytes_content_batches)
        self.cancel_pending()
        # Byte-to-Assembly projection was already accepted into the model.
        # Preserve its small UI commits so a cancelled prompt cannot lose them.
        self._pending_bytes_content_batches = pending_bytes
        return visual_pending, semantic_pending

    def resume_eventual_work(self, suspended: tuple[bool, bool]) -> None:
        """Restore only semantic maintenance after the modal interaction."""

        _visual_pending, semantic_pending = suspended
        if self._pending_bytes_content_batches:
            self._bytes_content_timer.start()
        if semantic_pending:
            self._schedule_semantic()

    def shutdown(self) -> None:
        """Release pending consistency work when its grid is destroyed."""

        self.cancel_pending()
        self._pool.shutdown()

    def _invalidate_visual(self) -> None:
        if self._visual_token is not None:
            self._visual_token.cancel()

    def _invalidate_semantic(self) -> None:
        self.semantic_generation += 1
        if self._semantic_token is not None:
            self._semantic_token.cancel()
        if (
            self._broad_copy_worker is not None
            and self._broad_copy_token is not None
            and not self._broad_copy_token.is_cancelled()
        ):
            self._broad_copy_token.cancel()
            self._broad_copy_generation += 1
            self._broad_copy_worker = None
            self._broad_copy_token = None
            self.grid.commandWarningRequested.emit(
                BINARY_WORKBENCH_TEXT.STATUS_COPY_CANCELLED
            )

    def _apply_line_content_batch(self, batch: LineContentBatch) -> bool:
        if (
            batch.owner != self.owner
            or batch.source_revision != self.source_revision
            or batch.generation != self.visual_generation
        ):
            return False
        apply_line_contents(self.grid, batch.rows)
        return True

    def _derive_lines(self, first: int, lines: list[str]) -> list[BinaryWorkbenchRowDTO] | None:
        rows = self.grid._codec.build_source_line_rows(
            lines,
            self.grid._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self.grid._offset_base_text(),
            self._contributions.prefix_bytes(first),
            self.grid._labels,
            self.grid._variables,
            self.grid._equates,
            False,
            self.grid._symbol_resolver,
        )
        return self.grid._validated_standard_jump_rows(rows, lines)

    def _derive_symbol_indices(
        self,
        indices: list[int],
    ) -> tuple[list[tuple[int, BinaryWorkbenchRowDTO]], int | None]:
        """Derive contiguous Symbol rows in bounded codec calls.

        Large Symbol imports commonly invalidate a whole viewport. Calling the
        assembler once per row multiplied setup work and blocked the UI even
        though the requested range was already bounded.
        """

        changed: list[tuple[int, BinaryWorkbenchRowDTO]] = []
        structural_from: int | None = None
        for first, last in _contiguous_index_ranges(indices):
            previous = self._model_rows[first : last + 1]
            rebuilt = self._derive_lines(
                first,
                [row.instruction for row in previous],
            )
            if rebuilt is None or len(rebuilt) != len(previous):
                continue
            previous_sizes = [_row_size(row) for row in previous]
            current_sizes = [_row_size(row) for row in rebuilt]
            self._model_rows[first : last + 1] = rebuilt
            self._line_revisions[first : last + 1] = [
                self.source_revision
            ] * len(rebuilt)
            self._contributions.splice(first, len(previous), current_sizes)
            changed.extend(
                (first + relative, row)
                for relative, row in enumerate(rebuilt)
            )
            for relative, (old_size, new_size) in enumerate(
                zip(previous_sizes, current_sizes)
            ):
                if old_size == new_size:
                    continue
                index = first + relative
                structural_from = (
                    index
                    if structural_from is None
                    else min(structural_from, index)
                )
        return changed, structural_from

    def _refresh_symbol_labels(self, viewport: DirtyRange) -> None:
        """Refresh visible label offsets without scanning the complete source."""

        labels = dict(self.grid._labels)
        previous_names = {name.casefold() for name in labels}
        for index in range(
            max(0, viewport.first),
            min(len(self._model_rows), viewport.last + 1),
        ):
            name = declared_label(self._model_rows[index].instruction)
            if name:
                labels[name] = f"0x{self._contributions.prefix_bytes(index):08X}"
        if labels == self.grid._labels:
            return
        declarations_changed = {
            name.casefold() for name in labels
        } != previous_names
        self.grid._set_editing_labels(
            labels,
            (viewport.first, viewport.last),
        )
        if declarations_changed:
            # Symbol values can move label addresses, but they cannot alter the
            # source-owned fold regions.  Rebuilding every region here caused
            # a visible pause on large catalogs.
            self.grid._refresh_label_folding()

    def _labels_changed(self, first: int, old_span: int, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        """Detect declaration changes, not an ordinary row-count difference."""

        before = [
            name
            for row in self._model_rows[first : first + old_span]
            if (name := declared_label(row.instruction))
        ]
        after = [
            name
            for row in rows
            if (name := declared_label(row.instruction))
        ]
        return before != after

    def _directive_folding_changed(
        self,
        first: int,
        old_span: int,
        rows: list[BinaryWorkbenchRowDTO],
    ) -> bool:
        """Detect edits that can change the leading directive fold group."""

        before = self._model_rows[first : first + old_span]
        if any(row.instruction.lstrip().startswith("*") for row in (*before, *rows)):
            return True
        region = self.grid._directive_fold_region
        return region is not None and first <= region.last_hidden_row

    def _block_lines(self, first: int, count: int) -> list[str]:
        document = self.grid.instructions.document()
        output: list[str] = []
        for index in range(first, first + count):
            block = document.findBlockByNumber(index)
            if block.isValid():
                output.append(block.text())
        return output

    def _document_lines(self) -> list[str]:
        document = self.grid.instructions.document()
        output: list[str] = []
        block = document.firstBlock()
        while block.isValid():
            output.append(block.text())
            block = block.next()
        return output

    def _viewport_range(self) -> DirtyRange:
        first = max(0, self.grid.instructions.firstVisibleBlock().blockNumber())
        return DirtyRange(first, min(len(self._model_rows) - 1, first + self.grid._visible_row_count()))

    def _viewport_ranges(self) -> tuple[DirtyRange, ...]:
        """Return exact visible source ranges when folding makes them disjoint."""

        if getattr(self.grid, "_last_fold_hidden_rows", None):
            ranges = self.grid._visible_source_ranges()
            if ranges:
                last_row = len(self._model_rows) - 1
                return tuple(
                    DirtyRange(max(0, first), min(last_row, last))
                    for first, last in ranges
                    if first <= last_row
                )
        return (self._viewport_range(),)

    def _clear_collector(self) -> None:
        self._pending_first = None
        self._pending_last = None
        self._explicit_dirty_lines.clear()
        self._collector_scheduled = False

    def _worker_failed(self, phase: str, message: str) -> None:
        if phase == "visual":
            self.state &= ~ConsistencyState.RECALCULATING_VISUAL
            self.state |= ConsistencyState.DIRTY_VISUAL
        else:
            self.state &= ~ConsistencyState.RECALCULATING_SEMANTIC
            self.state |= ConsistencyState.DIRTY_SEMANTIC
        self.grid.commandWarningRequested.emit(message)

    def _refresh_dependency_range(self, first: int, count: int) -> None:
        for indices in self._dependency_index.values():
            indices.difference_update(range(first, first + count))
        for index in range(first, min(len(self._model_rows), first + count)):
            symbol = _control_flow_symbol(self._model_rows[index].instruction)
            if symbol:
                self._dependency_index.setdefault(symbol, set()).add(index)


def _row_size(row: BinaryWorkbenchRowDTO) -> int:
    try:
        return len(bytes.fromhex(row.bytes_text.replace(" ", "")))
    except ValueError:
        return 0


def _contiguous_index_ranges(indices: list[int]) -> tuple[tuple[int, int], ...]:
    """Collapse sorted row indices into ranges for bounded batch derivation."""

    if not indices:
        return ()
    ordered = sorted(set(indices))
    ranges: list[tuple[int, int]] = []
    first = previous = ordered[0]
    for index in ordered[1:]:
        if index == previous + 1:
            previous = index
            continue
        ranges.append((first, previous))
        first = previous = index
    ranges.append((first, previous))
    return tuple(ranges)


def _viewport_first_rows(
    rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
    viewport: DirtyRange,
    limit: int,
) -> tuple[
    tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
    tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
]:
    """Return one immediate viewport batch and bounded deferred remainder."""

    visible = [item for item in rows if viewport.first <= item[0] <= viewport.last]
    visible_ids = {index for index, _row in visible}
    nearest = sorted(
        (item for item in rows if item[0] not in visible_ids),
        key=lambda item: min(
            abs(item[0] - viewport.first),
            abs(item[0] - viewport.last),
        ),
    )
    immediate = tuple([*visible, *nearest[: max(0, limit - len(visible))]])
    immediate_ids = {index for index, _row in immediate}
    deferred = tuple(item for item in rows if item[0] not in immediate_ids)
    return immediate, deferred


_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONTROL_FLOW = {
    "b",
    "beq",
    "bgez",
    "bgezal",
    "bgtz",
    "blez",
    "bltz",
    "bltzal",
    "bne",
    "j",
    "jal",
    "jump",
}


def _control_flow_symbol(text: str) -> str:
    code = text.split(";", 1)[0].split("#", 1)[0]
    if ":" in code:
        code = code.split(":", 1)[1]
    parts = code.replace(",", " ").split()
    if len(parts) < 2 or parts[0].casefold() not in _CONTROL_FLOW:
        return ""
    target = parts[-1].lstrip("&@_")
    return parts[-1].lstrip("&").casefold() if _SYMBOL.fullmatch(target) else ""


def _dependency_index(rows: list[BinaryWorkbenchRowDTO]) -> dict[str, set[int]]:
    output: dict[str, set[int]] = {}
    for index, row in enumerate(rows):
        symbol = _control_flow_symbol(row.instruction)
        if symbol:
            output.setdefault(symbol, set()).add(index)
    return output
