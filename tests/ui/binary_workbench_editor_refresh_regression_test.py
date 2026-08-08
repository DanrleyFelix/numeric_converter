import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QFocusEvent, QKeyEvent, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from src.presentation.ui.components.binary_workbench.editor.highlighters import (
    InstructionHighlighter,
    invalid_address_format,
)
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import (
    WorkbenchEditor,
)
from src.presentation.ui.components.binary_workbench.editor.grid_virtual_selection import (
    GridVirtualSelectionMixin,
)

_APP = None


def _app() -> QApplication:
    """Return the shared offscreen application."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_instruction_normalization_preserves_cursor_inside_comment():
    """Keep the typing cursor stable while the mnemonic becomes uppercase."""

    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.set_uppercase_instruction_hover(True)
    editor.setPlainText("lhu $v1, 0($v0) ; keep typing here")
    expected_position = editor.toPlainText().index("typing") + 2
    cursor = editor.textCursor()
    cursor.setPosition(expected_position)
    editor.setTextCursor(cursor)

    editor._normalize_current_instruction_line()

    assert editor.toPlainText() == "LHU $v1, 0($v0) ; keep typing here"
    assert editor.textCursor().position() == expected_position


def test_hex_letter_typing_preserves_cursor_inside_immediate():
    """Keep the cursor after a hexadecimal letter inserted inside a value."""

    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.set_uppercase_instruction_hover(True)
    editor.setPlainText("lui $v0, 0x8b")
    initial_position = editor.toPlainText().index("8") + 1
    cursor = editor.textCursor()
    cursor.setPosition(initial_position)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_A, Qt.NoModifier, "a"),
    )

    assert editor.toPlainText() == "LUI $v0, 0x8AB"
    assert editor.textCursor().position() == initial_position + 1


def test_load_store_highlighter_ignores_stale_numeric_block_cache():
    """Derive effective addresses from the preceding QTextBlock after edits."""

    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    editor.setPlainText("nop\nLHU $v1, 0($v0)")
    highlighter.rehighlight()
    highlighter._known_register_values_by_block[0] = {0: 0, 2: 1}

    block = editor.document().findBlockByNumber(1)
    highlighter.rehighlightBlock(block)
    _app().processEvents()

    invalid_color = invalid_address_format().background().color()
    operand_start = block.text().index("0(")
    assert not any(
        item.start <= operand_start < item.start + item.length
        and item.format.background().color() == invalid_color
        for item in block.layout().formats()
    )


def test_directive_diagnostics_ignore_unrelated_instruction_edits():
    """Do not refresh every block merely because one directive exists."""

    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    editor.setPlainText("* define $sp 0x801FFFF0\nnop")
    highlighter.rehighlight()
    block = editor.document().findBlockByNumber(1)
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.EndOfBlock)
    cursor.insertText(" ")

    assert highlighter._directive_refresh_timer.isActive() is False


def test_directive_edit_debounces_cross_line_diagnostics():
    """Consolidate global directive validation after editing a directive."""

    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    editor.setPlainText("* define $sp 0x801FFFF0\nnop")
    highlighter.rehighlight()
    cursor = QTextCursor(editor.document().firstBlock())
    cursor.movePosition(QTextCursor.EndOfBlock)
    cursor.insertText(" ")

    assert highlighter._directive_refresh_timer.isActive() is True
    QTest.qWait(120)
    assert highlighter._directive_refresh_timer.isActive() is False


class _CopySelectionHarness(GridVirtualSelectionMixin):
    """Exercise the grid copy contract without constructing the complete UI."""

    def __init__(self, editor: WorkbenchEditor) -> None:
        self.bytes = editor
        self.raw_instructions = WorkbenchEditor()
        self.instructions = WorkbenchEditor()
        self._virtual_selection_range = None
        self._selection_projection_request = ("Bytes", 0, 0)
        self._selection_projection_timer = QTimer()
        self._selection_projection_timer.setSingleShot(True)
        self._consistency_coordinator = None


def test_copy_keeps_selection_and_cancels_its_pending_projection():
    """Keep Ctrl+C selection after its obsolete selection projection expires."""

    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("00  00  00  00")
    editor.selectAll()
    harness = _CopySelectionHarness(editor)
    harness._selection_projection_timer.timeout.connect(
        lambda: editor.setTextCursor(QTextCursor(editor.document()))
    )
    harness._selection_projection_timer.start(0)

    harness._copy_editor_selection(editor)
    _app().processEvents()

    assert editor.textCursor().selectedText() == "00  00  00  00"
    assert harness._selection_projection_timer.isActive() is False


def test_right_click_inside_selection_does_not_start_another_selection():
    """Keep an existing block selected when its context menu is requested."""

    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("selected block")
    editor.selectAll()
    started = []
    editor.selectionStarted.connect(started.append)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(4)
    point = editor.cursorRect(cursor).center()

    QTest.mousePress(editor.viewport(), Qt.RightButton, pos=point)

    assert started == []
    assert editor.textCursor().selectedText() == "selected block"


def test_context_menu_focus_does_not_clear_selection():
    """Preserve the selected block while a popup temporarily owns focus."""

    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("selected block")
    editor.selectAll()

    editor.focusOutEvent(
        QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.PopupFocusReason)
    )

    assert editor.textCursor().selectedText() == "selected block"
