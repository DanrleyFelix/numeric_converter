from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from src.core.debugger.directives.validation.diagnostics import (
    debugger_directive_diagnostics,
)
from src.presentation.ui.components.binary_workbench.editor.constants.highlighter_rules import (
    DEBUGGER_DIRECTIVE_HIGHLIGHTER,
)
from src.presentation.ui.components.binary_workbench.editor.highlighters import (
    InstructionHighlighter,
)
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import (
    WorkbenchEditor,
)


def _app() -> QApplication:
    """Return the shared Qt application used by editor tests."""

    return QApplication.instance() or QApplication([])


def test_directive_autocomplete_is_reserved_for_star_prefixed_lines():
    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("* vi")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    assert editor._current_completion_prefix() == "* vi"
    assert editor._candidates_for_prefix("* vi") == ["* virtual_memory_range"]

    editor.setPlainText("vi")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    assert "virtual_memory_range" not in editor._candidates_for_prefix("vi")


def test_directive_highlighter_uses_required_colors_and_exposes_errors():
    _app()
    editor = WorkbenchEditor()
    editor.setPlainText(
        "* virtual_memory_range 0x801DFFFF 0x80000000\n"
        "* import current_file 0x801D9274"
    )
    highlighter = InstructionHighlighter(editor.document())
    highlighter.rehighlight()

    first_formats = editor.document().firstBlock().layout().formats()
    foregrounds = {
        item.format.foreground().color().name().upper()
        for item in first_formats
        if item.format.foreground().style()
    }
    errors = editor.document().property("debuggerDirectiveErrors")

    assert DEBUGGER_DIRECTIVE_HIGHLIGHTER["command"] in foregrounds
    assert DEBUGGER_DIRECTIVE_HIGHLIGHTER["hex"] in foregrounds
    assert "lower than" in errors[0]


def test_directive_diagnostics_reject_missing_symbol_and_late_directive():
    errors = debugger_directive_diagnostics(
        [
            "* virtual_memory_range 0x80000000 0x801DFFFF",
            "* define $pc MISSING",
            "nop",
            "* ignore $pc 0x80000010",
        ],
        {},
        lambda code: code == "nop",
    )

    assert "hexadecimal Symbol" in errors[1]
    assert "before assembly" in errors[3]


def test_directive_errors_refresh_after_live_editor_changes():
    _app()
    editor = WorkbenchEditor()
    highlighter = InstructionHighlighter(editor.document())

    editor.setPlainText("* virtual_memory_range 0x20 0x10")
    assert "lower than" in editor.document().property("debuggerDirectiveErrors")[0]

    editor.setPlainText("* virtual_memory_range 0x10 0x20")
    assert editor.document().property("debuggerDirectiveErrors") == {}


def test_directive_error_background_waits_for_value_and_covers_reserved_tokens():
    """Keep live typing neutral until a value exists, then cover the full invalid line."""

    _app()
    editor = WorkbenchEditor()
    highlighter = InstructionHighlighter(editor.document())
    editor.setPlainText("* define $pc")
    highlighter.rehighlight()
    assert not any(
        item.format.background().style() != Qt.NoBrush
        for item in editor.document().firstBlock().layout().formats()
    )

    editor.setPlainText("* define $pc MISSING")
    highlighter.rehighlight()
    formats = editor.document().firstBlock().layout().formats()
    covered = {
        position
        for item in formats
        if item.format.background().style() != Qt.NoBrush
        for position in range(item.start, item.start + item.length)
    }
    assert covered == set(range(len("* define $pc MISSING")))


def test_pc_directive_uses_the_stack_pointer_register_color():
    """Render `$pc` with the same established pointer color as `$sp`."""

    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("* define $pc 0x80000000\n* define $sp 0x801FFFF0")
    InstructionHighlighter(editor.document()).rehighlight()

    colors = []
    for block_number in (0, 1):
        block = editor.document().findBlockByNumber(block_number)
        register = next(item for item in block.layout().formats() if item.start == 9)
        colors.append(register.format.foreground().color().name())
    assert colors[0] == colors[1]
