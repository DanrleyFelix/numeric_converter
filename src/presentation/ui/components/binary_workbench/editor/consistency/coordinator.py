from __future__ import annotations

from uuid import uuid4
import re

from PySide6.QtCore import QObject, QTimer

from src.core.binary_workbench.editor_consistency import (
    ChangeKind,
    ConsistencyBarrierResult,
    ConsistencyState,
    ConsistentEditorSnapshot,
    DirtyRange,
    EditorOwner,
    LineContentBatch,
    SemanticSnapshot,
)
from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.classification import (
    classify_line_change,
    declared_label,
    merge_dirty_ranges,
)
from src.core.binary_workbench.editor_consistency.constants import OFFSET_BATCH_SIZE
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
    apply_semantic_projection,
    apply_structure_splice,
)
from src.presentation.ui.components.binary_workbench.editor.consistency.workers import (
    EditorConsistencyWorkerPool,
    OffsetDistributionWorker,
    SemanticWorker,
)


class EditorConsistencyCoordinator(QObject):
    """Coordinate proportional derived-state updates for one Assembly editor."""

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
        self._collector_scheduled = False
        self._viewport_restart_scheduled = False
        self._pending_bytes_content_batches: list[LineContentBatch] = []
        self._range_consistency = RangeConsistencyIndex()
        self._barrier_active = False
        self._visual_token: CancellationToken | None = None
        self._semantic_token: CancellationToken | None = None
        self._visual_worker = None
        self._semantic_worker = None
        self._pool = EditorConsistencyWorkerPool(self)
        self._visual_quiet = self._timer(BINARY_WORKBENCH_TIMING.CONSISTENCY_VISUAL_DEBOUNCE_MS, self._start_visual)
        self._visual_maximum = self._timer(BINARY_WORKBENCH_TIMING.CONSISTENCY_VISUAL_MAX_LATENCY_MS, self._start_visual)
        self._semantic_timer = self._timer(BINARY_WORKBENCH_TIMING.CONSISTENCY_SEMANTIC_DEBOUNCE_MS, self._start_semantic)
        self._viewport_timer = self._timer(
            BINARY_WORKBENCH_TIMING.CONSISTENCY_SCROLL_FRAME_MS,
            self._prioritize_coalesced_viewport,
        )
        self._bytes_content_timer = self._timer(0, self._flush_bytes_content_batch)
        grid.instructions.document().contentsChange.connect(self.collect_contents_change)
        grid.scrollbar.valueChanged.connect(lambda _value: self.prioritize_viewport())

    def _timer(self, interval: int, callback) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer

    def enabled(self) -> bool:
        """Return whether the active grid supports structural Assembly editing."""

        return not self.grid._virtual and self.grid._edit_rules.allow_byte_shift

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

    def begin_user_event(self, kind: str = "key") -> None:
        """Aggregate all document signals emitted by one Qt input event."""

        if self._operation_depth == 0:
            self.begin_edit_operation(kind)
            QTimer.singleShot(0, self.end_edit_operation)

    def collect_contents_change(self, position: int, removed: int, added: int) -> None:
        """Record only the approximate block range changed by QTextDocument."""

        if self.grid._updating or self._barrier_active or not self.enabled():
            return
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

    def flush_collected_changes(self) -> None:
        """Classify and apply one coalesced source edit."""

        if self._operation_depth or self._pending_first is None or not self.enabled():
            return
        first, last = self._pending_first, self._pending_last or self._pending_first
        explicit_lines = tuple(sorted(self._explicit_dirty_lines))
        self._clear_collector()
        self.source_revision += 1
        old_count = len(self._model_rows)
        new_count = self.grid.instructions.document().blockCount()
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
        if delta == 0 and old_span == 1 and new_span == 1:
            if self._apply_single_line(first, rows[0]):
                return
        previous_sizes = [_row_size(row) for row in self._model_rows[first : first + old_span]]
        current_sizes = [_row_size(row) for row in rows]
        label_changed = self._labels_changed(first, old_span, rows)
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
            apply_structure_splice(self.grid, first, old_span, list(rows))
        elif rows:
            apply_line_contents(
                self.grid,
                tuple((first + index, row) for index, row in enumerate(rows)),
            )
        immediate_last = self._apply_immediate_offsets(first)
        has_pending_visual = bool(self._dirty_ranges)
        needs_visual_worker = has_pending_visual or immediate_last < len(self._model_rows) - 1
        if needs_visual_worker:
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
        if labels_changed:
            self.grid._set_editing_labels(labels_from_source_rows(self._model_rows))
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
        active = rows
        sizes = [_row_size(row) for row in active]
        for _ in range(2):
            for local, row in enumerate(active):
                name = declared_label(row.instruction)
                if name:
                    labels[name] = f"0x{self._contributions.prefix_bytes(first + local):08X}"
            self.grid._set_editing_labels(labels, (first, first + len(active)))
            rebuilt = self._derive_lines(first, lines)
            if rebuilt is None or len(rebuilt) != len(active):
                break
            rebuilt_sizes = [_row_size(row) for row in rebuilt]
            self._model_rows[first : first + len(active)] = rebuilt
            self._contributions.splice(first, len(active), rebuilt_sizes)
            active = rebuilt
            if rebuilt_sizes == sizes:
                break
            sizes = rebuilt_sizes
        self._refresh_dependency_range(first, len(active))
        return active

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
        self.grid._refresh_jump_navigation()
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self.grid._dirty_editor_kind = None

    def _schedule_visual(self) -> None:
        self.state |= ConsistencyState.DIRTY_VISUAL
        self._visual_quiet.start()
        if not self._visual_maximum.isActive():
            self._visual_maximum.start()

    def _schedule_semantic(self) -> None:
        self.state |= ConsistencyState.DIRTY_SEMANTIC
        self._semantic_timer.start()

    def _start_visual(self) -> None:
        self._viewport_restart_scheduled = False
        if self._pending_bytes_content_batches:
            self._visual_quiet.start()
            return
        if not self._dirty_ranges or not self.enabled():
            return
        if (
            self.state & ConsistencyState.RECALCULATING_VISUAL
            and self._visual_token is not None
            and not self._visual_token.is_cancelled()
            and not self._visual_quiet.isActive()
            and not self._visual_maximum.isActive()
        ):
            return
        self._visual_quiet.stop()
        self._visual_maximum.stop()
        self.visual_generation += 1
        self._visual_token = CancellationToken()
        viewport = self._viewport_range()
        request = {
            "snapshot": self._contributions.snapshot(),
            "owner": self.owner,
            "structural_revision": self.structural_revision,
            "generation": self.visual_generation,
            "offset_names": tuple(self.grid._columns or [BINARY_WORKBENCH_TEXT.FILE]),
            "offset_bases": self.grid._offset_base_text(),
            "dirty_ranges": self._dirty_ranges,
            "dirty_from_line": self._dirty_from_line,
            "viewport": viewport,
        }
        worker = OffsetDistributionWorker(request, self._visual_token)
        worker.signals.offsetBatchReady.connect(self._apply_offset_batch)
        worker.signals.completed.connect(self._visual_completed)
        worker.signals.failed.connect(lambda message: self._worker_failed("visual", message))
        self._visual_worker = worker
        self.state |= ConsistencyState.RECALCULATING_VISUAL
        self._pool.start_visual(worker)

    def _apply_offset_batch(self, batch) -> None:
        if not self._valid_offset_batch(batch):
            return
        for index, offsets in batch.values:
            if index >= len(self._model_rows):
                continue
            row = self._model_rows[index]
            self._model_rows[index] = BinaryWorkbenchRowDTO(
                offsets,
                row.instruction,
                row.bytes_text,
                row.original_instruction,
                row.original_bytes_text,
            )
        try:
            self.grid._rows = list(self._model_rows)
            self.grid._all_rows = list(self._model_rows)
            apply_offset_values(self.grid, batch.values)
            self._range_consistency.mark(
                tuple(index for index, _offsets in batch.values),
                batch.structural_revision,
            )
            direct = tuple(
                (index, self._model_rows[index])
                for index, _ in batch.values
                if index < len(self._model_rows)
                and any(item.first <= index <= item.last for item in self._dirty_ranges)
            )
            if direct:
                apply_line_contents(self.grid, direct)
        except Exception as error:
            if self._visual_token is not None:
                self._visual_token.cancel()
            self.visual_generation += 1
            self.state &= ~ConsistencyState.RECALCULATING_VISUAL
            self._worker_failed("visual", str(error))

    def _visual_completed(self, envelope) -> None:
        owner, revision, generation = envelope
        if (owner, revision, generation) != (
            self.owner,
            self.structural_revision,
            self.visual_generation,
        ):
            return
        self._dirty_ranges = ()
        self._dirty_from_line = None
        self.state &= ~ConsistencyState.DIRTY_VISUAL
        self.state &= ~ConsistencyState.RECALCULATING_VISUAL
        self.visual_revision_applied = self.structural_revision
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self.grid._dirty_editor_kind = None

    def _start_semantic(self) -> None:
        if self._pending_bytes_content_batches:
            self._semantic_timer.start()
            return
        if not self.enabled():
            return
        self.semantic_generation += 1
        self._semantic_token = CancellationToken()
        snapshot = SemanticSnapshot(
            self.owner,
            self.source_revision,
            self.semantic_generation,
            self.grid._codec.display_name,
            binary_workbench_worker_codec_for(self.grid._codec.display_name),
            tuple(self._document_lines()),
            tuple(self.grid._columns or [BINARY_WORKBENCH_TEXT.FILE]),
            self.grid._offset_base_text(),
            dict(self.grid._variables),
            dict(self.grid._equates),
            self.grid._jump_reference_offset,
        )
        worker = SemanticWorker(snapshot, self._semantic_token)
        worker.signals.semanticReady.connect(self._apply_semantic_result)
        worker.signals.failed.connect(lambda message: self._worker_failed("semantic", message))
        self._semantic_worker = worker
        self.state |= ConsistencyState.RECALCULATING_SEMANTIC
        self._pool.start_semantic(worker)

    def _apply_semantic_result(self, result) -> None:
        if (
            result.owner != self.owner
            or result.source_revision != self.source_revision
            or result.generation != self.semantic_generation
        ):
            return
        rows = list(result.rows)
        if len(rows) != self.grid.instructions.document().blockCount():
            return
        content_changed = tuple(
            (index, row)
            for index, row in enumerate(rows)
            if index >= len(self._model_rows)
            or row.bytes_text != self._model_rows[index].bytes_text
            or row.instruction != self._model_rows[index].instruction
        )
        offset_changed = tuple(
            (index, row.offsets)
            for index, row in enumerate(rows)
            if index >= len(self._model_rows)
            or row.offsets != self._model_rows[index].offsets
        )
        previous_rows = self.grid._rows
        previous_all_rows = self.grid._all_rows
        self.grid._rows = list(rows)
        self.grid._all_rows = list(rows)
        try:
            apply_semantic_projection(self.grid, offset_changed, content_changed)
        except Exception as error:
            self.grid._rows = previous_rows
            self.grid._all_rows = previous_all_rows
            self.state &= ~ConsistencyState.RECALCULATING_SEMANTIC
            self._worker_failed("semantic", str(error))
            return
        previous_sizes = tuple(_row_size(row) for row in self._model_rows)
        current_sizes = tuple(_row_size(row) for row in rows)
        if previous_sizes != current_sizes:
            self.structural_revision += 1
            self._invalidate_visual()
        self._model_rows = rows
        self._line_revisions = [self.source_revision] * len(rows)
        self._contributions = LineContributionIndex(current_sizes)
        self._range_consistency.reset(len(rows), self.structural_revision)
        self._dependency_index = _dependency_index(rows)
        self.grid._set_editing_labels(dict(result.labels))
        self.grid.raw_instructions.set_hazard_extra_selections([])
        self.grid._apply_instruction_hazards(list(result.hazards))
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)
        self._dirty_ranges = ()
        self._dirty_from_line = None
        self.visual_revision_applied = self.structural_revision
        self.semantic_revision_applied = self.source_revision
        self.state &= ~ConsistencyState.DIRTY_VISUAL
        self.state &= ~ConsistencyState.RECALCULATING_VISUAL
        self.state &= ~ConsistencyState.DIRTY_SEMANTIC
        self.state &= ~ConsistencyState.RECALCULATING_SEMANTIC
        self.grid._last_assembly_refresh_window = None
        self.grid._assembly_refresh_warning_emitted = False

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
        """Repair the viewport immediately and establish a complete F1 revision."""

        self.flush_collected_changes()
        if (
            self.state == ConsistencyState.CLEAN
            and self.visual_revision_applied == self.structural_revision
            and self.semantic_revision_applied == self.source_revision
        ):
            return self.ensure_consistent("f1-clean")
        lines = self._document_lines()
        if not self.grid._bounded_refresh_available(lines):
            return self.ensure_consistent("f1")
        self.grid._refresh_bounded_source_rows(lines)
        self._model_rows = self.grid.export_rows()
        self._contributions = LineContributionIndex([_row_size(row) for row in self._model_rows])
        self._range_consistency.invalidate_from(
            0,
            len(self._model_rows),
            self.structural_revision,
        )
        self._dependency_index = _dependency_index(self._model_rows)
        self._dirty_ranges = (DirtyRange(0, max(0, len(self._model_rows) - 1)),)
        self._dirty_from_line = 0
        self._invalidate_visual()
        self._invalidate_semantic()
        self._start_visual()
        self._start_semantic()
        self.grid.commandWarningRequested.emit(BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_REBUILDING)
        snapshot = ConsistentEditorSnapshot(
            self.owner,
            self.source_revision,
            self.structural_revision,
            tuple(self._model_rows),
            dict(self.grid._labels),
        )
        return ConsistencyBarrierResult(True, snapshot)

    def prioritize_viewport(self) -> None:
        """Requeue a pending full projection around the newly visible region."""

        viewport = self._viewport_range()
        if self._range_consistency.is_current(
            viewport.first,
            viewport.last,
            self.structural_revision,
        ):
            return
        if not self._dirty_ranges or self._viewport_timer.isActive():
            return
        self._viewport_timer.start()

    def rederive_symbol_lines(self, indices: tuple[int, ...]) -> None:
        """Rebuild only rows depending on changed Symbol definitions."""

        active = tuple(sorted({
            index for index in indices
            if 0 <= index < len(self._model_rows)
        }))
        if not active or not self.enabled():
            return
        self.source_revision += 1
        self._invalidate_semantic()
        viewport = self._viewport_range()
        prioritized = sorted(
            active,
            key=lambda index: (
                0 if viewport.first <= index <= viewport.last else 1,
                min(abs(index - viewport.first), abs(index - viewport.last)),
                index,
            ),
        )
        immediate = sorted(prioritized[:OFFSET_BATCH_SIZE])
        changed: list[tuple[int, BinaryWorkbenchRowDTO]] = []
        structural_from: int | None = None
        for index in immediate:
            rebuilt = self._derive_lines(index, [self._model_rows[index].instruction])
            if not rebuilt:
                continue
            previous_size = _row_size(self._model_rows[index])
            current_size = _row_size(rebuilt[0])
            self._model_rows[index] = rebuilt[0]
            self._line_revisions[index] = self.source_revision
            self._contributions.splice(index, 1, [current_size])
            changed.append((index, rebuilt[0]))
            if previous_size != current_size:
                structural_from = index if structural_from is None else min(
                    structural_from, index
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
            self.structural_revision += 1
            self.visual_generation += 1
            self._invalidate_visual()
            self._range_consistency.invalidate_from(
                structural_from,
                len(self._model_rows),
                self.structural_revision,
            )
            dirty = DirtyRange(structural_from, len(self._model_rows) - 1)
            self._dirty_ranges = merge_dirty_ranges(self._dirty_ranges, dirty)
            self._dirty_from_line = (
                structural_from
                if self._dirty_from_line is None
                else min(self._dirty_from_line, structural_from)
            )
            self._schedule_visual()
        self._schedule_semantic()
        self.grid._emit_rows_changed(self.grid.export_rows(), deferred=True)

    def _prioritize_coalesced_viewport(self) -> None:
        """Apply at most one viewport reprioritization per display frame."""

        if self._viewport_restart_scheduled or not self._dirty_ranges:
            return
        self._viewport_restart_scheduled = True
        self._invalidate_visual()
        QTimer.singleShot(0, self._start_visual)

    def cancel_pending(self) -> None:
        """Invalidate timers and cooperative workers without terminating threads."""

        self._visual_quiet.stop()
        self._visual_maximum.stop()
        self._semantic_timer.stop()
        self._viewport_timer.stop()
        self._bytes_content_timer.stop()
        self._pending_bytes_content_batches.clear()
        self.visual_generation += 1
        self.semantic_generation += 1
        if self._visual_token is not None:
            self._visual_token.cancel()
        if self._semantic_token is not None:
            self._semantic_token.cancel()
        self._pool.clear()

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

    def _valid_offset_batch(self, batch) -> bool:
        return (
            batch.owner == self.owner
            and batch.structural_revision == self.structural_revision
            and batch.generation == self.visual_generation
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
            dict(self.grid._labels),
            dict(self.grid._variables),
            dict(self.grid._equates),
            False,
        )
        return self.grid._validated_standard_jump_rows(rows, lines)

    def _labels_changed(self, first: int, old_span: int, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        before = [declared_label(row.instruction) for row in self._model_rows[first : first + old_span]]
        after = [declared_label(row.instruction) for row in rows]
        return before != after

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
