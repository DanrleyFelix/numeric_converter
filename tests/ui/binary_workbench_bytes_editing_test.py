import os
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt, qInstallMessageHandler
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchRowDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.table import (
    BinaryWorkbenchGrid,
)

_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _grid(rows: list[BinaryWorkbenchRowDTO]) -> BinaryWorkbenchGrid:
    _app()
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.load_rows(
        [
            BINARY_WORKBENCH_TEXT.FILE,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.DECODED_TEXT,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        rows,
    )
    return grid


def test_bytes_and_offset_columns_are_centered_with_double_visual_byte_spacing():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000", "ram": "0x8000F800"},
                "nop",
                "00 00 00 00",
            )
        ]
    )
    QApplication.processEvents()

    assert grid.bytes.document().defaultTextOption().alignment() == Qt.AlignCenter
    assert all(
        editor.document().defaultTextOption().alignment() == Qt.AlignCenter
        for editor in grid._offset_editors.values()
    )
    spacing_ranges = [
        value
        for value in grid.bytes.document().firstBlock().layout().formats()
        if value.format.fontWordSpacing() > 0
    ]
    assert [(value.start, value.length) for value in spacing_ranges] == [
        (2, 1),
        (5, 1),
        (8, 1),
    ]


def test_source_only_rows_leave_bytes_and_raw_empty_but_keep_offset_dashes():
    rows = [
        BinaryWorkbenchRowDTO({"File": "-"}, "* define $sp 0x801FFFF0", ""),
        BinaryWorkbenchRowDTO({"File": "-"}, "; note", ""),
        BinaryWorkbenchRowDTO({"File": "-"}, "entry:", ""),
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "entry2: nop", "00 00 00 00"),
    ]
    grid = _grid(rows)

    for editor in grid._offset_editors.values():
        assert [editor.document().findBlockByNumber(i).text() for i in range(3)] == ["-"] * 3
        assert editor._dash_blocks == {0, 1, 2}
    for editor in (grid.raw_instructions, grid.bytes):
        assert [editor.document().findBlockByNumber(i).text() for i in range(3)] == [""] * 3
        assert editor._dash_blocks == set()
    assert grid.bytes.document().findBlockByNumber(3).text() == "00 00 00 00"


def test_rejected_label_edit_keeps_every_column_on_the_same_leading_row():
    rows = [
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "nop",
                "00 00 00 00",
            )
            for index in range(24)
        ],
    ]
    grid = _grid(rows)
    grid.resize(700, 240)
    grid.show()
    cursor = QTextCursor(grid.bytes.document().findBlockByNumber(0))
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )
    QApplication.processEvents()

    editors = (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.instructions,
    )
    assert {editor.document().blockCount() for editor in editors} == {len(rows)}
    assert {editor.firstVisibleBlock().blockNumber() for editor in editors} == {0}
    assert grid.bytes.toPlainText().splitlines()[:2] == ["", "00 00 00 00"]


def test_label_instruction_byte_edit_preserves_label_without_warning():
    grid = _grid(
        [BinaryWorkbenchRowDTO({"File": "0x00000000"}, "entry: nop", "00 00 00 00")]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    grid.bytes.setPlainText("01 00 00 00")

    assert grid.bytes.toPlainText() == "01 00 00 00"
    assert grid.instructions.toPlainText().startswith("entry:")
    assert warnings == []


def test_label_only_row_accepts_bytes_but_cannot_be_removed_from_bytes():
    grid = _grid(
        [BinaryWorkbenchRowDTO({"File": "-"}, "entry:", "")]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    QApplication.clipboard().setText("00 00 00 00")
    grid.bytes.setFocus()

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )

    assert grid.bytes.toPlainText() == "00 00 00 00"
    assert grid.instructions.toPlainText().lower().startswith("entry:")
    block = grid.bytes.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert grid.bytes.toPlainText() == "00 00 00 00"
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_BYTES_ROW_REMOVAL_BLOCKED]


def test_directive_row_rejects_direct_bytes_edit():
    grid = _grid(
        [BinaryWorkbenchRowDTO({"File": "-"}, "* define $sp 0x801FFFF0", "")]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    QApplication.clipboard().setText("00 00 00 00")

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )

    assert grid.bytes.toPlainText() == ""
    assert grid.instructions.toPlainText() == "* define $sp 0x801FFFF0"
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_BYTES_ASSEMBLY_ONLY]


def test_commented_instruction_byte_edit_preserves_comment():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000"},
                "addiu $t0, $zero, 1 ; keep",
                "01 00 08 24",
            ),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "nop", "00 00 00 00"),
        ]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    grid.bytes.setPlainText("02 00 08 24\n00 00 00 00")

    assert grid.bytes.toPlainText().splitlines()[0] == "02 00 08 24"
    assert grid.instructions.toPlainText().splitlines()[0].endswith("; keep")
    assert warnings == []


def test_removing_plain_instruction_byte_row_is_allowed():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO(
                {"File": "0x00000004"},
                "addiu $t0, $zero, 1 ; keep",
                "01 00 08 24",
            ),
            BinaryWorkbenchRowDTO({"File": "0x00000008"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    grid.bytes.setPlainText("01 00 08 24\n08 00 E0 03")

    assert grid.bytes.toPlainText() == "01 00 08 24\n08 00 E0 03"
    assert len(grid._rows) == 2
    assert grid.instructions.toPlainText().splitlines()[0].endswith("; keep")
    assert warnings == []


def test_deleting_complete_plain_instruction_bytes_removes_the_row():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    block = grid.bytes.document().findBlockByNumber(0)
    cursor = QTextCursor(block)
    cursor.setPosition(block.position())
    cursor.setPosition(block.position() + len(block.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert len(grid._rows) == 1
    assert grid._rows[0].instruction == "jr $ra"
    assert grid._rows[0].offsets["File"] == "0x00000000"
    assert grid.bytes.toPlainText() == "08 00 E0 03"


def test_deleting_last_byte_row_keeps_caret_on_the_new_last_row():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "nop",
                "00 00 00 00",
            )
            for index in range(60)
        ]
    )
    grid.resize(800, 240)
    grid.show()
    grid.scrollbar.setValue(grid.scrollbar.maximum())
    block = grid.bytes.document().lastBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position())
    cursor.setPosition(block.position() + len(block.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)
    scroll_before = grid.scrollbar.value()

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )
    QApplication.processEvents()

    assert len(grid._rows) == 59
    assert grid.bytes.textCursor().blockNumber() == 58
    assert grid.bytes.textCursor().positionInBlock() == 0
    assert grid.scrollbar.value() == min(scroll_before, grid.scrollbar.maximum())


def test_bytes_row_removal_then_assembly_insertion_keeps_all_columns_aligned():
    rows = [
        BinaryWorkbenchRowDTO({"File": "-"}, "entry:", ""),
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "nop",
                "00 00 00 00",
            )
            for index in range(30)
        ],
    ]
    grid = _grid(rows)
    byte_block = grid.bytes.document().findBlockByNumber(10)
    byte_cursor = QTextCursor(byte_block)
    byte_cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(byte_cursor)
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )
    assembly_block = grid.instructions.document().findBlockByNumber(12)
    assembly_cursor = QTextCursor(assembly_block)
    assembly_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    assembly_cursor.insertText("\n")
    grid._consistency_coordinator.flush_collected_changes()

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


def test_deleting_complete_word_bytes_removes_the_plain_row():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000"},
                "word 0x55665544",
                "44 55 66 55",
            ),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "nop", "00 00 00 00"),
        ]
    )
    block = grid.bytes.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position())
    cursor.setPosition(block.position() + len(block.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert [row.instruction.lower() for row in grid._rows] == ["nop"]
    assert grid.bytes.toPlainText() == "00 00 00 00"


def test_deleting_complete_commented_instruction_bytes_is_blocked():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000"},
                "nop ; keep",
                "00 00 00 00",
            )
        ]
    )
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    block = grid.bytes.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position())
    cursor.setPosition(block.position() + len(block.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert grid.bytes.toPlainText() == "00 00 00 00"
    assert grid.instructions.toPlainText().endswith("; keep")
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_BYTES_ROW_REMOVAL_BLOCKED]


def test_repeated_plain_byte_row_before_label_can_be_removed_exactly():
    rows = [
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            )
            for index in range(8)
        ],
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000020"},
            "addiu $sp, $sp, 0x60",
            "60 00 BD 27",
        ),
    ]
    grid = _grid(rows)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    block = grid.bytes.document().findBlockByNumber(3)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )

    assert warnings == []
    assert len(grid._rows) == len(rows) - 1
    assert grid._rows[7].instruction == "spInit:"
    assert grid._rows[8].instruction.lower() == "addiu $sp, $sp, 0x60"


def test_new_byte_row_can_be_inserted_before_a_label():
    rows = [
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            )
            for index in range(3)
        ],
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x0000000C"},
            "addiu $sp, $sp, 0x60",
            "60 00 BD 27",
        ),
    ]
    grid = _grid(rows)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    block = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)
    grid.bytes.setFocus()

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r"),
    )
    QApplication.clipboard().setText("00 00 00 00")
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )

    assert warnings == []
    assert len(grid._rows) == len(rows) + 1
    assert grid._rows[2].bytes_text == "00 00 00 00"
    assert grid._rows[4].instruction == "spInit:"
    assert grid._rows[5].instruction.lower() == "addiu $sp, $sp, 0x60"


def test_enter_after_last_byte_before_label_shifts_source_immediately():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": "0x00000040"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        ),
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000044"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    cursor = QTextCursor(grid.bytes.document().firstBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)
    grid.bytes.setFocus()

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r"),
    )

    assert len(grid._rows) == len(rows) + 1
    assert grid._rows[1].instruction == ""
    assert grid._rows[1].bytes_text == ""
    assert grid._rows[2].instruction == "spInit:"
    assert grid._rows[3].instruction.lower() == "sw $a0, 0x0($sp)"
    source_lines = grid.instructions.toPlainText().split("\n")
    assert source_lines[1] == ""
    assert source_lines[2] == "spInit:"
    assert source_lines[3].lower() == "sw $a0, 0x0($sp)"
    assert grid.bytes.textCursor().blockNumber() == 1


def test_enter_in_bytes_with_three_labels_keeps_folding_and_scroll_reachable():
    """Insert a Bytes row without inheriting a hidden zero-line layout block."""

    rows: list[BinaryWorkbenchRowDTO] = []
    offset = 0
    for label in ("first", "second", "third"):
        rows.append(BinaryWorkbenchRowDTO({"File": "-"}, f"{label}:", ""))
        for _unused in range(8):
            rows.append(BinaryWorkbenchRowDTO(
                {"File": f"0x{offset:08X}"},
                "nop",
                "00 00 00 00",
            ))
            offset += 4
    grid = _grid(rows)
    grid.resize(800, 240)
    grid.show()
    grid.set_label_folding_enabled(True)
    grid.toggle_label_fold("first")
    grid.toggle_label_fold("third")
    block = grid.bytes.document().findBlockByNumber(8)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r"),
    )
    QApplication.processEvents()

    editors = (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    )
    assert {editor.document().blockCount() for editor in editors} == {len(grid._rows)}
    masks = [
        tuple(
            editor.document().findBlockByNumber(row).isVisible()
            for row in range(editor.document().blockCount())
        )
        for editor in editors
    ]
    assert len(set(masks)) == 1
    expected = max(0, grid._scrollable_total_size() - grid.visible_size())
    assert grid.scrollbar.maximum() == expected


def test_backspace_on_inserted_empty_byte_row_returns_to_previous_instruction():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": "0x00000040"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        ),
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000044"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    cursor = QTextCursor(grid.bytes.document().firstBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)
    grid.bytes.setFocus()
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r"),
    )

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )

    cursor = grid.bytes.textCursor()
    assert len(grid._rows) == len(rows)
    assert cursor.blockNumber() == 0
    assert cursor.positionInBlock() == len("02 00 84 24")
    assert grid._rows[1].instruction == "spInit:"


def test_last_byte_removal_before_label_keeps_the_row_and_undoes():
    rows = [
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            )
            for index in range(5)
        ],
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000014"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    grid.set_label_folding_enabled(True)
    grid.toggle_label_fold("spInit")
    block = grid.bytes.document().findBlockByNumber(4)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    for _ in range(len("02 00 84 24")):
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
        )

    cursor = grid.bytes.textCursor()
    assert cursor.blockNumber() == 4
    assert cursor.positionInBlock() == 0
    assert grid._rows[5].instruction == "spInit:"
    assert grid.instructions._label_fold_regions == {5: ("spInit", True)}
    assert {
        editor.document().blockCount()
        for editor in (
            *grid._offset_editors.values(),
            grid.raw_instructions,
            grid.bytes,
            grid.decoded_text,
            grid.instructions,
        )
    } == {len(rows)}

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
    )
    QApplication.processEvents()

    assert len(grid._rows) == len(rows)
    assert grid._rows[4].instruction.lower() == "addiu $a0, $a0, 2"
    assert grid.bytes.document().findBlockByNumber(4).text() == "0"
    assert grid._rows[5].instruction == "spInit:"
    assert grid.instructions._label_fold_regions == {5: ("spInit", True)}


def test_empty_byte_row_inserted_before_label_has_no_valid_offset_immediately():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": "0x00000040"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        ),
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000044"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    grid.set_label_folding_enabled(True)
    cursor = QTextCursor(grid.bytes.document().firstBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r"),
    )

    assert grid._rows[1].instruction == ""
    assert grid._rows[1].bytes_text == ""
    assert grid._rows[1].offsets[BINARY_WORKBENCH_TEXT.FILE] == "-"
    offset_block = grid._offset_editors[
        BINARY_WORKBENCH_TEXT.FILE
    ].document().findBlockByNumber(1)
    assert offset_block.text() == "-"
    assert grid.instructions._label_fold_regions == {2: ("spInit", False)}


def test_bytes_structure_splice_repairs_a_diverged_peer_without_traceback():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        )
        for index in range(8)
    ]
    grid = _grid(rows)
    raw_lines = grid.raw_instructions.toPlainText().split("\n")
    grid.raw_instructions.setPlainText("\n".join(raw_lines[:-1]))
    block = grid.bytes.document().findBlockByNumber(3)
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert len(grid._rows) == len(rows) - 1
    assert {
        editor.document().blockCount()
        for editor in (
            *grid._offset_editors.values(),
            grid.raw_instructions,
            grid.bytes,
            grid.decoded_text,
            grid.instructions,
        )
    } == {len(rows) - 1}


def test_blocked_backspace_after_empty_bytes_does_not_consume_previous_undo():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": "0x00000000"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        ),
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000004"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    cursor = QTextCursor(grid.bytes.document().findBlockByNumber(2))
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    for _ in range(len("00 00 A4 AF")):
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
        )

    assert len(grid._rows) == 3
    assert grid._rows[1].instruction == "spInit:"
    assert grid.bytes.textCursor().blockNumber() == 2
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )
    assert len(grid._rows) == 2
    assert warnings == []
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_BYTES_ROW_REMOVAL_BLOCKED]

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
    )
    QApplication.processEvents()

    assert len(grid._rows) == len(rows)
    assert grid._rows[1].instruction == "spInit:"
    assert grid._rows[2].instruction == ""
    # The structural command restores the empty row first.  Subsequent Undo
    # commands restore each byte deletion individually.
    assert grid.bytes.document().findBlockByNumber(2).text() == ""


def test_multiple_selected_plain_byte_rows_are_removed_without_touching_label():
    rows = [
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            )
            for index in range(12)
        ],
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000030"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    first = grid.bytes.document().findBlockByNumber(5)
    last = grid.bytes.document().findBlockByNumber(8)
    cursor = QTextCursor(first)
    cursor.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert warnings == []
    assert len(grid._rows) == len(rows) - 4
    assert grid._rows[8].instruction == "spInit:"
    assert grid._rows[9].instruction.lower() == "sw $a0, 0x0($sp)"


def test_undo_restores_structurally_deleted_byte_rows_and_assembly_projection():
    rows = [
        *[
            BinaryWorkbenchRowDTO(
                {"File": f"0x{index * 4:08X}"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            )
            for index in range(6)
        ],
        BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
        BinaryWorkbenchRowDTO(
            {"File": "0x00000018"},
            "sw $a0, 0x0($sp)",
            "00 00 A4 AF",
        ),
    ]
    grid = _grid(rows)
    first = grid.bytes.document().findBlockByNumber(2)
    last = grid.bytes.document().findBlockByNumber(4)
    cursor = QTextCursor(first)
    cursor.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )
    assert len(grid._rows) == len(rows) - 3
    cursor = QTextCursor(grid.bytes.document().lastBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
    )

    assert len(grid._rows) == len(rows)
    assert grid.bytes.toPlainText().split("\n")[:6] == ["02 00 84 24"] * 6
    restored_source = grid.instructions.toPlainText().split("\n")[:6]
    assert all(
        source in {"ADDIU $a0, $a0, 2", "ADDIU $a0, $a0, 0x2"}
        for source in restored_source
    )
    assert grid.instructions.toPlainText().split("\n")[6] == "spInit:"
    assert grid._rows[6].instruction == "spInit:"
    assert grid._rows[7].instruction.lower() == "sw $a0, 0x0($sp)"
    assert {
        editor.document().blockCount()
        for editor in (
            *grid._offset_editors.values(),
            grid.raw_instructions,
            grid.bytes,
            grid.decoded_text,
            grid.instructions,
        )
    } == {len(rows)}
    assert grid.instructions.toPlainText().split("\n") == [
        grid._display_instruction(row.instruction) for row in grid._rows
    ]
    assert grid.bytes.toPlainText().split("\n") == [
        grid._display_bytes_row(row) for row in grid._rows
    ]

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Y, Qt.ControlModifier),
    )

    assert len(grid._rows) == len(rows) - 3
    assert grid._rows[3].instruction == "spInit:"
    assert grid._rows[4].instruction.lower() == "sw $a0, 0x0($sp)"


def test_bytes_structural_undo_keeps_every_projection_on_the_same_viewport_row():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        )
        for index in range(48)
    ]
    grid = _grid(rows)
    grid.resize(900, 240)
    grid.show()
    QApplication.processEvents()
    grid.scrollbar.setValue(80)
    first = grid.bytes.document().findBlockByNumber(8)
    last = grid.bytes.document().findBlockByNumber(12)
    cursor = QTextCursor(first)
    cursor.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )
    grid.bytes.moveCursor(QTextCursor.MoveOperation.End)
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
    )
    QApplication.processEvents()
    QApplication.processEvents()

    editors = (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    )
    assert {editor.document().blockCount() for editor in editors} == {len(rows)}
    visible_rows = {
        f"{editor.objectName()}:{index}": (
            editor.firstVisibleBlock().blockNumber(),
            editor.verticalScrollBar().value(),
        )
        for index, editor in enumerate(editors)
    }
    assert len({value[0] for value in visible_rows.values()}) == 1, visible_rows


def test_multiline_byte_paste_updates_corresponding_assembly_rows_immediately():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        )
        for index in range(6)
    ]
    grid = _grid(rows)
    first = grid.bytes.document().findBlockByNumber(1)
    last = grid.bytes.document().findBlockByNumber(3)
    cursor = QTextCursor(first)
    cursor.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)
    QApplication.clipboard().setText(
        "00 00 00 00\n01 00 08 24\n02 00 09 24"
    )

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )

    source = grid.instructions.toPlainText().split("\n")
    assert source[1].lower() == "nop"
    assert source[2].lower() == "addiu $t0, $zero, 0x1"
    assert source[3].lower() == "addiu $t1, $zero, 0x2"


def test_multicursor_byte_edit_updates_every_affected_assembly_row_immediately():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        )
        for index in range(4)
    ]
    grid = _grid(rows)
    ranges = []
    block = grid.bytes.document().firstBlock()
    while block.isValid():
        ranges.append((block.position() + 1, block.position() + 2))
        block = block.next()
    grid.bytes._occurrence_ranges = ranges
    grid.bytes._apply_occurrence_selection(ranges[-1])

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_3, Qt.NoModifier, "3"),
    )

    assert grid.bytes.toPlainText().split("\n") == ["03 00 84 24"] * 4
    assert grid.instructions.toPlainText().split("\n") == [
        "ADDIU $a0, $a0, 0x3"
    ] * 4


def test_pasting_complete_bytes_into_empty_row_keeps_typing_cursor():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
        ]
    )
    cursor = QTextCursor(grid.bytes.document().firstBlock())
    cursor.setPosition(cursor.block().position())
    grid.bytes.setTextCursor(cursor)
    QApplication.clipboard().setText("A0 FF BD 27")

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )

    assert grid.bytes.toPlainText().splitlines() == ["A0 FF BD 27", "00 00 00 00"]
    assert grid._rows[0].bytes_text == "A0 FF BD 27"
    assert grid.bytes.textCursor().blockNumber() == 0
    assert grid.bytes.textCursor().positionInBlock() == len("A0 FF BD 27")


def test_removing_byte_row_with_empty_assembly_source_is_allowed():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    empty = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(empty)
    cursor.setPosition(empty.position())
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )

    assert len(grid._rows) == 2
    assert [row.instruction for row in grid._rows] == ["nop", "jr $ra"]
    assert [line.lower() for line in grid.instructions.toPlainText().splitlines()] == [
        "nop",
        "jr $ra",
    ]
    assert warnings == []


def test_disabled_byte_shifting_reports_the_user_rule_for_plain_row_removal():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000"},
                "nop",
                "00 00 00 00",
            ),
            BinaryWorkbenchRowDTO(
                {"File": "0x00000004"},
                "jr $ra",
                "08 00 E0 03",
            ),
        ]
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)
    second = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(second)
    cursor.setPosition(second.position())
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )

    assert [row.instruction for row in grid._rows] == ["nop", "jr $ra"]
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_BYTES_SHIFTING_DISABLED]


def test_delete_key_removes_current_empty_assembly_row_from_bytes():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    cursor = QTextCursor(grid.bytes.document().findBlockByNumber(0))
    cursor.setPosition(0)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert len(grid._rows) == 1
    assert grid._rows[0].instruction == "jr $ra"
    assert grid.bytes.toPlainText() == "08 00 E0 03"


def test_delete_selection_removes_complete_empty_assembly_row_from_bytes():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, "entry:", ""),
            BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    empty = grid.bytes.document().findBlockByNumber(1)
    cursor = QTextCursor(empty)
    cursor.setPosition(empty.position())
    cursor.setPosition(empty.next().position(), QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier),
    )

    assert [row.instruction for row in grid._rows] == ["entry:", "jr $ra"]
    assert grid.bytes.toPlainText().splitlines() == ["", "08 00 E0 03"]


def test_completing_new_bytes_on_empty_source_row_commits_without_clearing():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
            BinaryWorkbenchRowDTO({"File": "-"}, "spInit:", ""),
            BinaryWorkbenchRowDTO({"File": "-"}, "", ""),
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000", "ram": "0x8000F800"},
                "addiu $sp, $sp, -0x60",
                "A0 FF BD 27",
            ),
            BinaryWorkbenchRowDTO(
                {"File": "0x00000004", "ram": "0x8000F804"},
                "sw $a0, 0x0($sp)",
                "00 00 A4 AF",
            ),
        ]
    )
    grid.set_label_folding_enabled(True)
    target = grid.bytes.document().findBlockByNumber(2)
    cursor = QTextCursor(target)
    cursor.setPosition(target.position())
    grid.bytes.setTextCursor(cursor)

    for key, text in (
        (Qt.Key_A, "A"),
        (Qt.Key_0, "0"),
        (Qt.Key_F, "F"),
        (Qt.Key_F, "F"),
        (Qt.Key_B, "B"),
        (Qt.Key_D, "D"),
        (Qt.Key_2, "2"),
        (Qt.Key_7, "7"),
    ):
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text),
        )

    assert grid.bytes.toPlainText().splitlines() == [
        "",
        "",
        "A0 FF BD 27",
        "A0 FF BD 27",
        "00 00 A4 AF",
    ]
    assert len(grid._rows) == 5
    assert grid._rows[2].bytes_text == "A0 FF BD 27"
    assert grid.instructions.document().findBlockByNumber(2).text()


def test_rejected_shorter_document_never_restores_cursor_out_of_range():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "entry: nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "jr $ra", "08 00 E0 03"),
        ]
    )
    cursor = grid.bytes.textCursor()
    cursor.movePosition(QTextCursor.End)
    grid.bytes.setTextCursor(cursor)
    messages: list[str] = []
    previous = qInstallMessageHandler(lambda _kind, _context, message: messages.append(message))
    try:
        grid.bytes.setPlainText("01 00 00 00")
    finally:
        qInstallMessageHandler(previous)

    assert grid.bytes.textCursor().position() <= grid.bytes.document().characterCount() - 1
    assert not any("out of range" in message for message in messages)


def test_normal_last_row_hex_edit_keeps_cursor_inside_document():
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "nop",
            "00 00 00 00",
        )
        for index in range(96)
    ]
    grid = _grid(rows)
    block = grid.bytes.document().findBlockByNumber(95)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.EndOfBlock)
    cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
    grid.bytes.setTextCursor(cursor)
    messages: list[str] = []
    previous = qInstallMessageHandler(lambda _kind, _context, message: messages.append(message))
    try:
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_1, Qt.NoModifier, "1"),
        )
    finally:
        qInstallMessageHandler(previous)

    assert grid.bytes.document().findBlockByNumber(95).text().endswith("01")
    assert grid.bytes.textCursor().position() <= grid.bytes.document().characterCount() - 1
    assert not any("out of range" in message for message in messages)


def test_incomplete_byte_edit_and_undo_never_remove_the_assembly_line():
    target = 66
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "sw $a2, 0x8($sp)" if index == target else "nop",
            "08 00 A6 AF" if index == target else "00 00 00 00",
        )
        for index in range(80)
    ]
    grid = _grid(rows)
    cursor = QTextCursor(grid.bytes.document().findBlockByNumber(target))
    cursor.movePosition(QTextCursor.EndOfBlock)
    grid.bytes.setTextCursor(cursor)
    messages: list[str] = []
    previous = qInstallMessageHandler(lambda _kind, _context, message: messages.append(message))
    try:
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
        )
        assert grid.bytes.document().findBlockByNumber(target).text() == "08 00 A6 A"
        assert grid.instructions.document().findBlockByNumber(target).text() == "SW $a2, 0x8($sp)"

        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_F, Qt.NoModifier, "F"),
        )
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
        )
    finally:
        qInstallMessageHandler(previous)

    assert grid.bytes.document().findBlockByNumber(target).text() == "08 00 A6 A"
    assert grid.instructions.document().findBlockByNumber(target).text() == "SW $a2, 0x8($sp)"
    assert grid._rows[target].bytes_text == "08 00 A6 AF"
    assert not any("out of range" in message for message in messages)


def test_plain_multiline_replace_and_complete_append_are_atomic():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00"),
            BinaryWorkbenchRowDTO({"File": "0x00000004"}, "nop", "00 00 00 00"),
        ]
    )

    grid.bytes.setPlainText("01 00 08 24\n02 00 09 24")
    assert [row.bytes_text for row in grid._rows] == ["01 00 08 24", "02 00 09 24"]

    grid.bytes.setPlainText("01 00 08 24\n02 00 09 24\n")
    assert len(grid._rows) == 2
    grid.bytes.setPlainText("01 00 08 24\n02 00 09 24\n00 00 00 00")
    assert len(grid._rows) == 3
    assert grid._rows[-1].bytes_text == "00 00 00 00"


def test_deleting_last_byte_is_bounded_and_does_not_remove_the_row(monkeypatch):
    rows = [
        BinaryWorkbenchRowDTO(
            {"File": f"0x{index * 4:08X}"},
            "addiu $a0, $a0, 2",
            "02 00 84 24",
        )
        for index in range(1000)
    ]
    grid = _grid(rows)
    monkeypatch.setattr(
        grid,
        "_sync_user_rows",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("last-byte deletion must not rebuild every row")
        ),
    )
    cursor = QTextCursor(grid.bytes.document().firstBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)
    for _ in range(10):
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
        )

    started = perf_counter()
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )
    elapsed = perf_counter() - started

    assert elapsed < 0.2
    assert len(grid._rows) == len(rows)
    assert grid.bytes.document().firstBlock().text() == ""
    assert {
        editor.document().blockCount()
        for editor in (
            *grid._offset_editors.values(),
            grid.raw_instructions,
            grid.bytes,
            grid.decoded_text,
            grid.instructions,
        )
    } == {len(rows)}


def test_deleting_last_byte_does_not_bypass_disabled_byte_shifting():
    grid = _grid(
        [
            BinaryWorkbenchRowDTO(
                {"File": "0x00000000"},
                "addiu $a0, $a0, 2",
                "02 00 84 24",
            ),
            BinaryWorkbenchRowDTO(
                {"File": "0x00000004"},
                "nop",
                "00 00 00 00",
            ),
        ]
    )
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))
    cursor = QTextCursor(grid.bytes.document().firstBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    grid.bytes.setTextCursor(cursor)

    for _ in range(len("02 00 84 24")):
        QApplication.sendEvent(
            grid.bytes,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
        )

    assert len(grid._rows) == 2
    assert grid.bytes.document().blockCount() == 2
    assert grid.bytes.document().firstBlock().text() == ""
    assert grid.instructions.document().firstBlock().text().lower().startswith("addiu")
