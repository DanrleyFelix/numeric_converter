import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchRowDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.consistency.projection import (
    apply_bytes_line_contents,
    apply_semantic_projection,
)
from src.presentation.ui.components.binary_workbench.editor.table import (
    BinaryWorkbenchGrid,
)


def _grid(rows: list[BinaryWorkbenchRowDTO]) -> BinaryWorkbenchGrid:
    """Create one editable static grid with the consistency coordinator active."""

    app = QApplication.instance() or QApplication([])
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.load_rows(
        [
            BINARY_WORKBENCH_TEXT.FILE,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        rows,
    )
    grid._test_app = app
    return grid


def _key(editor, key: int, modifiers=Qt.NoModifier) -> None:
    """Deliver one deterministic key press to an editor."""

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, key, modifiers),
    )


def _text_key(editor, key: int, text: str) -> None:
    """Deliver one deterministic printable key press to an editor."""

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text),
    )


def test_eventual_semantic_projection_preserves_bytes_structural_undo():
    """A semantic projection must not discard a user row-removal command."""

    rows = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
        BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
        BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
    ]
    grid = _grid(rows)
    empty = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(empty)
    cursor.setPosition(empty.position())
    grid.bytes.setTextCursor(cursor)

    _key(grid.bytes, Qt.Key_Backspace)
    apply_semantic_projection(grid, (), ())
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()

    assert grid.bytes.document().blockCount() == 3
    assert grid.bytes.document().findBlockByNumber(1).text() == ""
    assert [row.instruction for row in grid._rows] == ["nop", "", "jr $ra"]


def test_undo_skips_automatic_bytes_projection_and_reverts_user_edit():
    """Derived Bytes refreshes must never become a user-visible Undo action."""

    grid = _grid([
        BinaryWorkbenchRowDTO(
            {"File": "0x00000000"},
            "addiu $a0, $a0, 0",
            "00 00 84 24",
        )
    ])
    block = grid.bytes.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position())
    cursor.setPosition(block.position() + 2, QTextCursor.KeepAnchor)
    grid._updating = True
    try:
        cursor.insertText("01")
    finally:
        grid._updating = False
    assert grid.bytes.toPlainText() == "01 00 84 24"

    projected = BinaryWorkbenchRowDTO(
        {"File": "0x00000000"},
        "addiu $a0, $a0, 2",
        "02 00 84 24",
    )
    apply_semantic_projection(grid, (), ((0, projected),))
    assert grid.bytes.toPlainText() == "02 00 84 24"

    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    assert grid.bytes.toPlainText() == "00 00 84 24"
    _key(grid.bytes, Qt.Key_Y, Qt.ControlModifier)
    assert grid.bytes.toPlainText() == "01 00 84 24"
    _key(grid.bytes, Qt.Key_Y, Qt.ControlModifier)
    assert grid.bytes.toPlainText() == "01 00 84 24"


def test_undo_does_not_remove_projection_when_no_user_command_exists():
    """An automatic refresh alone must leave logical Undo unavailable."""

    grid = _grid([
        BinaryWorkbenchRowDTO(
            {"File": "0x00000000"},
            "addiu $a0, $a0, 0",
            "00 00 84 24",
        )
    ])
    projected = BinaryWorkbenchRowDTO(
        {"File": "0x00000000"},
        "addiu $a0, $a0, 2",
        "02 00 84 24",
    )
    apply_semantic_projection(grid, (), ((0, projected),))

    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)

    assert grid.bytes.toPlainText() == "02 00 84 24"


def test_assembly_undo_skips_automatic_projection_from_bytes():
    """Bytes-origin projection must not become Assembly's next Undo command."""

    grid = _grid([
        BinaryWorkbenchRowDTO(
            {"File": "0x00000000"},
            "addiu $a0, $a0, 0",
            "00 00 84 24",
        )
    ])
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid._updating = True
    try:
        cursor.insertText("addiu $a0, $a0, 1")
    finally:
        grid._updating = False

    apply_bytes_line_contents(
        grid,
        ((
            0,
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            ),
        ),),
    )
    assert grid.instructions.toPlainText().casefold() == "addiu $a0, $a0, 2"

    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    assert grid.instructions.toPlainText().casefold() == "addiu $a0, $a0, 0"
    _key(grid.instructions, Qt.Key_Y, Qt.ControlModifier)
    assert grid.instructions.toPlainText().casefold() == "addiu $a0, $a0, 1"


def test_next_backspace_is_not_overwritten_by_delayed_row_cursor_restore():
    """Continue deleting the prior row immediately after removing an empty row."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    current = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(current)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    for _unused in range(len("08 00 E0 03")):
        _key(grid.bytes, Qt.Key_Backspace)
    _key(grid.bytes, Qt.Key_Backspace)
    QApplication.processEvents()

    assert grid.bytes.textCursor().blockNumber() == 0
    assert grid.bytes.textCursor().positionInBlock() == len("00 00 00 00")

    _key(grid.bytes, Qt.Key_Backspace)
    QApplication.processEvents()

    assert grid.bytes.toPlainText() == "00 00 00 0"
    assert grid.bytes.textCursor().positionInBlock() == len("00 00 00 0")


def test_bytes_row_removal_undo_restores_structure_then_each_deleted_character():
    """Keep the row splice separate from every prior byte deletion command."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
            BinaryWorkbenchRowDTO({"File": "0x00000008"}, "nop", "00 00 00 00"),
        ]
    )
    current = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(current)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    deletion_states = []
    for _unused in range(len("08 00 E0 03")):
        _key(grid.bytes, Qt.Key_Backspace)
        deletion_states.append(
            grid.bytes.document().findBlockByNumber(1).text()
        )
    _key(grid.bytes, Qt.Key_Backspace)
    QApplication.processEvents()
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()

    assert grid.bytes.toPlainText().splitlines() == [
        "00 00 00 00",
        "",
        "00 00 00 00",
    ]
    assert [row.instruction.casefold() for row in grid._rows] == [
        "nop",
        "",
        "nop",
    ]
    assert grid.bytes.textCursor().blockNumber() == 1
    assert grid.bytes.textCursor().positionInBlock() == 0

    restored_states = []
    for _unused in range(len("08 00 E0 03")):
        _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
        QApplication.processEvents()
        restored_states.append(
            grid.bytes.document().findBlockByNumber(1).text()
        )

    assert restored_states == [
        *reversed(deletion_states[:-1]),
        "08 00 E0 03",
    ], (deletion_states, restored_states)
    assert grid.bytes.document().findBlockByNumber(1).text() == "08 00 E0 03"
    assert grid._rows[1].instruction.casefold() == "jr $ra"


def test_bytewise_row_removal_undo_keeps_following_label_attached():
    """Restore an empty row first while keeping the following label attached."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
            BinaryWorkbenchRowDTO({"File": "-"}, "tail:", ""),
            BinaryWorkbenchRowDTO({"File": "0x00000008"}, "nop", "00 00 00 00"),
        ]
    )
    grid.set_label_folding_enabled(True)
    current = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(current)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    for _unused in range(len("08 00 E0 03")):
        _key(grid.bytes, Qt.Key_Backspace)
    _key(grid.bytes, Qt.Key_Backspace)
    QApplication.processEvents()

    assert grid.instructions.document().findBlockByNumber(1).text() == "tail:"
    assert grid.instructions._label_fold_regions == {1: ("tail", False)}
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()

    assert grid.bytes.document().findBlockByNumber(1).text() == ""
    assert grid.instructions.document().findBlockByNumber(2).text() == "tail:"
    assert grid.instructions._label_fold_regions == {2: ("tail", False)}
    assert grid.bytes.textCursor().blockNumber() == 1
    assert grid.bytes.textCursor().positionInBlock() == 0

    for _unused in range(len("08 00 E0 03")):
        _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
        QApplication.processEvents()

    assert grid.bytes.document().findBlockByNumber(1).text() == "08 00 E0 03"
    assert grid.instructions.document().findBlockByNumber(2).text() == "tail:"
    assert grid.instructions._label_fold_regions == {2: ("tail", False)}


def test_no_shift_label_edit_refreshes_fold_marker_without_waiting():
    """Keep a fold marker attached to its renamed label in the same edit event."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, "entry:", ""),
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    grid.set_label_folding_enabled(True)
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    cursor.insertText("renamed:")

    assert grid.instructions._label_fold_regions == {0: ("renamed", False)}


def test_no_shift_delete_undo_preserves_directives_and_label_markers():
    """Undo a protected-mode edit without losing directives or moving fold controls."""

    source = [
        "* virtual_memory_range 0x80000000 0x801FFFFF",
        "* define $sp 0x801FFFF0",
        "entry:",
        "addiu $a0, $a0, 2",
        "jr $ra",
    ]
    rows = [
        BinaryWorkbenchRowDTO({"File": "-"}, source[0], ""),
        BinaryWorkbenchRowDTO({"File": "-"}, source[1], ""),
        BinaryWorkbenchRowDTO({"File": "-"}, source[2], ""),
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, source[3], "02 00 84 24"),
        BinaryWorkbenchRowDTO({"File": "0x00000004"}, source[4], "08 00 E0 03"),
    ]
    grid = _grid(rows)
    grid.set_label_folding_enabled(True)
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    block = grid.instructions.document().findBlockByNumber(3)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.instructions.setTextCursor(cursor)

    _key(grid.instructions, Qt.Key_Delete)
    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    QTest.qWait(100)

    lines = grid.instructions.toPlainText().splitlines()
    assert lines[:2] == source[:2]
    assert lines[2] == "entry:"
    assert grid.instructions._label_fold_regions == {2: ("entry", False)}


def test_blocked_no_shift_delete_does_not_replace_previous_undo():
    """A rejected row deletion must not become an Undoable projection edit."""

    source = [
        "* virtual_memory_range 0x80000000 0x801FFFFF",
        "* define $sp 0x801FFFF0",
        "entry:",
        "addiu $a0, $a0, 2",
        "jr $ra",
    ]
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, source[0], ""),
            BinaryWorkbenchRowDTO({"File": "-"}, source[1], ""),
            BinaryWorkbenchRowDTO({"File": "-"}, source[2], ""),
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, source[3], "02 00 84 24"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, source[4], "08 00 E0 03"),
        ]
    )
    grid.set_label_folding_enabled(True)
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    editable = grid.instructions.document().findBlockByNumber(3)
    cursor = QTextCursor(editable)
    cursor.setPosition(editable.position() + len(editable.text()) - 1)
    cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.KeepAnchor)
    grid.instructions.setTextCursor(cursor)
    _text_key(grid.instructions, Qt.Key_3, "3")
    QApplication.processEvents()
    assert grid.instructions.document().isUndoAvailable()
    undo_steps = grid.instructions.document().availableUndoSteps()
    blocked = grid.instructions.document().findBlockByNumber(4)
    cursor = QTextCursor(blocked)
    cursor.setPosition(blocked.position())
    grid.instructions.setTextCursor(cursor)

    _key(grid.instructions, Qt.Key_Backspace)
    QTest.qWait(100)
    assert grid.instructions.document().availableUndoSteps() == undo_steps
    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()

    restored = grid.instructions.toPlainText().splitlines()
    assert restored[:3] == source[:3]
    assert restored[3].casefold() == source[3].casefold()
    assert restored[4].casefold() == source[4].casefold()
    assert grid.instructions._label_fold_regions == {2: ("entry", False)}


def test_bytes_row_delete_undo_never_removes_leading_directives():
    """Restore one Bytes row without splicing source-only directive rows."""

    source = [
        "* virtual_memory_range 0x80000000 0x801FFFFF",
        "* define $sp 0x801FFFF0",
        "entry:",
        "addiu $a0, $a0, 2",
        "jr $ra",
    ]
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, source[0], ""),
            BinaryWorkbenchRowDTO({"File": "-"}, source[1], ""),
            BinaryWorkbenchRowDTO({"File": "-"}, source[2], ""),
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, source[3], "02 00 84 24"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, source[4], "08 00 E0 03"),
        ]
    )
    grid.set_label_folding_enabled(True)
    block = grid.bytes.document().findBlockByNumber(3)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)

    _key(grid.bytes, Qt.Key_Delete)
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()

    restored = grid.instructions.toPlainText().splitlines()
    assert restored[:3] == source[:3]
    assert [line.casefold() for line in restored[3:]] == [
        line.casefold() for line in source[3:]
    ]
    assert grid.instructions._label_fold_regions == {2: ("entry", False)}


def test_structural_bytes_undo_and_redo_respect_current_shifting_rule():
    """Block only the structural history command and retain it for later."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    block = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)
    _key(grid.bytes, Qt.Key_Delete)
    QApplication.processEvents()
    assert grid.bytes.document().blockCount() == 1

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    undo_steps = grid.bytes.document().availableUndoSteps()
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()

    assert grid.bytes.document().blockCount() == 1
    assert grid.bytes.document().availableUndoSteps() == undo_steps
    assert warnings[-1] == BINARY_WORKBENCH_TEXT.STATUS_HISTORY_BYTE_SHIFTING_DISABLED

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()
    assert grid.bytes.document().blockCount() == 2
    assert grid.bytes.document().isRedoAvailable()

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    QApplication.processEvents()
    assert grid.bytes.document().blockCount() == 2
    assert grid.bytes.document().isRedoAvailable()

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    _key(grid.bytes, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    QApplication.processEvents()
    assert grid.bytes.document().blockCount() == 1


def test_no_shift_rule_allows_a_new_assembly_line_to_become_valid():
    """A newly inserted source row remains the established no-shift exception."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.instructions.setTextCursor(cursor)

    _key(grid.instructions, Qt.Key_Return)
    _text_key(grid.instructions, Qt.Key_N, "n")
    _text_key(grid.instructions, Qt.Key_O, "o")
    _text_key(grid.instructions, Qt.Key_P, "p")
    QTest.qWait(100)
    QApplication.processEvents()

    assert grid.instructions.toPlainText().splitlines()[1].casefold() == "nop"
    assert grid.bytes.toPlainText().splitlines()[1] == "00 00 00 00"
    assert len(grid._rows) == 3


def test_structural_assembly_undo_and_redo_respect_current_shifting_rule():
    """Assembly history is blocked only while its row splice violates Rules."""

    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    first = grid.instructions.document().firstBlock()
    second = first.next()
    cursor = QTextCursor(grid.instructions.document())
    cursor.setPosition(first.position())
    cursor.setPosition(second.position(), QTextCursor.MoveMode.KeepAnchor)
    grid.instructions.setTextCursor(cursor)

    _key(grid.instructions, Qt.Key_Delete)
    QApplication.processEvents()
    assert grid.instructions.document().blockCount() == 1

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    undo_steps = grid.instructions.document().availableUndoSteps()
    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()
    assert grid.instructions.document().blockCount() == 1
    assert grid.instructions.document().availableUndoSteps() == undo_steps
    assert warnings[-1] == BINARY_WORKBENCH_TEXT.STATUS_HISTORY_BYTE_SHIFTING_DISABLED

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()
    assert grid.instructions.document().blockCount() == 2

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    QApplication.processEvents()
    assert grid.instructions.document().blockCount() == 2

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    _key(grid.instructions, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    QApplication.processEvents()
    assert grid.instructions.document().blockCount() == 1
