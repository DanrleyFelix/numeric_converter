import os
import inspect
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.editor_consistency import (
    ConsistencyBarrierResult,
    LineContentBatch,
    SemanticResult,
)
from src.core.binary_workbench.mips_r3000a import build_rows_from_instructions
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.binary_workbench.mips_r3000a import source_line_rows as source_rows_module
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.editor.consistency import (
    coordinator as coordinator_module,
    projection as projection_module,
)
from src.presentation.ui.components.binary_workbench.editor.consistency.coordinator import (
    EditorConsistencyCoordinator,
)
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.page import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
from src.presentation.ui.components.binary_workbench.tabs import BinaryWorkbenchTabs
from src.presentation.ui.helpers.load_qss import STYLESHEET
from src.presentation.ui.components.binary_workbench.window_version_actions import (
    BinaryWorkbenchWindowVersionMixin,
)

_APP = None
_REFERENCE = "Reference Offset A"
_GRIDS = []


@pytest.fixture(autouse=True)
def _cleanup_grids():
    yield
    for grid in _GRIDS:
        grid._consistency_coordinator.shutdown()
        grid.close()
        grid.deleteLater()
    _GRIDS.clear()
    _app().processEvents()


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _grid(lines: list[str], *, references: bool = False) -> BinaryWorkbenchGrid:
    _app()
    offsets = [BINARY_WORKBENCH_TEXT.FILE, *([_REFERENCE] if references else [])]
    bases = {_REFERENCE: "0x80000000"} if references else {}
    rows = build_rows_from_instructions(lines, offsets, bases)
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.set_symbols(labels_from_rows(rows), {}, {}, {})
    grid.load_rows(
        [
            *offsets,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.DECODED_TEXT,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        rows,
        reference_offset_bases=bases,
    )
    grid.resize(1000, 260)
    grid.show()
    _app().processEvents()
    _GRIDS.append(grid)
    return grid


def test_contents_change_handler_only_collects_a_region(monkeypatch):
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator
    called = []

    monkeypatch.setattr(
        coordinator,
        "_derive_lines",
        lambda *_args: called.append(True),
    )
    coordinator.collect_contents_change(0, 0, 1)

    assert coordinator._pending_first == 0
    assert coordinator._pending_last == 0
    assert coordinator.source_revision == 0
    assert not hasattr(coordinator, "_visual_worker")
    assert called == []
    coordinator._clear_collector()


def test_contents_change_handler_contains_no_expensive_derivation_path():
    source = inspect.getsource(EditorConsistencyCoordinator.collect_contents_change)

    assert "toPlainText" not in source
    assert "_derive_lines" not in source
    assert "_start_visual" not in source
    assert "_start_semantic" not in source
    assert "assemble" not in source


def test_symbol_projection_does_not_become_a_source_edit_or_erase_labels():
    grid = _grid(["entry:", "nop", "next:", "nop"])
    original_text = grid.instructions.toPlainText()
    original_labels = grid.current_labels()

    grid.set_symbols(original_labels, {"value": "0x20"}, {"value": "0x20"}, {})

    assert grid.instructions.toPlainText() == original_text
    assert grid.current_labels() == original_labels
    assert grid.instructions.document().isModified() is False


def test_known_offset_navigation_never_forces_a_global_barrier(monkeypatch):
    grid = _grid(["nop" for _ in range(200)], references=True)
    coordinator = grid._consistency_coordinator
    calls = []
    monkeypatch.setattr(
        coordinator,
        "ensure_consistent",
        lambda _reason: calls.append("barrier"),
    )

    assert grid.prepare_navigation() is True
    grid.set_visible_offset(120 * 4)
    _app().processEvents()

    assert calls == []


def test_navigation_to_current_offset_rechecks_typed_viewport_flags():
    grid = _grid(["nop" for _ in range(40)], references=True)
    coordinator = grid._consistency_coordinator
    current = coordinator._viewport_range()
    coordinator._pending_symbol_lines.add(current.first)
    coordinator._viewport_timer.stop()

    grid.set_visible_offset(grid.scrollbar.value())

    assert coordinator._viewport_timer.isActive() is True


def test_hidden_derived_column_does_not_force_full_structure_rebuild(monkeypatch):
    """A non-materialized legacy column must not penalize a source insertion."""

    grid = _grid(["nop"])
    grid._configured_columns.remove(BINARY_WORKBENCH_TEXT.DECODED_TEXT)
    grid.decoded_text.setPlainText("")
    monkeypatch.setattr(
        projection_module,
        "_rebuild_derived_documents",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("hidden column forced a full projection")
        ),
    )

    grid.instructions.setPlainText("nop\nnop")
    QTest.qWait(100)
    _app().processEvents()

    assert grid.instructions.document().blockCount() == 2
    assert grid.decoded_text.document().blockCount() == 1


def test_label_only_commit_reuses_symbol_catalog_maps(monkeypatch):
    grid = _grid(["entry: nop"])
    variables = {f"local_{index}": hex(index) for index in range(32)}
    equates = {f"global_{index}": hex(index) for index in range(64)}
    grid.set_symbols({"entry": "0x00000000"}, variables, equates, {})
    variable_map = grid._symbol_maps[1]
    equate_map = grid._symbol_maps[2]

    monkeypatch.setattr(
        grid._instruction_highlighter,
        "symbol_maps",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("label updates must not rebuild Symbol maps")
        ),
    )
    monkeypatch.setattr(
        grid.instructions,
        "set_symbol_helpers",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("label updates must not rebuild Symbol helpers")
        ),
    )

    grid._set_editing_labels({"entry": "0x00000004"})

    assert grid._symbol_maps[1] is variable_map
    assert grid._symbol_maps[2] is equate_map
    assert grid.instructions._label_offsets["entry"][1] == 4


def test_single_line_edit_reuses_large_symbol_resolver(monkeypatch):
    """Typing must not normalize a large Symbol catalog for every character."""

    grid = _grid(["ori $t0, $zero, _local_0001"])
    variables = {f"local_{index:04d}": hex(index) for index in range(2500)}
    grid.set_symbols({}, variables, {}, {})
    constructions: list[bool] = []
    original = source_rows_module.MipsSymbolResolver.__init__

    def tracked(resolver, *args, **kwargs):
        constructions.append(True)
        original(resolver, *args, **kwargs)

    monkeypatch.setattr(source_rows_module.MipsSymbolResolver, "__init__", tracked)
    editor = grid.instructions
    cursor = editor.textCursor()
    cursor.setPosition(len(editor.toPlainText()))
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key_Backspace)
    _app().processEvents()

    assert constructions == []


def test_locked_single_line_edit_stays_incremental_and_preserves_bytes(monkeypatch):
    """The shift rule must not send each Backspace through legacy full rebuilds."""

    grid = _grid(["nop", "nop"])
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    monkeypatch.setattr(
        grid,
        "_normalized_instruction_lines",
        lambda: (_ for _ in ()).throw(
            AssertionError("locked character edit scanned the complete document")
        ),
    )
    editor = grid.instructions
    cursor = QTextCursor(editor.document().firstBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)

    QTest.keyClick(editor, Qt.Key_Backspace)
    _app().processEvents()

    assert grid._consistency_coordinator.enabled() is True
    assert editor.document().firstBlock().text().casefold() == "no"
    assert grid.export_rows()[0].bytes_text == "00 00 00 00"


def test_deferred_rows_signal_allocates_snapshot_only_when_flushed(monkeypatch):
    grid = _grid(["nop" for _ in range(128)])
    calls = []
    original = grid.export_rows

    def tracked():
        calls.append(True)
        return original()

    monkeypatch.setattr(grid, "export_rows", tracked)
    grid._emit_rows_changed(deferred=True)

    assert calls == []
    grid.flush_pending_rows_changed()
    assert calls == [True]


def test_label_fold_refreshes_revealed_viewport_immediately(monkeypatch):
    grid = _grid(["entry:", "nop", "addiu $t0, $t0, 1"])
    grid.set_label_folding_enabled(True)
    viewport_calls = []
    highlight_calls = []
    monkeypatch.setattr(
        grid._consistency_coordinator,
        "prioritize_viewport",
        viewport_calls.append,
    )
    monkeypatch.setattr(
        grid,
        "_refresh_visible_highlighter_projection",
        lambda: highlight_calls.append(True),
    )

    grid.toggle_label_fold("entry")
    QTest.qWait(BINARY_WORKBENCH_TIMING.CONSISTENCY_FOLD_VIEWPORT_MS + 80)

    assert viewport_calls == ["label-fold"]
    assert len(highlight_calls) >= 1


def test_folded_viewport_reports_only_the_disjoint_rows_revealed_on_screen():
    """Collapsed bodies must not displace later visible labels from priority."""

    lines = []
    for label_index in range(3):
        lines.append(f"label_{label_index}:")
        lines.extend("nop" for _ in range(40))
    grid = _grid(lines)
    grid.set_label_folding_enabled(True)
    grid.toggle_label_fold("label_0")
    grid.toggle_label_fold("label_1")
    QTest.qWait(BINARY_WORKBENCH_TIMING.CONSISTENCY_FOLD_VIEWPORT_MS + 40)

    ranges = grid._visible_source_ranges()

    assert (0, 0) in ranges
    assert (41, 41) in ranges
    assert any(first <= 82 <= last for first, last in ranges)
    assert not any(first <= 20 <= last for first, last in ranges)


def test_declared_label_is_highlighted_before_global_semantics_finish():
    """A visible declaration is syntactic and does not need a global label map."""

    grid = _grid(["fresh_label:", "nop"])
    grid.set_symbols({}, {}, {}, {})
    grid._refresh_visible_highlighter_projection()
    _app().processEvents()
    formats = grid.instructions.document().firstBlock().layout().formats()
    expected = psx_mips_required_highlight_color("label").casefold()

    assert any(
        item.start == 0
        and item.length >= len("fresh_label")
        and item.format.foreground().color().name().casefold() == expected
        for item in formats
    )


def test_selection_demand_requires_a_complete_line_and_is_debounced(monkeypatch):
    """One selected character must not trigger derivation work."""

    grid = _grid(["addiu $a0, $a0, 2"])
    calls = []
    monkeypatch.setattr(
        grid._consistency_coordinator,
        "materialize_selected_projection",
        lambda *args: calls.append(args),
    )
    block = grid.bytes.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position() + 1, QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)
    QTest.qWait(BINARY_WORKBENCH_TIMING.CONSISTENCY_SELECTION_DEBOUNCE_MS + 20)

    assert calls == []

    block = grid.bytes.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)
    QTest.qWait(BINARY_WORKBENCH_TIMING.CONSISTENCY_SELECTION_DEBOUNCE_MS + 100)

    assert calls == [(BINARY_WORKBENCH_TEXT.BYTES, 0, 0)]


def test_selection_demand_projects_only_the_requested_column():
    """Selection refresh must not rewrite peer columns or start global work."""

    grid = _grid(["addiu $a0, $a0, 2"])
    projection_module._replace_line(grid.bytes, 0, "")
    projection_module._replace_line(grid.raw_instructions, 0, "RAW STALE")
    projection_module._replace_line(grid.decoded_text, 0, "DECODE STALE")
    grid._consistency_coordinator.state = (
        coordinator_module.ConsistencyState.DIRTY_SEMANTIC
    )

    grid._consistency_coordinator.materialize_selected_projection(
        BINARY_WORKBENCH_TEXT.BYTES,
        0,
        0,
    )

    assert _editor_line(grid.bytes, 0) == grid._display_bytes_row(
        grid._consistency_coordinator._model_rows[0]
    )
    assert _editor_line(grid.raw_instructions, 0) == "RAW STALE"
    assert _editor_line(grid.decoded_text, 0) == "DECODE STALE"


def test_selection_demand_skips_a_current_projection(monkeypatch):
    """Settled selection must not derive a row without a relevant dirty flag."""

    grid = _grid(["addiu $a0, $a0, 2"])
    monkeypatch.setattr(
        grid._consistency_coordinator,
        "_derive_lines",
        lambda *_args: pytest.fail("current selection started unnecessary work"),
    )

    grid._consistency_coordinator.materialize_selected_projection(
        BINARY_WORKBENCH_TEXT.BYTES,
        0,
        0,
    )


def test_large_selection_prepares_only_the_active_bounded_edge(monkeypatch):
    """A drag over many rows may request one selected edge, never all rows."""

    grid = _grid(["addiu $a0, $a0, 2"] * 400)
    calls = []
    monkeypatch.setattr(
        grid._consistency_coordinator,
        "materialize_selected_projection",
        lambda *args: calls.append(args),
    )
    grid.bytes.selectAll()
    QTest.qWait(BINARY_WORKBENCH_TIMING.CONSISTENCY_SELECTION_DEBOUNCE_MS + 100)

    assert len(calls) == 1
    kind, first, last = calls[0]
    assert kind == BINARY_WORKBENCH_TEXT.BYTES
    assert last == 399
    assert last - first + 1 == 128


def test_projection_repair_reports_stable_status():
    grid = _grid(["nop", "addiu $t0, $t0, 1"])
    statuses = []
    grid.commandStatusRequested.connect(statuses.append)

    projection_module._rebuild_derived_documents(grid)

    assert statuses == [BINARY_WORKBENCH_TEXT.STATUS_PROJECTION_RECOVERED]


def test_initial_tab_materialization_does_not_force_full_commit(
    monkeypatch,
    tmp_path,
):
    """A fresh page is already source-consistent and must not hit the barrier."""

    calls = []
    monkeypatch.setattr(
        BinaryWorkbenchEditorPage,
        "commit_current_editor_text",
        lambda _page: calls.append(True) or True,
    )
    context = BinaryWorkbenchTabContextDTO(
        "startup",
        "scratch",
        "Startup",
        rows=build_rows_from_instructions(
            ["nop"] * 32,
            [BINARY_WORKBENCH_TEXT.FILE],
            {},
        ),
    )
    tabs = BinaryWorkbenchTabs(
        BinaryWorkbenchStateDTO(tabs=[context], active_tab_id=context.tab_id),
        tmp_path,
    )

    assert calls == []
    tabs.close()
    tabs.deleteLater()
    _app().processEvents()


def test_broad_copy_never_runs_the_synchronous_barrier(monkeypatch):
    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator
    calls = []
    coordinator.visual_revision_applied = coordinator.structural_revision
    coordinator.semantic_revision_applied = coordinator.source_revision
    coordinator.state = coordinator_module.ConsistencyState.CLEAN
    monkeypatch.setattr(
        coordinator,
        "ensure_consistent",
        lambda reason: calls.append(reason) or ConsistencyBarrierResult(True),
    )

    assert coordinator.ensure_broad_copy_consistent() is True
    assert calls == []

    coordinator._dirty_ranges = (coordinator_module.DirtyRange(0, 1),)
    assert coordinator.ensure_broad_copy_consistent() is True
    assert calls == []

    coordinator.state = coordinator_module.ConsistencyState.DIRTY_SEMANTIC
    coordinator._copy_semantic_pending = True
    assert coordinator.ensure_broad_copy_consistent() is False
    assert calls == []


def test_stale_broad_copy_prepares_only_requested_rows_without_projection(monkeypatch):
    grid = _grid(["nop", "addiu $t0, $t0, 1"])
    coordinator = grid._consistency_coordinator
    coordinator.state = coordinator_module.ConsistencyState.DIRTY_SEMANTIC
    coordinator._copy_semantic_pending = True
    prepared = []
    monkeypatch.setattr(
        coordinator._pool,
        "start_immediate",
        lambda worker: worker.run(),
    )
    monkeypatch.setattr(
        coordinator_module,
        "apply_full_projection",
        lambda *_args, **_kwargs: pytest.fail("broad copy must not rewrite the UI"),
    )

    assert coordinator.request_broad_copy(
        1,
        1,
        lambda first, rows: prepared.append((first, rows)),
    ) is False
    assert prepared[0][0] == 1
    assert [row.bytes_text for row in prepared[0][1]] == ["01 00 08 25"]


def test_symbol_and_highlight_maintenance_does_not_block_broad_copy():
    grid = _grid(["nop", "addiu $t0, $t0, 1"])
    coordinator = grid._consistency_coordinator
    coordinator.state = coordinator_module.ConsistencyState.DIRTY_SEMANTIC
    coordinator._bulk_symbols_pending = True
    coordinator._pending_symbol_lines.add(1)
    coordinator._copy_semantic_pending = False

    assert coordinator.ensure_broad_copy_consistent() is True


def test_copying_all_bytes_checks_derived_consistency(monkeypatch):
    grid = _grid(["nop", "addiu $t0, $t0, 1"])
    calls = []
    monkeypatch.setattr(
        grid._consistency_coordinator,
        "request_broad_copy",
        lambda first, last, callback: calls.append((first, last)) or True,
    )
    grid.bytes.selectAll()

    grid._copy_local_editor_selection(grid.bytes)

    assert calls == [(0, 1)]
    assert QApplication.clipboard().text() == "00 00 00 00\n01 00 08 25"


def test_partial_bytes_copy_checks_only_copy_relevant_consistency(monkeypatch):
    grid = _grid(["nop", "addiu $t0, $t0, 1", "nop"])
    calls = []
    monkeypatch.setattr(
        grid._consistency_coordinator,
        "request_broad_copy",
        lambda first, last, callback: calls.append((first, last)) or True,
    )
    block = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)

    grid._copy_local_editor_selection(grid.bytes)

    assert calls == [(1, 1)]


def test_stale_bytes_copy_callback_keeps_the_requested_column(monkeypatch):
    """Regression: the async callback must capture its column kind."""

    grid = _grid(["nop", "addiu $t0, $t0, 1"])
    coordinator = grid._consistency_coordinator
    coordinator.state = coordinator_module.ConsistencyState.DIRTY_SEMANTIC
    coordinator._copy_semantic_pending = True
    monkeypatch.setattr(coordinator._pool, "start_immediate", lambda worker: worker.run())
    grid.bytes.selectAll()

    grid._copy_local_editor_selection(grid.bytes)

    assert QApplication.clipboard().text() == "00 00 00 00\n01 00 08 25"


def test_bytes_selection_summary_scans_only_its_two_edge_blocks(monkeypatch):
    """Selection feedback cost must not grow with the selected row count."""

    grid = _grid(["addiu $a0, $a0, 2"] * 4000)
    first = grid.bytes.document().findBlockByNumber(100)
    last = grid.bytes.document().findBlockByNumber(3900)
    cursor = QTextCursor(first)
    cursor.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
    visited = []
    original = grid._selected_token_indices

    def tracked(block, start, end):
        visited.append(block.blockNumber())
        return original(block, start, end)

    monkeypatch.setattr(grid, "_selected_token_indices", tracked)
    selected = grid._selected_byte_range(cursor)

    assert selected == (400, 15603, 15204)
    assert visited == [100, 3900]


def test_bytes_drag_does_not_autoscroll_inside_first_or_last_visible_line():
    """Autoscroll starts only after the mouse actually leaves the viewport."""

    grid = _grid(["nop"] * 80)
    editor = grid.bytes

    editor._update_selection_scroll(QPoint(0, 0))
    assert not editor._selection_timer.isActive()
    editor._update_selection_scroll(QPoint(0, editor.viewport().height() - 1))
    assert not editor._selection_timer.isActive()

    editor._update_selection_scroll(QPoint(0, -1))
    assert editor._selection_timer.isActive()
    assert editor._selection_scroll_delta < 0
    editor._stop_selection_scroll()
    editor._update_selection_scroll(QPoint(0, editor.viewport().height()))
    assert editor._selection_timer.isActive()
    assert editor._selection_scroll_delta > 0
    editor._stop_selection_scroll()


def test_single_bytes_character_edit_does_not_read_the_complete_document(monkeypatch):
    """Ordinary Bytes typing must remain O(1) even for a large document."""

    grid = _grid(["addiu $a0, $a0, 2" for _ in range(4000)])
    editor = grid.bytes
    block = editor.document().findBlockByNumber(2000)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)
    editor.setFocus()
    monkeypatch.setattr(
        grid,
        "_normalized_bytes_lines",
        lambda: (_ for _ in ()).throw(
            AssertionError("single Bytes character scanned the full document")
        ),
    )
    monkeypatch.setattr(
        grid,
        "_byte_row_policies",
        lambda: (_ for _ in ()).throw(
            AssertionError("single Bytes character scanned every row policy")
        ),
    )

    QTest.keyClick(editor, Qt.Key_Backspace)
    _app().processEvents()

    assert grid._bytes_staged_block == 2000
    assert len(_editor_line(editor, 2000).replace(" ", "")) == 7


def test_same_qt_cycle_coalesces_multiple_signals_into_one_flush(monkeypatch):
    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator
    calls = []
    original = coordinator.flush_collected_changes

    def tracked():
        calls.append(True)
        coordinator._clear_collector()

    monkeypatch.setattr(coordinator, "flush_collected_changes", tracked)
    coordinator.collect_contents_change(0, 0, 1)
    coordinator.collect_contents_change(2, 0, 1)
    _app().processEvents()

    assert calls == [True]
    monkeypatch.setattr(coordinator, "flush_collected_changes", original)


def test_non_contiguous_assembly_deletion_commits_every_visible_column_immediately():
    grid = _grid(["addiu $a0, $a0, 3" for _ in range(48)], references=True)
    ranges = []
    for index in (3, 6, 9):
        block = grid.instructions.document().findBlockByNumber(index)
        ranges.append((block.position(), block.position() + len(block.text())))
    grid.instructions._occurrence_ranges = ranges
    grid.instructions._apply_occurrence_selection(ranges[-1])
    grid.instructions.setFocus()

    QTest.keyClick(grid.instructions, Qt.Key_Backspace)
    _app().processEvents()

    for index in (3, 6, 9):
        assert _editor_line(grid.instructions, index) == ""
        assert _editor_line(grid.bytes, index) == ""
        assert _editor_line(grid.raw_instructions, index) == ""
        assert _editor_line(grid.decoded_text, index) == ""
        assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], index) == "-"
        assert _editor_line(grid._offset_editors[_REFERENCE], index) == "-"


@pytest.mark.parametrize("operation", ["paste", "delete", "cut", "replace", "undo", "redo"])
def test_explicit_multiline_operation_has_one_aggregated_flush(monkeypatch, operation):
    grid = _grid(["nop", "nop", "nop"])
    coordinator = grid._consistency_coordinator
    calls = []

    def tracked():
        calls.append((coordinator._pending_first, coordinator._pending_last))
        coordinator._clear_collector()

    monkeypatch.setattr(coordinator, "flush_collected_changes", tracked)
    coordinator.begin_edit_operation(operation)
    coordinator.collect_contents_change(0, 0, 4)
    coordinator.collect_contents_change(4, 4, 8)
    coordinator.collect_contents_change(8, 4, 0)
    coordinator.end_edit_operation()

    assert calls == [(0, 2)]


def test_only_viewport_and_small_bytes_projection_timers_remain():
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator

    assert coordinator._viewport_timer.interval() == 16
    assert coordinator._viewport_timer.isSingleShot()
    assert coordinator._bytes_content_timer.isSingleShot()
    assert not hasattr(coordinator, "_visual_quiet")
    assert not hasattr(coordinator, "_semantic_timer")
    assert not hasattr(coordinator, "_offset_batch_timer")


def test_dirty_visual_state_does_not_schedule_global_offset_work():
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator

    coordinator._schedule_visual()

    assert coordinator.state & coordinator_module.ConsistencyState.DIRTY_VISUAL
    assert not hasattr(coordinator._pool, "start_visual")


def test_user_input_cancels_obsolete_semantic_work_without_rescheduling_it():
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator
    from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken

    coordinator._semantic_token = CancellationToken()

    coordinator._defer_eventual_for_user_input()

    assert coordinator._semantic_token.is_cancelled()
    assert not hasattr(coordinator, "_semantic_timer")


def test_repeated_visual_invalidations_do_not_create_jobs():
    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator

    coordinator._schedule_visual()
    coordinator._schedule_visual()

    assert not hasattr(coordinator._pool, "start_visual")


def test_four_to_four_edit_is_local_and_preserves_typing_cursor():
    grid = _grid(["lui $v0, 0x8B", "nop"])
    coordinator = grid._consistency_coordinator
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    position = block.position() + block.text().index("B")
    cursor.setPosition(position)
    grid.instructions.setTextCursor(cursor)

    grid.instructions.insertPlainText("A")
    QTest.qWait(40)

    assert coordinator.source_revision == 1
    assert coordinator.structural_revision == 0
    assert grid.instructions.textCursor().position() == position + 1
    assert grid.export_rows()[0].bytes_text
    assert not hasattr(coordinator, "_semantic_timer")
    assert not hasattr(coordinator, "_semantic_worker")


def test_inserted_instruction_updates_offsets_immediately_without_a_redundant_job():
    grid = _grid(["nop", "nop"], references=True)
    coordinator = grid._consistency_coordinator
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.EndOfBlock)
    cursor.insertText("\nnop")
    grid.instructions.setTextCursor(cursor)
    _app().processEvents()

    rows = grid.export_rows()
    assert [row.offsets[BINARY_WORKBENCH_TEXT.FILE] for row in rows] == [
        "0x00000000",
        "0x00000004",
        "0x00000008",
    ]
    assert [row.offsets[_REFERENCE] for row in rows] == [
        "0x80000000",
        "0x80000004",
        "0x80000008",
    ]
    assert not hasattr(coordinator._pool, "start_visual")


def test_invalid_symbol_is_cleared_and_redistributed_immediately():
    grid = _grid(["nop", "nop", "nop"], references=True)
    coordinator = grid._consistency_coordinator
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    cursor.insertText("unknown_symbol")
    grid.instructions.setTextCursor(cursor)
    _app().processEvents()

    rows = grid.export_rows()
    assert rows[0].bytes_text == ""
    assert rows[0].offsets == {
        BINARY_WORKBENCH_TEXT.FILE: "-",
        _REFERENCE: "-",
    }
    assert rows[1].offsets[BINARY_WORKBENCH_TEXT.FILE] == "0x00000000"
    assert rows[2].offsets[BINARY_WORKBENCH_TEXT.FILE] == "0x00000004"
    assert rows[1].offsets[_REFERENCE] == "0x80000000"
    assert rows[2].offsets[_REFERENCE] == "0x80000004"
    assert not hasattr(coordinator._pool, "start_visual")


def test_invalid_line_becoming_valid_restores_visible_offset_text():
    grid = _grid(["unknown_symbol", "nop"], references=True)
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    cursor.insertText("nop")
    _app().processEvents()

    for editor in (
        grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE],
        grid._offset_editors[_REFERENCE],
    ):
        assert _editor_line(editor, 0).startswith("0x")
        assert _editor_line_alpha(editor, 0) > 0


def test_structural_edit_cannot_propagate_transparent_dash_format_to_offsets():
    lines = ["entry:", "unknown_symbol", "nop", "nop"]
    grid = _grid(lines, references=True)
    block = grid.instructions.document().findBlockByNumber(1)
    cursor = QTextCursor(block)
    cursor.setPosition(block.position())
    cursor.setPosition(block.next().position(), QTextCursor.KeepAnchor)
    cursor.removeSelectedText()
    _app().processEvents()

    for row in range(grid.instructions.document().blockCount()):
        if not grid.export_rows()[row].bytes_text:
            continue
        assert _editor_line_alpha(
            grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], row
        ) > 0
        assert _editor_line_alpha(grid._offset_editors[_REFERENCE], row) > 0


def test_two_trailing_blank_lines_keep_every_column_on_the_same_visible_row():
    grid = _grid(["entry:", *["nop" for _ in range(70)]], references=True)
    grid.set_label_folding_enabled(True)
    block = grid.instructions.document().lastBlock()
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.instructions.setTextCursor(cursor)
    grid.instructions.setFocus()

    QTest.keyClick(grid.instructions, Qt.Key_Return)
    QTest.keyClick(grid.instructions, Qt.Key_Return)
    QTest.qWait(50)
    _app().processEvents()

    editors = (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.instructions,
    )
    assert len({editor.document().blockCount() for editor in editors}) == 1
    assert len({editor.firstVisibleBlock().blockNumber() for editor in editors}) == 1


def test_structural_edit_repairs_a_previously_diverged_derived_document():
    grid = _grid(["entry:", *["nop" for _ in range(24)]], references=True)
    coordinator = grid._consistency_coordinator
    raw_lines = grid.raw_instructions.toPlainText().split("\n")
    grid.raw_instructions.setPlainText("\n".join(raw_lines[:-1]))
    block = grid.instructions.document().findBlockByNumber(5)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)

    cursor.insertText("\n")
    coordinator.flush_collected_changes()

    editors = (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    )
    assert {editor.document().blockCount() for editor in editors} == {
        grid.instructions.document().blockCount()
    }
    assert grid.raw_instructions.document().findBlockByNumber(6).isValid()


def test_undo_moves_the_assembly_cursor_to_the_undone_edit():
    grid = _grid(["entry:", *["nop" for _ in range(80)]], references=True)
    grid.scrollbar.setValue(40 * 4)
    block = grid.instructions.document().findBlockByNumber(45)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.instructions.setTextCursor(cursor)
    grid.instructions.setFocus()
    QTest.keyClick(grid.instructions, Qt.Key_Return)
    _app().processEvents()
    cursor_row = grid.instructions.textCursor().blockNumber()
    scroll_before = grid.scrollbar.value()

    QTest.keyClick(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    _app().processEvents()

    assert grid.instructions.textCursor().blockNumber() == cursor_row - 1
    assert grid.scrollbar.value() == min(scroll_before, grid.scrollbar.maximum())
    assert grid.instructions.textCursor().blockNumber() < (
        grid.instructions.document().blockCount() - 1
    )


def test_undo_without_available_action_keeps_the_current_cursor():
    grid = _grid(["nop", "jr $ra"], references=True)
    block = grid.instructions.document().findBlockByNumber(1)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.instructions.setTextCursor(cursor)
    position = grid.instructions.textCursor().position()

    QTest.keyClick(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    _app().processEvents()

    assert grid.instructions.textCursor().position() == position


def test_structural_source_delete_repairs_the_current_offset_viewport_immediately():
    grid = _grid(["nop" for _ in range(400)], references=True)
    grid.scrollbar.setValue(300 * 4)
    _app().processEvents()
    coordinator = grid._consistency_coordinator
    first = grid.instructions.document().findBlockByNumber(8)
    following = first.next()
    cursor = QTextCursor(grid.instructions.document())
    cursor.setPosition(first.position())
    cursor.setPosition(following.position(), QTextCursor.KeepAnchor)

    cursor.removeSelectedText()
    coordinator.flush_collected_changes()

    viewport = coordinator._viewport_range()
    file_document = grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE].document()
    reference_document = grid._offset_editors[_REFERENCE].document()
    for index in range(viewport.first, viewport.last + 1):
        assert file_document.findBlockByNumber(index).text() == f"0x{index * 4:08X}"
        assert reference_document.findBlockByNumber(index).text() == (
            f"0x{0x80000000 + index * 4:08X}"
        )


def test_current_viewport_schedules_zero_consistency_work():
    grid = _grid(["nop" for _ in range(100)], references=True)
    coordinator = grid._consistency_coordinator
    coordinator._viewport_timer.stop()

    coordinator.prioritize_viewport()

    assert coordinator._viewport_timer.isActive() is False


def test_newly_visible_stale_viewport_is_projected_without_global_work(monkeypatch):
    grid = _grid(["nop" for _ in range(100)], references=True)
    coordinator = grid._consistency_coordinator
    viewport = coordinator_module.DirtyRange(60, 68)
    coordinator.structural_revision += 1
    coordinator._range_consistency.invalidate_from(
        viewport.first,
        len(coordinator._model_rows),
        coordinator.structural_revision,
    )
    coordinator._dirty_ranges = ()
    monkeypatch.setattr(coordinator, "_viewport_range", lambda: viewport)

    coordinator.prioritize_viewport()
    assert coordinator._viewport_timer.isActive() is True
    assert coordinator._viewport_timer.interval() <= 70
    coordinator._viewport_timer.stop()
    coordinator._prioritize_coalesced_viewport()

    assert coordinator._range_consistency.is_current(
        viewport.first,
        viewport.last,
        coordinator.structural_revision,
    )
    for row in range(viewport.first, viewport.last + 1):
        assert _editor_line(
            grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], row
        ) == coordinator._model_rows[row].offsets[BINARY_WORKBENCH_TEXT.FILE]


def test_scroll_commit_rechecks_the_final_qt_viewport(monkeypatch):
    """The 16 ms coalescer must discard the pre-layout scrollbar viewport."""

    grid = _grid(["nop" for _ in range(100)], references=True)
    coordinator = grid._consistency_coordinator
    current = coordinator_module.DirtyRange(0, 5)
    final = coordinator_module.DirtyRange(60, 65)
    selected = [current]
    monkeypatch.setattr(coordinator, "_viewport_range", lambda: selected[0])
    coordinator.structural_revision += 1
    coordinator._range_consistency.invalidate_from(
        0,
        len(coordinator._model_rows),
        coordinator.structural_revision,
    )
    calls = []
    monkeypatch.setattr(
        coordinator,
        "_apply_offset_window",
        lambda first, count: calls.append((first, count)),
    )

    coordinator.prioritize_viewport("scrollbar")
    selected[0] = final
    coordinator._viewport_timer.stop()
    coordinator._prioritize_coalesced_viewport()

    assert calls == [(final.first, final.last - final.first + 1)]


def test_repeated_scroll_positions_restart_one_typed_viewport_job(monkeypatch):
    """Rapid dragging must defer stale work until the latest destination."""

    grid = _grid(["nop" for _ in range(100)], references=True)
    coordinator = grid._consistency_coordinator
    coordinator.structural_revision += 1
    coordinator._range_consistency.invalidate_from(
        0,
        len(coordinator._model_rows),
        coordinator.structural_revision,
    )
    starts = []
    monkeypatch.setattr(coordinator._viewport_timer, "start", lambda: starts.append(1))

    coordinator.prioritize_viewport()
    coordinator.prioritize_viewport()

    assert starts == [1, 1]


def test_newly_visible_pending_bytes_content_is_projected_immediately(monkeypatch):
    grid = _grid(["nop" for _ in range(100)], references=True)
    coordinator = grid._consistency_coordinator
    row_index = 60
    previous = coordinator._model_rows[row_index]
    changed = BinaryWorkbenchRowDTO(
        previous.offsets,
        "addiu $a0, $a0, 3",
        "03 00 84 24",
        previous.original_instruction,
        previous.original_bytes_text,
    )
    coordinator._model_rows[row_index] = changed
    grid._rows[row_index] = changed
    grid._all_rows[row_index] = changed
    coordinator._pending_bytes_content_batches = [LineContentBatch(
        coordinator.owner,
        coordinator.source_revision,
        coordinator.visual_generation,
        ((row_index, changed),),
    )]
    monkeypatch.setattr(
        coordinator,
        "_viewport_range",
        lambda: coordinator_module.DirtyRange(row_index, row_index + 4),
    )

    coordinator.prioritize_viewport()
    assert coordinator._viewport_timer.isActive() is True
    coordinator._viewport_timer.stop()
    coordinator._prioritize_coalesced_viewport()

    assert _editor_line(grid.instructions, row_index).casefold() == changed.instruction
    assert coordinator._pending_bytes_content_batches == []


def test_global_symbol_refresh_is_immediate_with_byte_shifting_disabled():
    """Symbol-derived Bytes and offsets must not depend on an edit permission."""

    grid = _grid(["ori $t0, $zero, @global_value"], references=True)
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    grid.set_symbols({}, {}, {"global_value": "0x20"}, {})

    grid._consistency_coordinator.rederive_symbol_lines((0,))

    row = grid.export_rows()[0]
    assert row.bytes_text == "20 00 08 34"
    assert row.offsets[BINARY_WORKBENCH_TEXT.FILE] == "0x00000000"
    assert row.offsets[_REFERENCE] == "0x80000000"
    assert _editor_line(grid.bytes, 0) == "20 00 08 34"


def test_loaded_symbol_catalog_materializes_the_initial_viewport():
    """Opening order (catalog before rows) must still derive visible Symbols."""

    _app()
    rows = build_rows_from_instructions(
        ["ori $t0, $zero, @global_value"],
        [BINARY_WORKBENCH_TEXT.FILE],
    )
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.set_symbols({}, {}, {"global_value": "0x20"}, {})
    grid.load_rows(
        [
            BINARY_WORKBENCH_TEXT.FILE,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        rows,
    )
    grid.resize(1000, 260)
    grid.show()
    _app().processEvents()
    _GRIDS.append(grid)

    assert grid._rows[0].bytes_text == "20 00 08 34"
    assert _editor_line(grid.bytes, 0) == "20 00 08 34"
    assert grid._consistency_coordinator._symbol_consistency.is_current(
        0,
        0,
        grid._consistency_coordinator.source_revision,
    )
    formats = grid.instructions.document().firstBlock().layout().formats()
    expected = psx_mips_required_highlight_color("equate").casefold()
    assert any(
        item.format.foreground().color().name().casefold() == expected
        for item in formats
    )


def test_contiguous_symbol_viewport_uses_one_bounded_codec_call(monkeypatch):
    """Avoid one assembler setup per row during a large Symbol import."""

    grid = _grid(
        ["ori $t0, $zero, @global_value" for _ in range(64)],
        references=True,
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    grid.set_symbols({}, {}, {"global_value": "0x20"}, {})
    coordinator = grid._consistency_coordinator
    calls: list[int] = []
    original = coordinator._derive_lines

    def tracked(first: int, lines: list[str]):
        calls.append(len(lines))
        return original(first, lines)

    monkeypatch.setattr(coordinator, "_derive_lines", tracked)

    coordinator.rederive_symbol_lines(tuple(range(64)))

    assert calls == [64]
    assert all(row.bytes_text == "20 00 08 34" for row in grid.export_rows())


def test_scrolling_to_pending_symbol_rows_materializes_only_new_viewport(monkeypatch):
    """A distant stale region becomes immediate when it enters the viewport."""

    grid = _grid(
        ["ori $t0, $zero, @global_value" for _ in range(300)],
        references=True,
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    grid.set_symbols({}, {}, {"global_value": "0x20"}, {})
    coordinator = grid._consistency_coordinator
    coordinator.rederive_symbol_lines(tuple(range(300)))
    viewport = coordinator_module.DirtyRange(280, 299)
    monkeypatch.setattr(coordinator, "_viewport_range", lambda: viewport)

    coordinator.prioritize_viewport()
    assert coordinator._viewport_timer.isActive() is True
    coordinator._viewport_timer.stop()
    coordinator._prioritize_coalesced_viewport()

    assert not coordinator._pending_symbol_lines.intersection(range(280, 300))
    assert all(
        coordinator._model_rows[index].bytes_text == "20 00 08 34"
        for index in range(280, 300)
    )


def test_last_valid_instruction_gets_all_offsets_immediately_after_blank_lines():
    grid = _grid(["entry:", *["nop" for _ in range(8)]], references=True)
    previous = grid.export_rows()[-1]
    previous_file = int(previous.offsets[BINARY_WORKBENCH_TEXT.FILE], 0)
    previous_reference = int(previous.offsets[_REFERENCE], 0)
    cursor = QTextCursor(grid.instructions.document().lastBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.instructions.setTextCursor(cursor)
    grid.instructions.setFocus()

    QTest.keyClick(grid.instructions, Qt.Key_Return)
    QTest.keyClick(grid.instructions, Qt.Key_Return)
    QTest.keyClicks(grid.instructions, "nop")
    _app().processEvents()

    rows = grid.export_rows()
    assert rows[-2].offsets == {BINARY_WORKBENCH_TEXT.FILE: "-", _REFERENCE: "-"}
    assert rows[-1].offsets[BINARY_WORKBENCH_TEXT.FILE] == f"0x{previous_file + 4:08X}"
    assert rows[-1].offsets[_REFERENCE] == f"0x{previous_reference + 4:08X}"
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], len(rows) - 1) == rows[-1].offsets[BINARY_WORKBENCH_TEXT.FILE]
    assert _editor_line(grid._offset_editors[_REFERENCE], len(rows) - 1) == rows[-1].offsets[_REFERENCE]


def test_initial_stylesheet_controls_visible_text_without_embedded_black_format():
    grid = _grid(["nop"], references=True)
    grid.setStyleSheet(STYLESHEET)
    _app().processEvents()

    for editor in (*grid._offset_editors.values(), grid.raw_instructions, grid.bytes, grid.instructions):
        assert editor.palette().text().color().lightness() > 128
    for editor in grid._offset_editors.values():
        block = editor.document().firstBlock()
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.KeepAnchor)
        assert cursor.charFormat().foreground().style() == Qt.BrushStyle.NoBrush


def test_collapsed_label_keeps_first_instruction_offsets_after_f1():
    lines = [
        "* virtual_memory_range 0x80000000 0x801FFFFF",
        "* import current_file 0x80000000",
        "* define $sp 0x801FFFF0",
        "* define $pc 0x80000000",
        "* define $gp 0x8009AF08",
        "entry:",
        "nop",
        "addiu $t0, $t0, 1",
    ]
    label_row = 5
    grid = _grid(lines, references=True)
    grid.set_label_folding_enabled(True)
    grid.toggle_label_fold("entry")

    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], label_row) == "0x00000000"
    assert _editor_line(grid._offset_editors[_REFERENCE], label_row) == "0x80000000"
    assert _editor_line_alpha(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], label_row) > 0
    assert _editor_line_alpha(grid._offset_editors[_REFERENCE], label_row) > 0

    result = grid._consistency_coordinator.force_refresh()
    _app().processEvents()

    assert result.success is True
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], label_row) == "0x00000000"
    assert _editor_line(grid._offset_editors[_REFERENCE], label_row) == "0x80000000"
    assert _editor_line_alpha(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], label_row) > 0
    assert _editor_line_alpha(grid._offset_editors[_REFERENCE], label_row) > 0


@pytest.mark.parametrize("operation", ["insert", "delete"])
def test_large_structural_edit_projects_viewport_and_repairs_navigation_target(operation):
    lines = ["entry:", *["nop" for _ in range(300)]]
    grid = _grid(lines, references=True)
    coordinator = grid._consistency_coordinator
    document = grid.instructions.document()
    block = document.findBlockByNumber(10)
    cursor = QTextCursor(document)
    cursor.setPosition(block.position())
    if operation == "insert":
        cursor.insertText("nop\n")
    else:
        cursor.setPosition(block.next().position(), QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
    _app().processEvents()

    rows = grid.export_rows()
    immediate_last = min(
        len(rows) - 1,
        10 + coordinator_module.OFFSET_BATCH_SIZE - 1,
    )
    _assert_valid_file_offsets(rows[: immediate_last + 1])
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], 10)
    assert _editor_line(grid._offset_editors[_REFERENCE], 10)
    assert all(_editor_line(editor, 10) for editor in (grid.raw_instructions, grid.bytes, grid.instructions))

    last = len(rows) - 1
    coordinator.request_viewport(last, last, "go-to")
    QTest.qWait(30)

    rows = grid.export_rows()
    assert rows[-1].offsets[BINARY_WORKBENCH_TEXT.FILE] != "-"
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], len(rows) - 1)
    assert all(
        editor.document().blockCount() == grid.instructions.document().blockCount()
        for editor in grid._fold_editors()
    )


def test_removing_invalid_line_preserves_last_valid_offset_and_f1():
    lines = ["entry:", *["nop" for _ in range(32)], "unknown_symbol", *["nop" for _ in range(32)]]
    grid = _grid(lines, references=True)
    document = grid.instructions.document()
    invalid_row = 33
    block = document.findBlockByNumber(invalid_row)
    cursor = QTextCursor(document)
    cursor.setPosition(block.position())
    cursor.setPosition(block.next().position(), QTextCursor.KeepAnchor)
    cursor.removeSelectedText()
    _app().processEvents()

    rows = grid.export_rows()
    _assert_valid_file_offsets(rows)
    last_expected = rows[-1].offsets[BINARY_WORKBENCH_TEXT.FILE]
    assert last_expected != "-"
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], len(rows) - 1) == last_expected

    result = grid._consistency_coordinator.force_refresh()
    _app().processEvents()

    assert result.success is True
    rows = grid.export_rows()
    _assert_valid_file_offsets(rows)
    assert rows[-1].offsets[BINARY_WORKBENCH_TEXT.FILE] == last_expected
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], len(rows) - 1) == last_expected


def test_removing_instruction_keeps_following_last_row_aligned():
    lines = ["entry:", *["nop" for _ in range(40)], "addiu $sp, $sp, 0x60"]
    grid = _grid(lines, references=True)
    document = grid.instructions.document()
    removed_row = len(lines) - 2
    block = document.findBlockByNumber(removed_row)
    cursor = QTextCursor(document)
    cursor.setPosition(block.position())
    cursor.setPosition(block.next().position(), QTextCursor.KeepAnchor)
    cursor.removeSelectedText()
    _app().processEvents()

    rows = grid.export_rows()
    last = len(rows) - 1
    _assert_valid_file_offsets(rows)
    assert rows[last].instruction.casefold() == "addiu $sp, $sp, 0x60"
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], last) == rows[last].offsets[BINARY_WORKBENCH_TEXT.FILE]
    assert _editor_line(grid.raw_instructions, last)
    assert _editor_line(grid.bytes, last)
    assert _editor_line(grid.instructions, last).casefold() == "addiu $sp, $sp, 0x60"


def _editor_line(editor, index: int) -> str:
    """Return one projected editor line for a consistency assertion."""

    return editor.document().findBlockByNumber(index).text()


def _editor_line_alpha(editor, index: int) -> int:
    """Return the foreground alpha used by one projected text line."""

    block = editor.document().findBlockByNumber(index)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.KeepAnchor)
    return cursor.charFormat().foreground().color().alpha()


def _assert_valid_file_offsets(rows: list[BinaryWorkbenchRowDTO]) -> None:
    """Assert sequential offsets without deciding whether a row is valid."""

    current = 0
    for row in rows:
        if not row.bytes_text:
            assert row.offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-") == "-"
            continue
        assert row.offsets[BINARY_WORKBENCH_TEXT.FILE] == f"0x{current:08X}"
        current += len(bytes.fromhex(row.bytes_text.replace(" ", "")))


def test_old_line_content_batch_cannot_overwrite_new_source_revision():
    grid = _grid(["lui $v0, 0x8B"])
    coordinator = grid._consistency_coordinator
    stale = LineContentBatch(
        coordinator.owner,
        coordinator.source_revision,
        coordinator.visual_generation,
        ((0, BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "DE AD BE EF")),),
    )
    cursor = grid.instructions.textCursor()
    cursor.movePosition(QTextCursor.End)
    grid.instructions.setTextCursor(cursor)
    grid.instructions.insertPlainText("0")
    QTest.qWait(40)
    current_bytes = grid.bytes.document().firstBlock().text()

    assert coordinator._apply_line_content_batch(stale) is False
    assert grid.bytes.document().firstBlock().text() == current_bytes
    assert current_bytes != "DE AD BE EF"


def test_activation_epoch_rejects_a_result_from_the_previous_version_activation():
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator
    coordinator.activate_owner("tab", "stable-version-id")
    stale = LineContentBatch(
        coordinator.owner,
        coordinator.source_revision,
        coordinator.visual_generation,
        ((0, BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "DE AD BE EF")),),
    )

    coordinator.activate_owner("tab", "stable-version-id")

    assert coordinator.owner.version_id == "stable-version-id"
    assert coordinator.owner.activation_epoch == stale.owner.activation_epoch + 1
    assert coordinator._apply_line_content_batch(stale) is False


def test_each_runtime_version_restores_its_own_revision_context():
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator
    coordinator.activate_owner("tab", "v1-id")
    coordinator.source_revision = 5
    coordinator.structural_revision = 2
    coordinator.visual_revision_applied = 2
    coordinator.semantic_revision_applied = 5

    coordinator.activate_owner("tab", "v2-id")
    assert (coordinator.source_revision, coordinator.structural_revision) == (0, 0)
    coordinator.source_revision = 3
    coordinator.activate_owner("tab", "v1-id")

    assert (coordinator.source_revision, coordinator.structural_revision) == (5, 2)
    assert (coordinator.visual_revision_applied, coordinator.semantic_revision_applied) == (2, 5)


def test_runtime_version_uuid_survives_rename_without_entering_public_json():
    registry = type("Registry", (), {"_consistency_version_ids": {"v1": "uuid-1"}})()

    BinaryWorkbenchEditorPage.rename_consistency_version(registry, "v1", "renamed")

    assert registry._consistency_version_ids == {"renamed": "uuid-1"}


@pytest.mark.parametrize("reason", ["save-version", "debugger"])
def test_barrier_rejects_broad_copy_results_from_before_alt_s_or_f5(reason):
    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator
    from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken

    generation = coordinator._broad_copy_generation
    token = CancellationToken()
    coordinator._broad_copy_token = token
    delivered = []
    stale = SemanticResult(
        coordinator.owner,
        coordinator.source_revision,
        generation,
        (
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "DE AD BE EF"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "nop", "DE AD BE EF"),
        ),
        {},
    )

    result = coordinator.ensure_consistent(reason)
    current = tuple(row.bytes_text for row in grid.export_rows())
    coordinator._complete_broad_copy(
        stale,
        generation,
        lambda rows: delivered.append(rows),
    )

    assert result.success is True
    assert result.snapshot is not None
    assert token.is_cancelled()
    assert delivered == []
    assert tuple(row.bytes_text for row in result.snapshot.rows) == current
    assert tuple(row.bytes_text for row in grid.export_rows()) == current
    assert current != ("DE AD BE EF", "DE AD BE EF")


def test_failed_barrier_projection_never_rewrites_authoritative_source(monkeypatch):
    grid = _grid(["nop", "addiu $v0, $zero, 1"])
    coordinator = grid._consistency_coordinator
    source = grid.instructions.toPlainText()
    revisions = (coordinator.source_revision, coordinator.structural_revision)

    monkeypatch.setattr(
        coordinator_module,
        "apply_full_projection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("projection failed")),
    )
    result = coordinator.ensure_consistent("test")

    assert result.success is False
    assert "projection failed" in (result.error or "")
    assert grid.instructions.toPlainText() == source
    assert (coordinator.source_revision, coordinator.structural_revision) == revisions


def test_alt_s_preserves_exact_bytes_origin_rows(monkeypatch):
    """A save barrier must not remount memory entered in the Bytes column."""

    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator
    row = grid._complete_byte_row(0, "D9 00 00 00", 0)
    assert row is not None
    coordinator.accept_bytes_line(0, row)

    original_deriver = grid._instruction_rows_from_lines

    def conflicting_deriver(lines, *args, **kwargs):
        derived = original_deriver(lines, *args, **kwargs)
        assert derived is not None
        return [BinaryWorkbenchRowDTO(item.offsets, item.instruction, "19 00 00 00") for item in derived]

    monkeypatch.setattr(grid, "_instruction_rows_from_lines", conflicting_deriver)
    result = coordinator.ensure_consistent("save-version")

    assert result.success is True
    assert result.snapshot is not None
    assert result.snapshot.rows[0].bytes_text == "D9 00 00 00"
    assert result.snapshot.rows[0].instruction.lower() == "word 0x000000d9"
    assert grid.export_rows()[0].bytes_text == "D9 00 00 00"


def test_full_bytes_sync_marks_only_the_modified_rows_as_authoritative():
    """Unchanged Assembly rows must remain eligible for Symbol rederivation."""

    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator
    changed = grid._complete_byte_row(0, "D9 00 00 00", 0)
    assert changed is not None
    rows = grid.export_rows()
    coordinator.accept_synchronous_rows([changed, rows[1]])

    assert coordinator._bytes_authoritative_lines == {0}


def test_alt_s_failure_keeps_the_previous_version_context_dirty():
    previous = BinaryWorkbenchTabContextDTO(
        tab_id="tab",
        kind="assembly",
        display_name="source.asm",
        source_path="source.asm",
        active_version_name="v1",
        version_dirty=True,
    )

    class Tabs:
        restored = None
        marked = False
        ensure_calls = 0
        update_options = None

        def ensure_current_consistent(self, _reason):
            self.ensure_calls += 1
            return ConsistencyBarrierResult(True)

        def current_context(self):
            return previous

        def update_current_version(self, *_args, **kwargs):
            self.update_options = kwargs
            return True

        def save_current_workspace(self):
            return False

        def _set_current_context_without_page_reload(self, context):
            self.restored = context

        def mark_initial_version_saved(self, _tab_id):
            self.marked = True

        def backup_default_version_if_due(self):
            raise AssertionError("a failed save cannot advance the backup counter")

    class Window:
        tabs = Tabs()
        statuses = []

        def _set_editor_popups_suppressed(self, _enabled):
            pass

        def _hide_editor_popups(self):
            pass

        def _show_status(self, message, *_args):
            self.statuses.append(message)

        def _show_warning_status(self, message):
            self.statuses.append(message)

    window = Window()
    BinaryWorkbenchWindowVersionMixin._update_version(window)

    assert window.tabs.restored is previous
    assert window.tabs.marked is False
    assert window.tabs.ensure_calls == 1
    assert window.tabs.update_options["ensure_consistency"] is False
    assert previous.version_dirty is True
    assert window.statuses[-1] == "Unable to persist the current version atomically."
