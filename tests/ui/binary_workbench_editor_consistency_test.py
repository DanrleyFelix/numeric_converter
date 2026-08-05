import os
import inspect
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
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
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.consistency import (
    coordinator as coordinator_module,
)
from src.presentation.ui.components.binary_workbench.editor.consistency.coordinator import (
    EditorConsistencyCoordinator,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.page import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
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
    assert coordinator._visual_worker is None
    assert called == []
    coordinator._clear_collector()


def test_contents_change_handler_contains_no_expensive_derivation_path():
    source = inspect.getsource(EditorConsistencyCoordinator.collect_contents_change)

    assert "toPlainText" not in source
    assert "_derive_lines" not in source
    assert "_start_visual" not in source
    assert "_start_semantic" not in source
    assert "assemble" not in source


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


def test_visual_and_semantic_timers_use_the_revised_deadlines():
    grid = _grid(["nop"])
    coordinator = grid._consistency_coordinator

    assert coordinator._visual_quiet.interval() == 80
    assert coordinator._visual_maximum.interval() == 280
    assert coordinator._semantic_timer.interval() == 1000
    assert coordinator._visual_quiet.isSingleShot()
    assert coordinator._visual_maximum.isSingleShot()
    assert coordinator._semantic_timer.isSingleShot()


def test_quiet_and_maximum_timer_race_starts_only_one_visual_job(monkeypatch):
    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator
    jobs = []
    monkeypatch.setattr(coordinator._pool, "start_visual", jobs.append)
    coordinator._dirty_ranges = (coordinator_module.DirtyRange(0, 1),)
    coordinator._dirty_from_line = 0

    coordinator._start_visual()
    coordinator._start_visual()

    assert len(jobs) == 1


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
    assert coordinator._semantic_timer.isActive() is False
    assert coordinator._semantic_worker is None


def test_inserted_instruction_updates_offsets_immediately_without_a_redundant_job(monkeypatch):
    grid = _grid(["nop", "nop"], references=True)
    coordinator = grid._consistency_coordinator
    jobs = []
    def tracked(worker):
        jobs.append(worker)

    monkeypatch.setattr(coordinator._pool, "start_visual", tracked)
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
    assert jobs == []


def test_invalid_symbol_is_cleared_and_redistributed_immediately(monkeypatch):
    grid = _grid(["nop", "nop", "nop"], references=True)
    coordinator = grid._consistency_coordinator
    jobs = []
    monkeypatch.setattr(coordinator._pool, "start_visual", jobs.append)
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
    assert jobs == []


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


def test_undo_keeps_the_assembly_cursor_and_shared_viewport_near_the_edit():
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

    assert grid.instructions.textCursor().blockNumber() == min(
        cursor_row,
        grid.instructions.document().blockCount() - 1,
    )
    assert grid.scrollbar.value() == min(scroll_before, grid.scrollbar.maximum())
    assert grid.instructions.textCursor().blockNumber() < (
        grid.instructions.document().blockCount() - 1
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
def test_large_structural_edit_projects_current_batch_immediately(monkeypatch, operation):
    lines = ["entry:", *["nop" for _ in range(300)]]
    grid = _grid(lines, references=True)
    coordinator = grid._consistency_coordinator
    jobs = []
    monkeypatch.setattr(coordinator._pool, "start_visual", jobs.append)
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
    immediate_last = min(len(rows) - 1, 10 + 255)
    _assert_valid_file_offsets(rows[: immediate_last + 1])
    assert _editor_line(grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE], 10)
    assert _editor_line(grid._offset_editors[_REFERENCE], 10)
    assert all(_editor_line(editor, 10) for editor in (grid.raw_instructions, grid.bytes, grid.instructions))

    coordinator._visual_quiet.stop()
    coordinator._visual_maximum.stop()
    coordinator._start_visual()
    assert len(jobs) == 1
    jobs[0].run()
    _app().processEvents()

    rows = grid.export_rows()
    _assert_valid_file_offsets(rows)
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
def test_barrier_rejects_semantic_results_from_before_alt_s_or_f5(reason):
    grid = _grid(["nop", "nop"])
    coordinator = grid._consistency_coordinator
    stale = SemanticResult(
        coordinator.owner,
        coordinator.source_revision,
        coordinator.semantic_generation,
        (
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "DE AD BE EF"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "nop", "DE AD BE EF"),
        ),
        {},
    )

    result = coordinator.ensure_consistent(reason)
    current = tuple(row.bytes_text for row in grid.export_rows())
    coordinator._apply_semantic_result(stale)

    assert result.success is True
    assert result.snapshot is not None
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
