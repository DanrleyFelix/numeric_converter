import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import build_rows_from_instructions
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchEditRulesDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.table import (
    BinaryWorkbenchGrid,
)

_APP = None
_REFERENCES = ["Reference Offset A", "Reference Offset B"]

def _app() -> QApplication:
    """Return the shared offscreen application."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _grid(lines: list[str]) -> BinaryWorkbenchGrid:
    """Create a visible editable grid containing every column kind."""

    app = _app()
    offsets = [BINARY_WORKBENCH_TEXT.FILE, *_REFERENCES]
    bases = {name: f"0x{0x80000000 + index * 0x1000:08X}" for index, name in enumerate(_REFERENCES)}
    rows = build_rows_from_instructions(
        lines,
        offsets,
        bases,
    )
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
    grid.resize(1200, 220)
    grid.show()
    grid.set_label_folding_enabled(True)
    app.processEvents()
    return grid


def _editors(grid: BinaryWorkbenchGrid):
    """Return every row-aligned editor in display order."""

    return (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    )


def test_three_labels_keep_every_visible_column_scrolled_together():
    """Restore full synchronized scrolling after expanding the final label."""

    lines = [
        line for label in range(3)
        for line in [f"label_{label}:", *(["nop"] * 18)]
    ]
    grid = _grid(lines)
    grid.toggle_label_fold("label_2")
    _app().processEvents()
    collapsed_maximum = grid.scrollbar.maximum()
    grid.toggle_label_fold("label_2")
    _app().processEvents()
    assert grid.scrollbar.maximum() > collapsed_maximum
    grid.set_visible_offset(grid.scrollbar.maximum())
    _app().processEvents()

    expected = grid.scrollbar.value() // 4
    assert expected > 0
    assert all(editor.verticalScrollBar().maximum() >= expected for editor in _editors(grid))
    assert {
        editor.verticalScrollBar().value()
        for editor in _editors(grid)
        if editor.isVisible()
    } == {expected}
    assert {
        editor.firstVisibleBlock().blockNumber()
        for editor in _editors(grid)
        if editor.isVisible()
    } == {grid.instructions.firstVisibleBlock().blockNumber()}
    grid.raw_shell.hide()
    shared_value = grid.scrollbar.value()
    grid.raw_instructions.verticalScrollBar().setValue(0)
    assert grid.scrollbar.value() == shared_value
    grid.set_visible_offset(shared_value)
    grid.raw_shell.show()
    assert grid.raw_instructions.verticalScrollBar().value() == expected

def test_deleting_label_expands_previous_owner_of_merged_rows():
    """Reveal merged rows and preserve column scrolling after label deletion."""

    body = ["nop"] * 18
    grid = _grid(["top:", *body, "middle:", *body, "bottom:", *body])
    grid.toggle_label_fold("top")
    grid.toggle_label_fold("middle")
    grid.toggle_label_fold("bottom")
    middle = grid.instructions.document().findBlockByNumber(19)
    cursor = QTextCursor(middle)
    cursor.setPosition(middle.next().position(), QTextCursor.KeepAnchor)
    grid.instructions.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )
    QTest.qWait(120)

    assert "middle:" not in grid.instructions.toPlainText().splitlines()
    assert len({editor.document().blockCount() for editor in _editors(grid)}) == 1
    assert "top" not in grid._collapsed_labels
    grid.set_visible_offset(grid.scrollbar.maximum())
    _app().processEvents()
    expected = grid.scrollbar.value() // 4
    assert {editor.verticalScrollBar().value() for editor in _editors(grid)} == {expected}
    assert len({editor.firstVisibleBlock().blockNumber() for editor in _editors(grid)}) == 1

def test_editing_hidden_label_body_expands_its_owner():
    """Expand a folded region before a key mutates one of its hidden rows."""

    grid = _grid(["top:", "nop", "bottom:", "nop"])
    grid.toggle_label_fold("top")
    hidden = grid.instructions.document().findBlockByNumber(1)
    cursor = QTextCursor(hidden)
    cursor.movePosition(QTextCursor.EndOfBlock)
    grid.instructions.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_X, Qt.NoModifier, "x"),
    )
    _app().processEvents()

    assert grid.instructions.document().findBlockByNumber(1).text() == "nopx"
    assert "top" not in grid._collapsed_labels
    assert grid.instructions.document().findBlockByNumber(1).isVisible()


def test_raw_instruction_rerender_preserves_folds_with_invalid_jump():
    """Keep Raw Instructions folded when an invalid source row triggers repaint."""

    grid = _grid([
        "first:",
        "nop",
        "second:",
        "nop",
        "third:",
        "j @return",
    ])
    grid.toggle_label_fold("first")
    grid.toggle_label_fold("second")

    grid._render_raw_instructions()
    _app().processEvents()

    raw_visibility = [
        grid.raw_instructions.document().findBlockByNumber(row).isVisible()
        for row in range(len(grid._rows))
    ]
    instruction_visibility = [
        grid.instructions.document().findBlockByNumber(row).isVisible()
        for row in range(len(grid._rows))
    ]
    assert raw_visibility == instruction_visibility
    assert raw_visibility[1] is False
    assert raw_visibility[3] is False


def test_new_label_marker_is_published_in_the_same_qt_cycle():
    """Expose a newly typed label without waiting for another source edit."""

    grid = _grid(["nop", "nop", "nop"])
    block = grid.instructions.document().findBlockByNumber(0)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.instructions.setTextCursor(cursor)

    QTest.keyClicks(grid.instructions, "new_label:")
    _app().processEvents()

    assert any(
        region.label == "new_label" for region in grid._label_fold_regions
    ), grid.instructions.toPlainText()
    assert grid.instructions._label_fold_regions[0][0] == "new_label"


def test_fold_refresh_repairs_visible_blocks_with_zero_layout_lines():
    """Normalize a visible block inherited from a previously hidden neighbour."""

    grid = _grid(["first:", "nop", "second:", "nop", "third:", "nop"])
    block = grid.instructions.document().findBlockByNumber(3)
    block.setVisible(True)
    block.setLineCount(0)

    grid._refresh_label_folding()

    assert block.isVisible() is True
    assert block.lineCount() == 1


def test_collapsed_scroll_range_ignores_transient_editor_maximums():
    """Derive the shared range from logical rows while Qt layouts settle."""

    body = ["nop"] * 18
    grid = _grid(["first:", *body, "second:", *body, "third:", *body])
    grid.toggle_label_fold("first")
    grid.raw_instructions.verticalScrollBar().setMaximum(0)
    expected = max(0, grid._scrollable_total_size() - grid.visible_size())

    grid._configure_scrollbar()

    assert expected > 0
    assert grid.scrollbar.maximum() == expected


def test_three_quick_collapses_keep_the_last_label_reachable_after_expansion():
    """Keep every logical row reachable across unsettled folding layouts."""

    body = ["nop"] * 18
    grid = _grid([
        "first:", *body,
        "second:", *body,
        "third:", *body,
        "fourth:", *body,
    ])
    for label in ("first", "second", "third", "fourth"):
        grid.toggle_label_fold(label)
    grid.toggle_label_fold("second")
    _app().processEvents()

    expected = max(0, grid._scrollable_total_size() - grid.visible_size())
    assert grid.scrollbar.maximum() == expected
    grid.set_visible_offset(expected)
    _app().processEvents()

    fourth_row = next(
        region.label_row
        for region in grid._label_fold_regions
        if region.label == "fourth"
    )
    assert grid.instructions.document().findBlockByNumber(fourth_row).isVisible()
    assert any(
        marker[0] == fourth_row
        for marker in grid.instructions.visible_label_fold_markers()
    )
    masks = [
        tuple(
            editor.document().findBlockByNumber(row).isVisible()
            for row in range(editor.document().blockCount())
        )
        for editor in _editors(grid)
    ]
    assert len(set(masks)) == 1


def test_new_rows_near_folded_labels_keep_documents_and_scroll_range_aligned():
    """Commit structural source insertion without orphaning a Qt layout row."""

    body = ["nop"] * 8
    grid = _grid(["first:", *body, "second:", *body, "third:", *body])
    grid.toggle_label_fold("first")
    grid.toggle_label_fold("third")
    insertion_row = 9 + len(body) - 1
    block = grid.instructions.document().findBlockByNumber(insertion_row)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.instructions.setTextCursor(cursor)

    QTest.keyClick(grid.instructions, Qt.Key_Return)
    _app().processEvents()

    counts = {editor.document().blockCount() for editor in _editors(grid)}
    assert counts == {len(grid._rows)}
    expected = max(0, grid._scrollable_total_size() - grid.visible_size())
    assert grid.scrollbar.maximum() == expected
    masks = [
        tuple(
            editor.document().findBlockByNumber(row).isVisible()
            for row in range(editor.document().blockCount())
        )
        for editor in _editors(grid)
    ]
    assert len(set(masks)) == 1
