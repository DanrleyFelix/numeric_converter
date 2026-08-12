from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication
from pathlib import Path

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


def test_import_completion_waits_for_typing_debounce(tmp_path: Path):
    """Do not scan an import directory from the key event itself."""

    _app()
    source = tmp_path / "main.asm"
    source.write_text("nop", encoding="utf-8")
    editor = WorkbenchEditor()
    editor.set_import_source_path(source)
    calls: list[tuple[Path | None, str]] = []
    provider = editor._import_completion_provider
    original = provider.complete

    def complete(path: Path | None, prefix: str):
        calls.append((path, prefix))
        return original(path, prefix)

    provider.complete = complete
    editor.setPlainText("* import ch")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor._schedule_completions_after_edit(deleting=False)

    assert calls == []
    assert editor._symbol_completion_timer.isActive() is True
    assert editor._symbol_completion_timer.interval() == 400

    editor._symbol_completion_timer.stop()
    editor._refresh_completions()
    assert calls == [(source, "ch")]


def test_import_completion_enters_directory_without_second_debounce(tmp_path: Path):
    """Open a selected folder immediately, then append a space to files."""

    _app()
    source = tmp_path / "main.asm"
    source.write_text("nop", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "child.asm").write_text("nop", encoding="utf-8")
    editor = WorkbenchEditor()
    editor.set_import_source_path(source)
    editor.setPlainText("* import ne")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    editor._refresh_completions()
    editor._insert_completion("nested/")

    assert editor.toPlainText() == "* import nested/"
    assert editor._completion_model.stringList() == ["nested/child.asm"]

    editor._insert_completion("nested/child.asm")
    assert editor.toPlainText() == "* import nested/child.asm "


def test_data_file_completion_opens_external_import_path_immediately(tmp_path: Path):
    """Offer the modifier, then reuse hierarchical import completion."""

    _app()
    source = tmp_path / "main.asm"
    source.write_text("nop", encoding="utf-8")
    (tmp_path / "data.asm").write_text("nop", encoding="utf-8")
    editor = WorkbenchEditor()
    editor.set_import_source_path(source)
    editor.setPlainText("* import da")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    editor._refresh_completions()
    assert "data_file" in editor._completion_model.stringList()
    editor._insert_completion("data_file")

    assert editor.toPlainText() == "* import data_file "
    assert editor._completion_model.stringList() == ["data.asm"]
    assert "current_file" not in editor._completion_model.stringList()


def test_data_file_modifier_uses_dodger_blue_highlight():
    """Distinguish the data-only import modifier from the import command."""

    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("* import data_file data/table.asm 0x801A7E20")
    highlighter = InstructionHighlighter(editor.document())
    highlighter.rehighlight()

    data_file_format = next(
        item
        for item in editor.document().firstBlock().layout().formats()
        if item.start == len("* import ") and item.length == len("data_file")
    )

    assert data_file_format.format.foreground().color().name().upper() == "#1E90FF"


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
