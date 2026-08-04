import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import build_rows_from_instructions
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.debugger.directives.parser import parse_debugger_directives
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid


SOURCE_LINES = [
    "* virtual_memory_range 0x80000000 0x801FFFFF",
    "* import current_file 0x80000000",
    "* define $sp 0x801FFFF0",
    "* define $pc 0x80000000",
    "start: nop",
    "nop",
]
REFERENCE_OFFSET = "ram"


def _app() -> QApplication:
    """Return the shared offscreen Qt application."""

    return QApplication.instance() or QApplication([])


def _grid() -> BinaryWorkbenchGrid:
    """Create an assembly grid containing debugger directives and code."""

    _app()
    rows = build_rows_from_instructions(
        SOURCE_LINES,
        [BINARY_WORKBENCH_TEXT.FILE, REFERENCE_OFFSET],
        {REFERENCE_OFFSET: "0x8000F800"},
    )
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
    grid.load_rows(
        [
            BINARY_WORKBENCH_TEXT.FILE,
            REFERENCE_OFFSET,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.DECODED_TEXT,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        rows,
        reference_offset_bases={REFERENCE_OFFSET: "0x8000F800"},
    )
    grid.resize(1100, 300)
    grid.show()
    grid.set_label_folding_enabled(True)
    _app().processEvents()
    return grid


def _editors(grid: BinaryWorkbenchGrid):
    """Return every complete row projection synchronized by folding."""

    return (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    )


def test_directive_fold_is_visual_only_and_keeps_debugger_source_complete():
    """Hide directive projections without mutating rows or debugger input."""

    grid = _grid()
    source = grid.instructions.toPlainText()
    rows = grid.export_rows()
    parsed_before = parse_debugger_directives(source.splitlines())

    grid.instructions.request_label_fold_toggle(0)
    _app().processEvents()

    assert grid.instructions._directive_fold_region == (0, True)
    for editor in _editors(grid):
        assert editor.document().findBlockByNumber(0).isVisible() is True
        assert all(
            editor.document().findBlockByNumber(row).isVisible() is False
            for row in range(1, 4)
        )
        assert editor.document().findBlockByNumber(4).isVisible() is True
    assert grid.instructions.toPlainText() == source
    assert grid.export_rows() == rows
    assert parse_debugger_directives(grid.instructions.toPlainText().splitlines()) == parsed_before
    assert grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE].document().findBlockByNumber(4).text() == "0x00000000"
    barrier = grid.ensure_consistent("debugger")
    assert barrier.success is True
    assert barrier.snapshot is not None
    assert [row.instruction for row in barrier.snapshot.rows] == SOURCE_LINES
    assert grid.instructions.document().findBlockByNumber(1).isVisible() is False
    for editor in grid._offset_editors.values():
        dash_visibility = {
            label.property("offsetBlock"): label.isVisible()
            for label in editor._dash_labels
        }
        assert dash_visibility == {0: True, 1: False, 2: False, 3: False}

    grid.instructions.request_label_fold_toggle(0)
    _app().processEvents()
    assert all(editor.document().findBlockByNumber(1).isVisible() for editor in _editors(grid))
    for editor in grid._offset_editors.values():
        assert {
            label.property("offsetBlock"): label.isVisible()
            for label in editor._dash_labels
        } == {0: True, 1: True, 2: True, 3: True}


def test_directive_and_label_folds_keep_independent_visibility_states():
    """Expanding directives must not expand a separately collapsed label."""

    grid = _grid()
    grid.toggle_directive_fold()
    grid.toggle_label_fold("start")

    assert grid.instructions.document().findBlockByNumber(1).isVisible() is False
    assert grid.instructions.document().findBlockByNumber(5).isVisible() is False

    grid.toggle_directive_fold()

    assert grid.instructions.document().findBlockByNumber(1).isVisible() is True
    assert grid.instructions.document().findBlockByNumber(5).isVisible() is False
