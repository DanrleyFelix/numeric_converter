import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QShortcut, QTextCursor, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QFileDialog, QLabel, QListWidget, QMessageBox, QPushButton, QComboBox, QDialog, QLineEdit, QMenu, QPlainTextEdit, QScrollArea, QScrollBar, QTableView, QTextBrowser, QToolButton, QWidget

from src.main import create_main_window
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_FIND_DEFAULT_LENGTH_KB,
    BINARY_WORKBENCH_FIND_MAX_LENGTH_KB,
    BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_KB,
)
from src.modules.dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchLbaFilesystemDTO,
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchLabelsDialog,
    BinaryWorkbenchSymbolOffsetsDialog,
    BinaryWorkbenchSymbolsDialog,
)
from src.presentation.ui.components.binary_workbench.editor.constants.highlighter_rules import (
    PSX_MIPS_HIGHLIGHTER,
)
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
)
from src.presentation.ui.components.binary_workbench.editor.highlighters import (
    InstructionHighlighter,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    invalid_instruction,
)
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.binary_workbench.editor.constants.context_menu import (
    CONTEXT_MENU_SHORTCUTS,
)
from src.presentation.ui.components.binary_workbench.editor import (
    page_immediate_symbols as page_immediate_symbols_module,
)
from src.presentation.ui.components.binary_workbench.editor.page import (
    BinaryWorkbenchEditorPage,
)
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor
from src.presentation.ui.components.binary_workbench.editor.add_command_dialog import AddCommandDialog
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchInternalFileDialog,
    BinaryWorkbenchLbaFilesystemDialog,
    BinaryWorkbenchVersionActionsDialog,
    BinaryWorkbenchVersionChangeDialog,
    BinaryWorkbenchVersionNameDialog,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.native_dialogs import _map_windows_response
from src.presentation.ui.components.binary_workbench.preferences import (
    BinaryWorkbenchAdvancedConfigDialog,
    BinaryWorkbenchViewDialog,
)
from src.presentation.ui.components.binary_workbench.search import (
    BinaryWorkbenchFindDialog,
    BinaryWorkbenchGoToDialog,
    BinaryWorkbenchReplaceBytesDialog,
    BinaryWorkbenchSelectBlockDialog,
)
from src.presentation.repository.binary_workbench_payload import (
    binary_workbench_state_from_payload,
    binary_workbench_state_to_payload,
)
from src.presentation.repository.binary_workbench_workspace.constants import (
    GLOBAL_SYMBOLS,
)


_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _window(root: Path | None = None):
    _app()
    return create_main_window(root or Path(tempfile.mkdtemp()))


def test_main_window_registers_global_window_recovery_shortcut(tmp_path: Path):
    window = _window(tmp_path)
    shortcut = window.findChild(QShortcut, "window-recovery-shortcut")

    assert shortcut is not None
    assert shortcut.key().toString() == "Ctrl+Space"
    assert shortcut.context() == Qt.ApplicationShortcut


def test_binary_workbench_opens_multiple_file_tabs_with_independent_contexts(tmp_path: Path):
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"\x00\x01")
    second.write_bytes(b"\x02\x03")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(first)
    tool.open_binary_path(second)
    state = tool.export_state()

    assert tool.tabs.count() == 2
    assert [tab.display_name for tab in state.tabs] == ["first.bin", "second.bin"]
    assert [tab.source_path for tab in state.tabs] == [str(first), str(second)]
    assert state.tabs[0].tab_id != state.tabs[1].tab_id
    assert state.tabs[0].labels == {}
    assert state.tabs[1].labels == {}
    assert state.tabs[0].rows[0].offsets["File"] == "0x00000000"


def test_binary_workbench_guide_uses_help_window_pages(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.toolbar.help_action.trigger()

    assert tool._help_window is not None
    nav_titles = [
        tool._help_window.navigation.item(index).text()
        for index in range(tool._help_window.navigation.count())
    ]
    assert nav_titles == [
        "Main Window",
        "Debugger Directives",
        "Debugger Window",
        "File",
        "Versions",
        "Internal Files",
        "Environment",
        "Preferences",
        "Search",
        "Editor Helpers",
        "Shortcuts",
    ]
    page = tool._help_window.pages.currentWidget()
    browser = page.findChild(QTextBrowser, "help-page")
    assert browser is not None
    assert browser.verticalScrollBar().objectName() == "help-page-scrollbar"
    tool._help_window.navigation.setCurrentRow(nav_titles.index("Shortcuts"))
    shortcuts_browser = tool._help_window.pages.currentWidget().findChild(QTextBrowser, "help-page")
    text = shortcuts_browser.toPlainText()
    for value in ("Ctrl+O", "Alt+V", "Ctrl+F", "Alt+H", "Alt+K", "Ctrl+Y"):
        assert value in text
    tool._help_window.navigation.setCurrentRow(
        nav_titles.index("Debugger Directives")
    )
    directives = tool._help_window.pages.currentWidget().findChild(
        QTextBrowser, "help-page"
    ).toPlainText()
    assert "virtual_memory_range" in directives
    assert "virtual memory" in directives.casefold()
    for value in ("data_file", "mapped data range", "persisted version"):
        assert value in directives
    tool._help_window.navigation.setCurrentRow(nav_titles.index("Debugger Window"))
    debugger_guide = tool._help_window.pages.currentWidget().findChild(
        QTextBrowser, "help-page"
    ).toPlainText()
    for value in (
        "Run (F5)",
        "Restart (F8)",
        "READY",
        "without resetting",
        "Config (F11)",
        "Interval (ms)",
        "Follow W",
    ):
        assert value in debugger_guide


def test_binary_workbench_open_file_reuses_existing_external_tab(tmp_path: Path):
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"\x00\x01")
    second.write_bytes(b"\x02\x03")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(first)
    tool.open_file_path(second)
    tool.open_file_path(first)

    assert tool.tabs.count() == 2
    assert tool.tabs.currentIndex() == 0
    assert tool.footer_status.property("statusKind") == "warning"
    assert tool.footer_status.text() == 'File "first.bin" is already open.'


def test_binary_workbench_open_file_does_not_match_internal_tab_name(tmp_path: Path):
    parent = tmp_path / "disc.bin"
    external = tmp_path / "SLUS"
    parent.write_bytes(bytes(range(64)))
    external.write_bytes(b"\x00\x01\x02\x03")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(parent)
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO("SLUS", 0)])
    tool.tabs.open_internal_tab("SLUS")
    tool.open_file_path(external)

    assert tool.tabs.count() == 3
    assert tool.tabs.current_context().source_path == str(external)


def test_binary_workbench_internal_file_footer_and_close_feedback(tmp_path: Path):
    parent = tmp_path / ("a" * 70 + ".bin")
    parent.write_bytes(bytes(range(64)))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(parent)
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO("SLUS", 0)])
    tool.tabs.open_internal_tab("SLUS")
    page = tool.tabs.currentWidget()

    assert page.internal_file_summary.isVisible()  # type: ignore[attr-defined]
    assert page.internal_file_summary.text() == f'Internal File from "{parent.name[:60]}"'  # type: ignore[attr-defined]
    tool.tabs.close_tab(tool.tabs.currentIndex())
    assert "Internal Files" in tool.footer_status.text()


def test_binary_workbench_loads_full_binary_instead_of_truncating(tmp_path: Path):
    binary_path = tmp_path / "full.bin"
    binary_path.write_bytes(bytes(range(256)))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    current = tool.tabs.current_context()
    page = tool.tabs.currentWidget()

    assert current is not None
    assert current.rows[0].offsets["File"] == "0x00000000"
    assert current.rows[-1].offsets["File"] <= "0x000000FC"
    assert page is not None
    assert current.file_size == 256


def test_binary_workbench_open_binary_does_not_create_unsaved_overlays(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 2D 58 20 45 58 45"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert current.byte_overlays == {}
    assert current.instruction_overlays == {}
    assert current.version_dirty is False
    assert tool.tabs.has_unsaved_changes(0) is False


def test_binary_workbench_closes_clean_binary_without_save_prompt(tmp_path: Path, monkeypatch):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 2D 58 20 45 58 45"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    _app().processEvents()
    monkeypatch.setattr(
        tool,
        "_native_close_question",
        lambda: pytest.fail("Clean binary tab must not request saving"),
    )

    tool._request_tab_close(tool.tabs.currentIndex())

    assert tool.tabs.count() == 0


def test_binary_workbench_open_binary_loads_rows_for_visible_editor_height(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes(range(256)) * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.resize(1200, 720)
    tool.open_binary_path(binary_path)
    _app().processEvents()
    page = tool.tabs.currentWidget()
    current = tool.tabs.current_context()

    assert page is not None
    assert current is not None
    assert len(current.rows) == page.grid.visible_size() // 4  # type: ignore[attr-defined]
    assert len(current.rows) > 2


def test_binary_workbench_blank_instruction_line_preserves_loaded_bytes(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 2D 58"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    surface = page.grid  # type: ignore[attr-defined]
    original = surface._rows[0]

    rows = surface._instruction_rows_from_lines(["   "])

    assert rows == [original]
    assert rows[0].bytes_text == "00 00 2D 58"


def test_binary_workbench_space_input_does_not_mark_binary_dirty(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    cursor = editor.textCursor()
    cursor.setPosition(len(editor.toPlainText().splitlines()[0]))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier, " "))
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Tab, Qt.NoModifier))
    _app().processEvents()

    assert tool.tabs.has_unsaved_changes(0) is False


def test_binary_workbench_blank_instruction_line_updates_offsets_immediately(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]

    editor.setPlainText("NOP\n")
    _app().processEvents()

    offset_lines = page.grid._offset_editors["File"].toPlainText().splitlines()  # type: ignore[attr-defined]
    assert offset_lines[1].strip() == "-"

    editor.setPlainText("NOP")
    _app().processEvents()

    offset_lines = page.grid._offset_editors["File"].toPlainText().splitlines()  # type: ignore[attr-defined]
    assert len(offset_lines) == 1
    assert offset_lines[0].strip() != "-"

    editor.setPlainText("NOP\n; comment")
    _app().processEvents()

    offset_lines = page.grid._offset_editors["File"].toPlainText().splitlines()  # type: ignore[attr-defined]
    assert offset_lines[1].strip() == "-"

    editor.setPlainText("NOP")
    _app().processEvents()

    offset_lines = page.grid._offset_editors["File"].toPlainText().splitlines()  # type: ignore[attr-defined]
    assert len(offset_lines) == 1
    assert offset_lines[0].strip() != "-"


def test_binary_workbench_version_dialog_exposes_change_version():
    _app()
    actions = BinaryWorkbenchVersionActionsDialog()
    buttons = actions.findChildren(QPushButton)

    assert actions.findChild(QLabel, "preferences-title") is None
    assert actions.layout().spacing() == 15
    assert actions.layout().getContentsMargins() == (20, 20, 20, 20)
    assert "Load Versions File" in [button.text() for button in buttons]
    assert "Change Version" in [button.text() for button in buttons]

    picker = BinaryWorkbenchVersionChangeDialog(
        [
            BinaryWorkbenchVersionDTO("v2 test"),
            BinaryWorkbenchVersionDTO("v1_test_2"),
        ],
        "v1_test_2",
    )
    version_buttons = picker.findChildren(QPushButton)
    version_list = picker.findChild(QWidget, "binary-workbench-version-list")

    assert picker.findChild(QLabel, "preferences-title") is None
    assert picker.findChild(QLabel, "preferences-subtitle") is None
    assert picker.layout().getContentsMargins() == (20, 20, 20, 20)
    assert version_list is not None
    assert version_list.layout().spacing() == 15
    assert version_list.layout().contentsMargins().left() == 15
    assert [button.text() for button in version_buttons] == ["v2 test", "v1_test_2"]
    assert version_buttons[1].objectName() == "binary-workbench-version-active"
    assert all(button.focusPolicy() == Qt.NoFocus for button in version_buttons)
    assert all(button.cursor().shape() == Qt.PointingHandCursor for button in version_buttons)


def test_binary_workbench_create_version_uses_centered_confirm_button():
    _app()
    dialog = BinaryWorkbenchVersionNameDialog("Create Version")
    dialog.show()
    _app().processEvents()
    confirm = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Confirm")

    assert dialog.findChild(QLabel, "preferences-title") is None
    assert dialog.findChild(QLabel, "preferences-subtitle") is None
    assert dialog.name_field.width() == confirm.width()
    assert dialog.name_field.height() == confirm.height()
    assert dialog.name_field.mapTo(dialog, QPoint()).x() == confirm.mapTo(dialog, QPoint()).x()
    assert confirm.mapTo(dialog, QPoint()).y() - dialog.name_field.mapTo(dialog, QPoint()).y() > dialog.name_field.height()


def test_binary_workbench_add_command_dialog_uses_wide_centered_controls():
    _app()
    dialog = AddCommandDialog()
    dialog.show()
    _app().processEvents()
    confirm = next(button for button in dialog.findChildren(QPushButton) if button.text() == BINARY_WORKBENCH_TEXT.CONFIRM)

    assert dialog.width() == BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_DIALOG_WIDTH
    assert dialog.width() == 300
    assert dialog.height() == BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_DIALOG_HEIGHT
    assert dialog.layout().getContentsMargins() == (20, 20, 20, 20)
    assert dialog.name_input.width() == BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_FIELD_WIDTH
    assert dialog.name_input.width() == 260
    assert confirm.width() == BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_FIELD_WIDTH
    assert dialog.name_input.mapTo(dialog, QPoint()).x() == confirm.mapTo(dialog, QPoint()).x()


def test_binary_workbench_load_versions_file_replaces_available_versions(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00"))
    versions_path = tmp_path / "replacement_versions.json"
    versions_path.write_text(
        (
            '{"active_version":"new_b","versions":{'
            '"new_a":{"0":"word 0x00100000"},'
            '"new_b":{"0":"word 0x00200000"}'
            "}}"
        ),
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    current = tool.tabs.current_context()
    assert current is not None
    tool.tabs._set_current_context(
        BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "versions": [
                    BinaryWorkbenchVersionDTO("old_a"),
                    BinaryWorkbenchVersionDTO("old_b"),
                ],
                "active_version_name": "old_a",
                "module_paths": {
                    "version:old_a": "old_versions.json",
                    "versions": "old_versions.json",
                },
            }
        )
    )

    assert tool.tabs.load_versions_file(versions_path) == "new_b"
    current = tool.tabs.current_context()

    assert current is not None
    assert [version.name for version in current.versions] == ["new_a", "new_b"]
    assert current.active_version_name == "new_b"
    imported_path = tmp_path / "data" / "binary_workbench" / "workspaces" / "Versions" / versions_path.name
    assert current.module_paths["versions"] == str(imported_path)
    assert imported_path.read_text(encoding="utf-8") == versions_path.read_text(encoding="utf-8")
    assert "version:old_a" not in current.module_paths
    assert "version:new_b" in current.module_paths


def test_binary_workbench_environment_directories_ignore_last_external_location(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    external = tmp_path / "external"
    expected_folders = {
        "symbols": "Symbols",
        "lba_filesystem": "LBA File System",
        "versions": "Versions",
        "offset_regions": "Offset Regions",
        "commands": "Commands",
        "encoding_tables": "Encoding Tables",
    }
    for action_key, folder in expected_folders.items():
        tool.tabs.set_directory(action_key, external)
        expected = tmp_path / "data" / "binary_workbench" / "workspaces" / folder
        assert tool.tabs.directory_for(action_key) == str(expected)
        assert expected.is_dir()


def test_binary_workbench_bytes_remains_editable_after_line_version_load(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00 00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    current = tool.tabs.current_context()
    assert current is not None
    tool.tabs._set_current_context(
        BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "versions": [
                    BinaryWorkbenchVersionDTO(
                        "v1",
                        instructions_by_line={
                            0: "NOP",
                            1: "; comment",
                            2: "NOP",
                        },
                    )
                ],
            }
        )
    )

    assert tool.tabs.load_version("v1") is True
    page = tool.tabs.currentWidget()
    valid_index = next(index for index, row in enumerate(page.grid._rows) if row.bytes_text)  # type: ignore[attr-defined]
    displayed = page.grid.bytes.toPlainText().splitlines()  # type: ignore[attr-defined]
    displayed[valid_index] = "AABBCCDD"
    page.grid.bytes.setPlainText("\n".join(displayed))  # type: ignore[attr-defined]
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert page.grid.bytes.toPlainText().splitlines()[valid_index] == "AA BB CC DD"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[1] == ""  # type: ignore[attr-defined]
    assert current.rows[1].offsets["File"] == "-"
    assert current.rows[1].instruction == "; comment"
    assert page.grid.raw_instructions.toPlainText().splitlines()[1] == ""  # type: ignore[attr-defined]

    displayed = page.grid.bytes.toPlainText().splitlines()  # type: ignore[attr-defined]
    displayed[1] = "11223344"
    page.grid.bytes.setPlainText("\n".join(displayed))  # type: ignore[attr-defined]
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert page.grid.bytes.toPlainText().splitlines()[valid_index] == "AA BB CC DD"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[1] == "11 22 33 44"  # type: ignore[attr-defined]
    assert current.rows[1].offsets["File"] == "-"
    assert current.rows[1].instruction.endswith("; comment")
    assert current.byte_overlays["0x00000000"] == "AA BB CC DD"
    assert page.grid._offset_editors["File"].toPlainText().splitlines()[1].strip() == "-"  # type: ignore[attr-defined]
    assert page.grid.raw_instructions.toPlainText().splitlines()[1] != ""  # type: ignore[attr-defined]


def test_binary_workbench_restored_redundant_overlays_are_compacted(tmp_path: Path):
    binary_path = tmp_path / "clean.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 2D 58 20 45 58 45"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs._append_tab(
        BinaryWorkbenchTabContextDTO(
            tab_id="legacy",
            kind="binary",
            display_name=binary_path.name,
            source_path=str(binary_path),
            read_mode="bytes",
            byte_overlays={"0x00000000": "00 00 00 00"},
            instruction_overlays={
                "0x00000000": "",
                "0x00000004": "WORD 0x45584520",
            },
            version_dirty=True,
        )
    )
    current = tool.tabs.current_context()

    assert current is not None
    assert current.rows[0].bytes_text == "00 00 2D 58"
    assert current.byte_overlays == {}
    assert current.instruction_overlays == {}
    assert current.version_dirty is False
    assert tool.tabs.has_unsaved_changes(0) is False


def test_binary_workbench_seeks_visible_binary_rows_when_body_scrolls(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes(range(256)) * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    current = tool.tabs.current_context()

    assert page is not None
    assert current is not None
    initial_first = current.rows[0].offsets["File"]
    assert len(current.rows) < (binary_path.stat().st_size // 4)
    _app().processEvents()
    scrollbar = page.grid.scrollbar  # type: ignore[attr-defined]
    scrollbar.setValue(scrollbar.maximum())
    _app().processEvents()
    updated = tool.tabs.current_context()

    assert updated is not None
    assert updated.rows[0].offsets["File"] != initial_first
    assert updated.rows[0].offsets["File"] == f"0x{scrollbar.value() - (scrollbar.value() % 4):08X}"
    assert "FF" in page.grid.bytes.toPlainText()  # type: ignore[attr-defined]


def test_binary_workbench_footer_status_uses_body_aligned_label(tmp_path: Path):
    binary_path = tmp_path / "status.bin"
    binary_path.write_bytes(b"\x00\x00\x00\x00")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    footer = tool.findChild(QLabel, "binary-workbench-footer-status")

    assert footer is not None
    assert footer.text() == 'Opened "status.bin".'
    assert tool.statusBar().isHidden()


def test_binary_workbench_file_action_without_tab_shows_yellow_feedback(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    assert tool.tabs.count() == 0

    tool.toolbar.labels_action.trigger()

    assert tool.footer_status.property("statusKind") == "warning"
    assert tool.footer_status.text() == BINARY_WORKBENCH_TEXT.STATUS_FILE_REQUIRED


def test_binary_workbench_restores_workspace_contexts_when_sources_exist(tmp_path: Path):
    binary_path = tmp_path / "restored.bin"
    binary_path.write_bytes(b"\xAA\xBB")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    tool.tabs.new_scratch_tab()
    window._state_service.save_default_binary_context(tool.export_state())
    restored = _window(tmp_path)
    restored._open_binary_workbench()
    restored_tool = restored._binary_workbench_window

    assert restored_tool is not None
    assert restored_tool.tabs.count() == 2
    assert [tab.kind for tab in restored_tool.export_state().tabs] == [
        BINARY_WORKBENCH_TAB_KIND.BINARY,
        BINARY_WORKBENCH_TAB_KIND.SCRATCH,
    ]


def test_binary_workbench_keeps_five_binary_workspaces_loaded_in_memory(tmp_path: Path):
    paths = []
    for index in range(6):
        path = tmp_path / f"memory_{index}.bin"
        path.write_bytes(bytes([index]) * 64)
        paths.append(path)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    for path in paths[:5]:
        tool.open_binary_path(path)
    assert all(tool.tabs.context_at(index).rows for index in range(5))

    tool.open_binary_path(paths[5])
    loaded = [
        context
        for context in tool.tabs._state.tabs  # type: ignore[attr-defined]
        if context.rows or context.versions
    ]

    assert len(loaded) == 5
    assert tool.tabs.current_context().rows


def test_binary_workbench_skips_missing_file_tabs_and_keeps_scratch_tabs(tmp_path: Path):
    missing = tmp_path / "missing.bin"
    missing.write_bytes(b"\xCC")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(missing)
    tool.tabs.new_scratch_tab()
    state = tool.export_state()
    missing.unlink()
    restored = _window(tmp_path)
    restored._binary_workbench_state = state
    restored._open_binary_workbench()
    restored_tool = restored._binary_workbench_window

    assert restored_tool is not None
    assert restored_tool.tabs.count() == 1
    assert restored_tool.export_state().tabs[0].kind == BINARY_WORKBENCH_TAB_KIND.SCRATCH


def test_binary_workbench_uses_separate_offset_columns_and_editable_panels(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    summary = tool.findChild(QLabel, "binary-workbench-selection")
    offset_panels = tool.findChildren(QPlainTextEdit, "binary-workbench-offsets-panel")
    bytes_panel = tool.findChild(QPlainTextEdit, "binary-workbench-bytes-panel")
    instruction_panel = tool.findChild(QPlainTextEdit, "binary-workbench-instructions-panel")
    close_button = tool.tabs.tabBar().close_button(0)
    headers = [label.text() for label in tool.findChildren(QLabel, "binary-workbench-column-label")]
    body_scroll = tool.findChild(QScrollBar, "binary-workbench-editor-scrollbar")

    assert summary is not None
    assert len(offset_panels) == 1
    assert all(panel.isReadOnly() is True for panel in offset_panels)
    assert all(panel.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff for panel in offset_panels)
    assert bytes_panel is not None and bytes_panel.isReadOnly() is False
    assert bytes_panel.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert instruction_panel is not None and instruction_panel.isReadOnly() is False
    assert instruction_panel.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert isinstance(close_button, QPushButton)
    assert close_button.text() == "X"
    assert headers == ["File", "Raw Instructions", "Bytes", "Instruction"]
    assert summary.text() == "Selected: none | Length: 0 bytes"
    assert body_scroll is not None


def test_binary_workbench_column_titles_have_shared_left_margin(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    tool.tabs.set_current_reference_offsets(
        ["File", "ram_offset"],
        {"File": "0x00000000", "ram_offset": "0x80010000"},
        {"File": True, "ram_offset": True},
    )
    labels = tool.findChildren(QLabel, "binary-workbench-column-label")

    assert labels
    assert "ram_offset" in {label.text() for label in labels}
    assert all(
        label.contentsMargins().left() == BINARY_WORKBENCH_LAYOUT.PANEL_LABEL_LEFT_MARGIN
        for label in labels
    )


def test_binary_workbench_instruction_and_bytes_edit_roundtrip(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    surface = page.grid  # type: ignore[attr-defined]
    surface.instructions.setPlainText("word 0x246301F4")
    _app().processEvents()

    assert surface.bytes.toPlainText().splitlines()[0] == "F4 01 63 24"
    surface.bytes.setPlainText("0C 00 23 96")
    _app().processEvents()
    assert surface.instructions.toPlainText().splitlines()[0] != ""


def test_binary_workbench_bytes_edit_updates_instruction_and_raw_panels(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    surface = page.grid  # type: ignore[attr-defined]
    surface.instructions.setPlainText("nop")
    assert surface.ensure_consistent("test").success
    surface.bytes.setPlainText("F4 01 63 24")
    _app().processEvents()
    instruction = surface.instructions.toPlainText().splitlines()[0]
    raw_instruction = surface.raw_instructions.toPlainText().splitlines()[0]

    assert instruction.startswith("ADDIU")
    assert "0x1F4" in instruction
    assert raw_instruction.startswith("addiu")
    assert "0x1f4" in raw_instruction.lower()


def test_binary_workbench_user_bytes_edit_preserves_matching_symbols(tmp_path: Path):
    binary_path = tmp_path / "source.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00 00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    tool.tabs.set_current_symbols({"variable1": "0x1F4"}, {"equate1": "0x34"}, {})
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText(  # type: ignore[attr-defined]
        "Entry: addiu $v1,$zero,_variable1\naddiu $s2,$zero,@equate1"
    )
    _app().processEvents()

    current = tool.tabs.current_context()
    assert current is not None
    assert "_variable1" in current.instruction_overlays["0x00000000"]

    page.grid.bytes.setPlainText("F4 01 63 24\n34 00 52 26")  # type: ignore[attr-defined]
    _app().processEvents()
    page.go_to_offset(0)
    _app().processEvents()
    current = tool.tabs.current_context()
    instructions = page.grid.instructions.toPlainText().splitlines()  # type: ignore[attr-defined]
    raw_instructions = page.grid.raw_instructions.toPlainText().splitlines()  # type: ignore[attr-defined]

    assert current is not None
    assert current.labels == {"Entry": "0x00000000"}
    assert current.instruction_overlays["0x00000000"].startswith("Entry:")
    assert "_variable1" in current.instruction_overlays["0x00000000"]
    assert "@equate1" in current.instruction_overlays["0x00000004"]
    assert instructions[0].startswith("Entry: ADDIU")
    assert "_variable1" in instructions[0]
    assert "@equate1" in instructions[1]
    assert "_variable1" not in raw_instructions[0]
    assert "@equate1" not in raw_instructions[1]


def test_binary_workbench_raw_instructions_show_preprocessed_mips(tmp_path: Path):
    assembly_path = tmp_path / "symbols.asm"
    assembly_path.write_text(
        "loop: addiu $s1, $zero, _variable1 ; comment\n"
        "addiu $s2, $zero, @equate1\n"
        "j loop\n"
        "li $v0, 1\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    current = tool.tabs.current_context()
    assert current is not None
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, current.labels)
    page = tool.tabs.currentWidget()
    raw_lines = page.grid.raw_instructions.toPlainText().split("\n")  # type: ignore[attr-defined]
    rows = tool.tabs.current_context().rows  # type: ignore[union-attr]

    assert raw_lines == [
        "addiu $s1, $zero, 20",
        "addiu $s2, $zero, 0x34",
        "j 0x80010000",
        "addiu $v0, $zero, 1",
    ]
    assert rows[0].bytes_text == "14 00 11 24"
    assert rows[1].bytes_text == "34 00 12 24"


def test_binary_workbench_symbols_recalculate_offsets_and_bytes(tmp_path: Path):
    assembly_path = tmp_path / "symbols.asm"
    assembly_path.write_text(
        "addiu $t1,$zero,_card_id\n"
        "addiu $a0,$zero,@spell_id\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    tool.tabs.set_current_symbols({"card_id": "0x1B3"}, {"spell_id": "0x15C"}, {})
    current = tool.tabs.current_context()
    page = tool.tabs.currentWidget()

    assert current is not None
    assert [row.offsets["File"] for row in current.rows[:2]] == ["0x00000000", "0x00000004"]
    assert [row.bytes_text for row in current.rows[:2]] == ["B3 01 09 24", "5C 01 04 24"]
    assert page.grid.bytes.toPlainText().splitlines()[:2] == ["B3 01 09 24", "5C 01 04 24"]  # type: ignore[attr-defined]


def test_binary_workbench_add_symbol_replaces_immediate_text(tmp_path: Path, monkeypatch):
    class Dialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *_args):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def symbol_name(self):
            return "card_id"

    monkeypatch.setattr(page_immediate_symbols_module, "ImmediateSymbolNameDialog", Dialog)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("addiu $t1,$zero,0x71")  # type: ignore[attr-defined]
    _app().processEvents()
    text = page.grid.instructions.toPlainText()  # type: ignore[attr-defined]
    start = text.index("0x71")
    page._add_immediate_symbol(  # type: ignore[attr-defined]
        BINARY_WORKBENCH_TEXT.SYMBOL_TARGET,
        "0x71",
        start,
        start + len("0x71"),
    )
    current = tool.tabs.current_context()

    assert current is not None
    assert current.symbols == {"card_id": "0x71"}
    assert current.variables == {"card_id": "0x71"}
    assert current.equates == current.variables
    assert page.grid.instructions.toPlainText() == "ADDIU $t1,$zero,@card_id"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText() == "71 00 09 24"  # type: ignore[attr-defined]


def test_binary_workbench_add_symbol_replaces_memory_operand(tmp_path: Path, monkeypatch):
    class Dialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *_args):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def symbol_name(self):
            return "actor_hp"

    monkeypatch.setattr(page_immediate_symbols_module, "ImmediateSymbolNameDialog", Dialog)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("lw $v0, 0x2CD($gp)")  # type: ignore[attr-defined]
    _app().processEvents()
    text = page.grid.instructions.toPlainText()  # type: ignore[attr-defined]
    start = text.index("0x2CD($gp)")
    page._add_immediate_symbol(  # type: ignore[attr-defined]
        BINARY_WORKBENCH_TEXT.SYMBOL_TARGET,
        "0x2CD($gp)",
        start,
        start + len("0x2CD($gp)"),
    )
    current = tool.tabs.current_context()

    assert current is not None
    assert current.symbols == {"actor_hp": "0x2CD($gp)"}
    assert current.variables == {"actor_hp": "0x2CD($gp)"}
    assert current.equates == current.variables
    assert page.grid.instructions.toPlainText() == "LW $v0, @actor_hp"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText() == "CD 02 82 8F"  # type: ignore[attr-defined]


def test_binary_workbench_add_symbol_preserves_instruction_and_bytes_cursors(
    tmp_path: Path,
):
    assembly_path = tmp_path / "cursor.asm"
    assembly_path.write_text("nop\naddiu $v0, $zero, 1\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]

    instruction_block = grid.instructions.document().findBlockByNumber(1)
    instruction_cursor = QTextCursor(instruction_block)
    instruction_cursor.setPosition(instruction_block.position() + 4)
    grid.instructions.setTextCursor(instruction_cursor)
    grid.instructions.setFocus()
    tool.tabs.set_current_symbols({"value": "0x20"}, {}, {})
    assert (
        grid.instructions.textCursor().blockNumber(),
        grid.instructions.textCursor().positionInBlock(),
    ) == (1, 4)

    bytes_block = grid.bytes.document().findBlockByNumber(1)
    bytes_cursor = QTextCursor(bytes_block)
    bytes_cursor.setPosition(bytes_block.position() + 3)
    grid.bytes.setTextCursor(bytes_cursor)
    grid.bytes.setFocus()
    tool.tabs.set_current_symbols({"value": "0x24"}, {}, {})
    assert (
        grid.bytes.textCursor().blockNumber(),
        grid.bytes.textCursor().positionInBlock(),
    ) == (1, 3)


def test_binary_workbench_editor_menu_uses_only_add_symbol_shortcut():
    assert CONTEXT_MENU_SHORTCUTS["Add Symbol"] == "Alt+W"
    assert "Add Variable" not in CONTEXT_MENU_SHORTCUTS
    assert "Add Equate" not in CONTEXT_MENU_SHORTCUTS
    assert "Alt+E" not in CONTEXT_MENU_SHORTCUTS.values()


def test_binary_workbench_environment_has_local_and_global_symbol_actions(
    tmp_path: Path,
):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    assert tool.toolbar.local_symbols_action.text() == BINARY_WORKBENCH_TEXT.LOCAL_SYMBOLS
    assert tool.toolbar.global_symbols_action.text() == BINARY_WORKBENCH_TEXT.GLOBAL_SYMBOLS
    assert tool.toolbar.symbols_action is tool.toolbar.local_symbols_action


def test_binary_workbench_binary_symbols_refresh_overlay_bytes(tmp_path: Path):
    binary_path = tmp_path / "symbols.bin"
    binary_path.write_bytes(bytes(8))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    current = tool.tabs.current_context()
    assert current is not None
    tool.tabs._set_current_context(  # type: ignore[attr-defined]
        BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "instruction_overlays": {
                    "0x00000000": "addiu $t1,$zero,_card_id",
                    "0x00000004": "addiu $a0,$zero,@spell_id",
                },
            }
        )
    )
    tool.tabs.set_current_symbols({"card_id": "0x1B3"}, {"spell_id": "0x15C"}, {})
    current = tool.tabs.current_context()
    page = tool.tabs.currentWidget()

    assert current is not None
    assert current.byte_overlays == {
        "0x00000000": "B3 01 09 24",
        "0x00000004": "5C 01 04 24",
    }
    assert page.grid.bytes.toPlainText().splitlines()[:2] == ["B3 01 09 24", "5C 01 04 24"]  # type: ignore[attr-defined]


def test_binary_workbench_editor_assembly_marks_hazards(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText(  # type: ignore[attr-defined]
        "lw $s1, 0($s0)\naddiu $s2, $s1, 1\nj 0x80010000\njal 0x80010010"
    )
    _app().processEvents()

    assert page.grid.raw_instructions.isReadOnly() is True  # type: ignore[attr-defined]
    assert page.grid.raw_instructions.extraSelections() == []  # type: ignore[attr-defined]
    assert len(page.grid.instructions.extraSelections()) == 2  # type: ignore[attr-defined]


def test_binary_workbench_li_stays_in_editor_and_converts_only_in_raw(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("li $v0, 1")  # type: ignore[attr-defined]
    _app().processEvents()

    assert page.grid.instructions.toPlainText().splitlines() == [  # type: ignore[attr-defined]
        "LI $v0, 1",
    ]
    assert page.grid.raw_instructions.toPlainText().splitlines() == [  # type: ignore[attr-defined]
        "addiu $v0, $zero, 1",
    ]
    assert page.grid.bytes.toPlainText().splitlines() == ["01 00 02 24"]  # type: ignore[attr-defined]


def test_binary_workbench_reads_asm_sources_as_text_by_default(tmp_path: Path):
    assembly_path = tmp_path / "double_summon.asm"
    assembly_path.write_text("addiu v1, v1, 0x1F4\nlhu v1, 0xC(s1)\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    current = tool.tabs.current_context()
    page = tool.tabs.currentWidget()

    assert current is not None and current.read_mode == "assembly"
    assert page is not None
    assert page.grid.instructions.toPlainText().splitlines()[0] == "ADDIU v1, v1, 0x1F4"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[0] != ""  # type: ignore[attr-defined]


def test_binary_workbench_applies_uppercase_when_loading_binary_windows(tmp_path: Path):
    binary_path = tmp_path / "scrolling.bin"
    binary_path.write_bytes(b"\xF4\x01\x63\x24" * 128)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()

    assert page is not None
    assert "ADDIU" in page.grid.instructions.toPlainText()  # type: ignore[attr-defined]
    scrollbar = page.grid.scrollbar  # type: ignore[attr-defined]
    scrollbar.setValue(scrollbar.maximum())
    _app().processEvents()

    assert "ADDIU" in page.grid.instructions.toPlainText()  # type: ignore[attr-defined]


def test_binary_workbench_tabs_use_truncated_labels_and_tooltips(tmp_path: Path):
    path = tmp_path / "averyveryveryverylong_binary_filename.bin"
    path.write_bytes(b"\x00\x00\x00\x00")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(path)

    assert tool.tabs.tabText(0) == f"{path.name[:18]}..."
    assert tool.tabs.tabBar().tabToolTip(0) == path.name
    assert tool.tabs.tabBar().isMovable() is True
    close_button = tool.tabs.tabBar().close_button(0)
    assert isinstance(close_button, QPushButton)
    assert close_button.text() == "X"
    assert close_button.isHidden() is False
    tab_rect = tool.tabs.tabBar().tabRect(0)
    close_rect = close_button.geometry()
    assert close_rect.right() <= tab_rect.right()
    assert close_rect.top() >= tab_rect.top()

    first_id = tool.tabs.context_at(0).tab_id
    tool.tabs.new_scratch_tab()
    second_id = tool.tabs.context_at(1).tab_id
    first_close_position = close_button.pos()
    tool.tabs.setCurrentIndex(1)
    _app().processEvents()
    assert close_button.pos() == first_close_position
    tool.tabs.tabBar().moveTab(1, 0)

    assert [tab.tab_id for tab in tool.export_state().tabs[:2]] == [second_id, first_id]


def test_binary_workbench_symbols_dialog_tolerates_non_string_values(tmp_path: Path):
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"flag": True}, {"base": 2048}, {"loop": "0x8000"})

    assert dialog.values()[0]["flag"] == "True"
    assert dialog.values()[0]["base"] == "2048"
    assert dialog.values()[1] == {}


def test_binary_workbench_ignores_semicolon_comments_when_loading_assembly(tmp_path: Path):
    assembly_path = tmp_path / "hook.asm"
    assembly_path.write_text(
        "; 675 = 0x02A3\n"
        "; hook 1 em 0x8001b590\n"
        "jal    0x1D9200 ; call SPELL\n"
        "; VERSÃƒO ENCURTADA\n"
        "addiu  $sp,$sp,-0x10\n"
        "sw     $a0,0x00($sp)\n"
        "sw     $a1,0x04($sp)\n"
        "sw     $ra,0x08($sp)\n"
        "lui    $t0,0x801A\n"
        "ori    $t0,$t0,0x7BD4\n"
        "subu   $t1,$t0,$v0\n"
        "sltiu  $t0,$t1,0x0071\n"
        "bne    $t0,$zero,0x8\n"
        "lhu    $t0,0x000C($v0)\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    current = tool.tabs.current_context()

    assert current is not None
    assert len(current.rows) == 14
    assert [row.offsets["File"] for row in current.rows[:5]] == [
        "-",
        "-",
        "0x00000000",
        "-",
        "0x00000004",
    ]
    assert [row.bytes_text for row in current.rows[:5]] == [
        "",
        "",
        "80 64 07 0C",
        "",
        "F0 FF BD 27",
    ]
    assert current.rows[2].instruction.startswith("jal")
    assert current.rows[2].bytes_text != "00 00 00 00"
    assert current.rows[-1].bytes_text != "00 00 00 00"
    page = tool.tabs.currentWidget()
    assert page.grid.raw_instructions.toPlainText().splitlines()[:5] == [  # type: ignore[attr-defined]
        "",
        "",
        "jal 0x1D9200",
        "",
        "addiu $sp, $sp, -0x10",
    ]
    assert page.grid.bytes.toPlainText().splitlines()[:5] == [  # type: ignore[attr-defined]
        "",
        "",
        current.rows[2].bytes_text,
        "",
        current.rows[4].bytes_text,
    ]
    tool.tabs.set_current_reference_offsets(
        ["File", "ram_offset"],
        {"File": "0x00000000", "ram_offset": "0x80010000"},
        {"File": True, "ram_offset": True},
    )
    page = tool.tabs.currentWidget()
    empty_offsets = [
        page.grid._offset_editors[name].toPlainText().splitlines()[0]  # type: ignore[attr-defined]
        for name in ("File", "ram_offset")
    ]
    assert all(
        value.strip() == "-"
        for value in empty_offsets
    )


def test_binary_workbench_opens_internal_file_from_configured_lba(tmp_path: Path):
    source = bytearray(2352)
    source[:12] = b"\x00" + (b"\xFF" * 10) + b"\x00"
    source[15] = 2
    source[24:28] = bytes.fromhex("AA BB CC DD")
    binary_path = tmp_path / "disc.bin"
    binary_path.write_bytes(source)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    assert tool.toolbar.open_internal_action.isEnabled() is True
    assert tool.toolbar.open_internal_action.shortcut().toString() == "Alt+I"
    tool._open_internal_file()
    assert tool.footer_status.property("statusKind") == "warning"
    assert tool.footer_status.text() == BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_REQUIREMENTS
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO(name="slus", start_lba=0)])
    assert tool.toolbar.open_internal_action.isEnabled() is True
    tool.tabs.open_internal_tab("slus")
    state = tool.export_state()

    assert tool.tabs.count() == 2
    assert state.tabs[-1].kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL
    assert state.tabs[-1].display_name == "slus"
    assert state.tabs[-1].internal_file_start_lba == 0
    assert state.tabs[-1].internal_parent_tab_id == state.tabs[0].tab_id
    assert "Binary" not in state.tabs[-1].reference_offsets
    assert state.tabs[-1].rows[0].offsets["File"] == "0x00000000"
    assert state.tabs[-1].rows[0].bytes_text == "AA BB CC DD"


def test_binary_workbench_internal_file_requires_binary_tab(tmp_path: Path):
    assembly_path = tmp_path / "source.asm"
    assembly_path.write_bytes(bytes(2048) + bytes.fromhex("AA BB CC DD"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO(name="chunk", start_lba=1)], 2048)
    tool.tabs.open_internal_tab("chunk")
    state = tool.export_state()

    assert len(state.tabs) == 1
    assert state.tabs[0].kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
    assert tool.footer_status.property("statusKind") == "warning"


def test_binary_workbench_internal_file_versions_and_saves_back_to_bin_offsets(tmp_path: Path):
    source = bytearray(2352)
    source[:12] = b"\x00" + (b"\xFF" * 10) + b"\x00"
    source[15] = 2
    source[24:28] = bytes.fromhex("AA BB CC DD")
    binary_path = tmp_path / "disc.bin"
    output_path = tmp_path / "patched.bin"
    binary_path.write_bytes(source)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO("SLUS", 0)])
    tool.tabs.open_internal_tab("SLUS")
    page = tool.tabs.currentWidget()
    lines = page.grid.bytes.toPlainText().splitlines()  # type: ignore[attr-defined]
    lines[0] = "11 22 33 44"
    page.grid.bytes.setPlainText("\n".join(lines))  # type: ignore[attr-defined]
    _app().processEvents()

    state = tool.export_state()
    assert state.tabs[0].byte_overlays["0x00000018"] == "11 22 33 44"
    page._load_visible_rows(256, page.grid.visible_size(), 1)  # type: ignore[attr-defined]
    page._load_visible_rows(0, page.grid.visible_size(), -1)  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[0] == "11 22 33 44"  # type: ignore[attr-defined]

    assert tool.tabs.create_version("internal-v1") is True
    version = tool.tabs.current_context().versions[-1]
    assert version.rows[0].offsets == {"File": "0x00000000"}
    assert version.rows[0].original_bytes_text == "AA BB CC DD"
    assert tool.tabs.save_current_workspace() is True
    parent = tool.export_state().tabs[0]
    parent_version = next(
        version for version in parent.versions if version.name == parent.active_version_name
    )
    assert parent_version.rows[0].offsets["File"] == "0x00000018"
    tool.tabs.close_tab(tool.tabs.currentIndex())
    tool.tabs.setCurrentIndex(0)
    tool.tabs.open_internal_tab("SLUS")
    reopened = tool.tabs.currentWidget()
    assert reopened.grid.bytes.toPlainText().splitlines()[0] == "11 22 33 44"  # type: ignore[attr-defined]
    assert tool.tabs.save_current_binary_copy(output_path) is True
    assert binary_path.read_bytes()[24:28] == bytes.fromhex("AA BB CC DD")
    assert output_path.read_bytes()[24:28] == bytes.fromhex("11 22 33 44")


def test_binary_workbench_versioning_saves_modified_copy_without_touching_original(tmp_path: Path):
    binary_path = tmp_path / "source.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00 11 22 33 44"))
    output_path = tmp_path / "patched.bin"
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    surface = page.grid  # type: ignore[attr-defined]
    surface.bytes.setPlainText("AA BB CC DD\n11 22 33 44")
    _app().processEvents()

    assert tool.tabs.create_version("v1") is True
    assert tool.export_state().tabs[0].active_version_name == "v1"
    assert len(tool.export_state().tabs[0].versions[0].rows) == 1
    assert tool.tabs.save_current_binary_copy(output_path) is True
    assert binary_path.read_bytes() == bytes.fromhex("00 00 00 00 11 22 33 44")
    assert output_path.read_bytes()[:8] == bytes.fromhex("AA BB CC DD 11 22 33 44")
    assert tool.export_state().directories["save_file"] == str(output_path.parent)
    assert str(output_path) in window._program_context.recent_files


def test_binary_workbench_save_file_uses_current_active_version_overlay(tmp_path: Path):
    binary_path = tmp_path / "source.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00"))
    output_path = tmp_path / "patched.bin"
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    assert tool.tabs.create_version("v1") is True
    page = tool.tabs.currentWidget()
    page.grid.bytes.setPlainText("AA BB CC DD")  # type: ignore[attr-defined]
    _app().processEvents()

    assert tool.tabs.save_current_binary_copy(output_path) is True
    assert output_path.read_bytes() == bytes.fromhex("AA BB CC DD")


def test_binary_workbench_workspace_restores_instruction_version_by_exact_source(tmp_path: Path):
    binary_path = tmp_path / "source.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00 00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("Label_1: addiu $s1,$s1,_variable1")  # type: ignore[attr-defined]
    _app().processEvents()

    assert tool.tabs.create_version("v1") is True
    assert tool.tabs.save_current_workspace() is True

    version_path = tmp_path / "data" / "binary_workbench" / "workspaces" / "Versions" / "source_workspace_manifest_versions.json"
    payload = version_path.read_text(encoding="utf-8")
    assert '"0x00000000"' in payload
    assert "Label_1:" in payload

    restored = _window(tmp_path)
    restored._open_binary_workbench()
    restored_tool = restored._binary_workbench_window

    assert restored_tool is not None
    restored_tool.open_binary_path(binary_path)
    current = restored_tool.tabs.current_context()

    assert current is not None
    assert current.active_version_name == "v1"
    assert current.variables == {"variable1": "20"}
    assert current.equates == {"equate1": "0x34"}
    assert current.labels == {"Label_1": "0x00000000"}
    assert current.instruction_overlays["0x00000000"].startswith("Label_1:")


def test_binary_workbench_saves_assembly_copy_and_persists_directory(tmp_path: Path):
    output_path = tmp_path / "edited.asm"
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    surface = page.grid  # type: ignore[attr-defined]
    surface.instructions.setPlainText("nop\naddiu $sp,$sp,-0x10")
    _app().processEvents()

    assert tool.tabs.save_current_assembly_copy(output_path) is True
    assert "ADDIU $sp,$sp,-0x10" in output_path.read_text(encoding="utf-8")
    assert tool.export_state().directories["save_assembly"] == str(output_path.parent)


def test_binary_workbench_open_file_action_calls_native_dialog_directly(
    tmp_path: Path,
    monkeypatch,
):
    """Keep native pickers on the direct QAction path without queued lag."""

    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    assert tool.tabs.current_context() is None
    calls = []
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: (calls.append(args) or ("", "")),
    )

    tool.toolbar.open_file_action.trigger()
    assert len(calls) == 1


def test_binary_workbench_toolbar_buttons_do_not_retain_modal_focus(tmp_path: Path):
    """The QAction keeps shortcuts without a stale hover-colored focus state."""

    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    assert all(
        button.focusPolicy() == Qt.NoFocus
        for button in tool.toolbar.findChildren(QToolButton)
    )


def test_binary_workbench_save_as_adopts_scratch_source_for_workspace_identity(tmp_path: Path, monkeypatch):
    output_path = tmp_path / "renamed.asm"
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("addiu $sp,$sp,-0x10")  # type: ignore[attr-defined]
    _app().processEvents()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output_path), ""))

    assert tool._save_assembly_code() is True
    current = tool.tabs.current_context()

    assert current is not None
    assert output_path.read_text(encoding="utf-8") == "ADDIU $sp,$sp,-0x10"
    assert current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
    assert current.display_name == "renamed.asm"
    assert current.source_path == str(output_path)
    assert tool.tabs.tabText(0) == "renamed.asm"
    assert tool.tabs.has_unsaved_changes(0) is False


def test_binary_workbench_close_save_persists_scratch_file_before_closing(tmp_path: Path, monkeypatch):
    output_path = tmp_path / "closed.asm"
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("nop\naddiu $sp,$sp,-0x10")  # type: ignore[attr-defined]
    _app().processEvents()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output_path), ""))
    monkeypatch.setattr(tool, "_native_close_question", lambda: QMessageBox.StandardButton.Save)

    tool._request_tab_close(0)

    assert tool.tabs.count() == 0
    assert "ADDIU $SP,$SP,-0X10" in output_path.read_text(encoding="utf-8").upper()
    assert (tmp_path / "data" / "binary_workbench" / "workspaces" / "closed_workspace_manifest.json").exists()


def test_binary_workbench_reference_offsets_adds_visible_offset_column(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    tool.tabs.set_current_reference_offsets(
        ["File", "ram_offset"],
        {"File": "0x00000000", "ram_offset": "0x80010000"},
        {"File": True, "ram_offset": True},
    )
    headers = [label.text() for label in tool.findChildren(QLabel, "binary-workbench-column-label")]
    offset_panels = tool.findChildren(QPlainTextEdit, "binary-workbench-offsets-panel")

    assert headers == ["File", "ram_offset", "Raw Instructions", "Bytes", "Instruction"]
    assert len(offset_panels) == 2
    assert offset_panels[1].toPlainText().splitlines()[0] == "0x80010000"


def test_binary_workbench_go_to_dialog_resolves_extra_offsets(tmp_path: Path):
    _app()
    dialog = BinaryWorkbenchGoToDialog(
        BinaryWorkbenchTabContextDTO(
            tab_id="tab",
            kind="scratch",
            display_name="scratch.asm",
            reference_offsets=["File", "ram_offset"],
            reference_offset_bases={"File": "0x00000000", "ram_offset": "0x80010000"},
        )
    )
    dialog.target.setCurrentText("ram_offset")
    dialog.value.setText("0x80010040")

    assert dialog.selected_offsets() == [0x40]


def test_binary_workbench_go_to_dialog_lists_hidden_extra_offsets(tmp_path: Path):
    _app()
    dialog = BinaryWorkbenchGoToDialog(
        BinaryWorkbenchTabContextDTO(
            tab_id="tab",
            kind="scratch",
            display_name="scratch.asm",
            reference_offsets=["File"],
            reference_offset_bases={"File": "0x00000000", "ram_offset": "0x80010000"},
        )
    )
    dialog.target.setCurrentText("ram_offset")
    dialog.value.setText("0x80010040")

    assert "ram_offset" in [dialog.target.itemText(index) for index in range(dialog.target.count())]
    assert dialog.selected_offsets() == [0x40]


def test_binary_workbench_go_to_resolves_lba_filesystem_name(tmp_path: Path):
    _app()
    dialog = BinaryWorkbenchGoToDialog(
        BinaryWorkbenchTabContextDTO(
            tab_id="tab",
            kind="binary",
            display_name="disc.bin",
            internal_files=[BinaryWorkbenchInternalFileDTO("slus", 24)],
            lba_sector_size=2048,
        )
    )
    dialog.target.setCurrentText(BINARY_WORKBENCH_TEXT.INTERNAL_FILE_TARGET)
    dialog.value.setText("slus")

    assert dialog.selected_offsets() == [24 * 2048]


def test_binary_workbench_go_to_supports_unaligned_offsets_and_labels(tmp_path: Path):
    assembly_path = tmp_path / "labels.asm"
    assembly_path.write_text("Label_1: addiu $s1,$s1,0x2\nj Label_1\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    current = tool.tabs.current_context()

    assert current is not None
    assert current.labels["Label_1"] == "0x00000000"
    dialog = BinaryWorkbenchGoToDialog(current)
    dialog.target.setCurrentText("Label")
    dialog.value.setText("Label_1")
    assert dialog.selected_offsets() == [0]
    binary_path = tmp_path / "offsets.bin"
    binary_path.write_bytes(bytes(range(128)))
    tool.open_file_path(binary_path)
    tool.tabs.go_to_offset(0x22)
    page = tool.tabs.currentWidget()
    assert page.current_cursor_offset() == 0x22  # type: ignore[attr-defined]


def test_binary_workbench_scrollbar_reaches_end_of_assembly(tmp_path: Path):
    assembly_path = tmp_path / "long.asm"
    assembly_path.write_text("\n".join("nop" for _ in range(120)), encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    page = tool.tabs.currentWidget()
    scrollbar = page.grid.scrollbar  # type: ignore[attr-defined]
    scrollbar.setValue(scrollbar.maximum())
    _app().processEvents()

    assert scrollbar.maximum() > 0
    assert "0x000001DC" in page.grid._offset_editors["File"].toPlainText()  # type: ignore[attr-defined]


def test_binary_workbench_down_arrow_loads_next_visible_window(tmp_path: Path):
    assembly_path = tmp_path / "long.asm"
    assembly_path.write_text("\n".join("nop" for _ in range(120)), encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    bottom_block = editor.cursorForPosition(
        QPoint(4, editor.viewport().height() - 2)
    ).block()
    cursor = editor.textCursor()
    cursor.setPosition(bottom_block.position())
    editor.setTextCursor(cursor)
    before_block = cursor.blockNumber()
    before = page.grid.scrollbar.value()  # type: ignore[attr-defined]
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Down, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(editor, event)
    _app().processEvents()

    assert page.grid.scrollbar.value() > before  # type: ignore[attr-defined]
    assert editor.textCursor().blockNumber() == before_block + 1


def test_binary_workbench_selection_counts_selected_bytes_exactly(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    surface = page.grid  # type: ignore[attr-defined]
    surface.bytes.setFocus()
    surface.select_offsets(1, 2)
    _app().processEvents()

    assert page.length_summary.text() == "Length (bytes): 2"  # type: ignore[attr-defined]


def test_binary_workbench_select_block_can_load_more_than_visible_rows(tmp_path: Path):
    binary_path = tmp_path / "wide.bin"
    binary_path.write_bytes(bytes(range(256)) * 4)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    tool.tabs.select_block(0, 255)
    _app().processEvents()

    assert page.length_summary.text() == "Length (bytes): 256"  # type: ignore[attr-defined]


def test_binary_workbench_select_block_defaults_to_typing_cursor_offset(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("nop\nnop")
    _app().processEvents()
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position())
    editor.setTextCursor(cursor)
    dialog = BinaryWorkbenchSelectBlockDialog(
        start_offset=tool.tabs.current_cursor_offset()
    )

    assert dialog.start.text() == "0x00000004"
    dialog.start.setText("0x20")
    dialog.length.setText("4")
    assert dialog.selected_range() == (0x20, 0x23)


def test_binary_workbench_replace_bytes_dialog_uses_cursor_offset_and_limits():
    from src.presentation.ui.components.binary_workbench.toolbar import BinaryWorkbenchToolbar

    _app()
    dialog = BinaryWorkbenchReplaceBytesDialog(start_offset=0x24)
    toolbar = BinaryWorkbenchToolbar()
    search_button = next(
        button
        for button in toolbar.findChildren(QToolButton)
        if button.text().strip() == BINARY_WORKBENCH_TEXT.SEARCH
    )

    assert dialog.start.text() == "0x00000024"
    assert toolbar.replace_bytes_action.shortcut().toString() == "Ctrl+R"
    assert toolbar.replace_bytes_action in search_button.menu().actions()
    dialog.end.setText("0x2B")
    dialog.length.setText("8")
    dialog.bytes_input.setPlainText("AA BB CC DD\n11 22 33 44")

    request = dialog.replacement_request()
    assert request is not None
    assert request.start_offset == 0x24
    assert request.data == bytes.fromhex("AA BB CC DD 11 22 33 44")


def test_binary_workbench_replace_bytes_uses_seek_outside_viewport(tmp_path: Path):
    binary_path = tmp_path / "replace.bin"
    binary_path.write_bytes(bytes(0x400))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    replacement = bytes.fromhex("AA BB CC DD")

    assert page.replacement_bytes_at(0x300, 4) == bytes(4)  # type: ignore[attr-defined]
    assert page.replace_bytes_at(0x300, replacement) is True  # type: ignore[attr-defined]
    assert page.replacement_bytes_at(0x300, 4) == replacement  # type: ignore[attr-defined]
    assert tool.tabs.current_context().byte_overlays["0x00000300"] == "AA BB CC DD"


def test_binary_workbench_replace_bytes_growth_requires_byte_shift_rule(tmp_path: Path):
    binary_path = tmp_path / "replace-growth.bin"
    binary_path.write_bytes(bytes(8))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    replacement = bytes.fromhex("AA BB CC DD 11 22")

    assert page.replacement_bytes_at(6, len(replacement)) is None  # type: ignore[attr-defined]
    assert page.replace_bytes_at(6, replacement) is False  # type: ignore[attr-defined]
    assert page.current_context().file_size == 8  # type: ignore[attr-defined]

    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))  # type: ignore[attr-defined]
    assert page.replacement_bytes_at(6, len(replacement)) == bytes(6)  # type: ignore[attr-defined]
    assert page.replace_bytes_at(6, replacement) is True  # type: ignore[attr-defined]

    current = page.current_context()  # type: ignore[attr-defined]
    assert current.file_size == 12
    assert current.byte_overlays["0x00000006"] == "AA BB CC DD 11 22"
    assert "0x00000008" in page.grid._offset_editors["File"].toPlainText()  # type: ignore[attr-defined]


def test_binary_workbench_replace_bytes_confirms_nonzero_targets(tmp_path: Path, monkeypatch):
    from src.core.binary_workbench.byte_replacement import ReplaceBytesRequest
    from src.presentation.ui.components.binary_workbench import window_search_actions

    binary_path = tmp_path / "nonzero.bin"
    binary_path.write_bytes(bytes.fromhex("01 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window
    request = ReplaceBytesRequest(0, bytes.fromhex("AA"))

    class AcceptedReplaceDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def replacement_request(self):
            return request

    monkeypatch.setattr(window_search_actions, "BinaryWorkbenchReplaceBytesDialog", AcceptedReplaceDialog)
    monkeypatch.setattr(window_search_actions, "confirm_nonzero_byte_replacement", lambda parent: False)

    assert tool is not None
    tool.open_binary_path(binary_path)
    tool._open_replace_bytes()
    assert tool.tabs.current_context().byte_overlays == {}

    monkeypatch.setattr(window_search_actions, "confirm_nonzero_byte_replacement", lambda parent: True)
    tool._open_replace_bytes()
    assert tool.tabs.current_context().byte_overlays["0x00000000"] == "AA"


def test_binary_workbench_binary_scrollbar_reaches_past_first_block(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes(range(256)) * 32)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    scrollbar = page.grid.scrollbar  # type: ignore[attr-defined]
    scrollbar.setValue(scrollbar.maximum())
    _app().processEvents()

    assert scrollbar.maximum() > 512
    assert page.grid._visible_start_offset > 512  # type: ignore[attr-defined]


def test_binary_workbench_binary_assembly_mode_still_scrolls_whole_source(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes(range(256)) * 32)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    current = tool.tabs.current_context()
    assert current is not None
    tool.tabs._set_current_context(  # type: ignore[attr-defined]
        BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "read_mode": "assembly",
                "rows": current.rows[:128],
            }
        )
    )
    page = tool.tabs.currentWidget()
    scrollbar = page.grid.scrollbar  # type: ignore[attr-defined]
    scrollbar.setValue(scrollbar.maximum())
    _app().processEvents()

    assert scrollbar.maximum() > 512
    assert page.grid._visible_start_offset > 512  # type: ignore[attr-defined]


def test_binary_workbench_ctrl_c_copies_entire_virtual_selection(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid._virtual_selection_range = (  # type: ignore[attr-defined]
        BINARY_WORKBENCH_TEXT.INSTRUCTION,
        0,
        0xE0,
    )
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.KeyboardModifier.ControlModifier)
    QApplication.sendEvent(page.grid.instructions, event)  # type: ignore[attr-defined]
    _app().processEvents()

    copied = QApplication.clipboard().text().splitlines()
    assert len(copied) == 57
    assert copied == ["nop"] * 57


def test_binary_workbench_raw_instructions_virtual_selection_is_visible(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid._select_visible_virtual_range(  # type: ignore[attr-defined]
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        0,
        0x10,
    )

    assert page.grid.raw_instructions.textCursor().selectedText().count("nop") == 5  # type: ignore[attr-defined]


def test_binary_workbench_virtual_bytes_delete_preserves_raw_and_undo(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("F4 01 63 24 34 00 52 26") + bytes.fromhex("00 00 00 00") * 78)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    bytes_editor = page.grid.bytes  # type: ignore[attr-defined]
    raw_editor = page.grid.raw_instructions  # type: ignore[attr-defined]
    offset_editor = next(iter(page.grid._offset_editors.values()))  # type: ignore[attr-defined]
    original_bytes = bytes_editor.toPlainText().splitlines()[:2]
    original_raw = raw_editor.toPlainText().splitlines()[:2]
    cursor = QTextCursor(bytes_editor.document())
    cursor.setPosition(0)
    cursor.setPosition(bytes_editor.document().findBlockByNumber(2).position(), QTextCursor.KeepAnchor)
    bytes_editor.setTextCursor(cursor)

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert bytes_editor.toPlainText().splitlines()[:2] == original_bytes
    assert raw_editor.toPlainText().splitlines()[:2] == original_raw
    assert offset_editor.toPlainText().splitlines()[:2] == ["0x00000000", "0x00000004"]
    assert bytes_editor.textCursor().position() <= bytes_editor.document().characterCount() - 1

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    _app().processEvents()

    assert bytes_editor.toPlainText().splitlines()[:2] == original_bytes


def test_binary_workbench_virtual_empty_bytes_line_blocks_backspace_shift(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("F4 01 63 24") + bytes.fromhex("00 00 00 00") * 79)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    bytes_editor = page.grid.bytes  # type: ignore[attr-defined]
    cursor = QTextCursor(bytes_editor.document())
    first = bytes_editor.document().findBlockByNumber(0)
    cursor.setPosition(first.position())
    cursor.setPosition(first.position() + len(first.text()), QTextCursor.KeepAnchor)
    bytes_editor.setTextCursor(cursor)
    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()
    text_after_clear = bytes_editor.toPlainText()

    cursor = bytes_editor.textCursor()
    cursor.setPosition(0)
    bytes_editor.setTextCursor(cursor)
    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert bytes_editor.toPlainText() == text_after_clear
    assert bytes_editor.textCursor().position() == 0


def test_binary_workbench_bytes_delete_preserves_assembly_annotations(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("entry: nop ; keep\nnop\n; comment\nnop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    bytes_editor = grid.bytes
    first = bytes_editor.document().findBlockByNumber(0)
    cursor = QTextCursor(first)
    cursor.setPosition(first.position())
    cursor.setPosition(first.position() + len(first.text()), QTextCursor.KeepAnchor)
    bytes_editor.setTextCursor(cursor)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert grid.instructions.toPlainText().splitlines() == [
        "entry: nop ; keep",
        "nop",
        "; comment",
        "nop",
    ]
    assert len(bytes_editor.toPlainText().split("\n")) == 4
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_BYTES_ROW_REMOVAL_BLOCKED]

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    _app().processEvents()

    assert bytes_editor.toPlainText().splitlines()[0] == "00 00 00 00"
    assert grid.instructions.toPlainText().splitlines()[0] == "entry: nop ; keep"


def test_binary_workbench_bytes_can_remove_empty_row_after_label(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.instructions.setPlainText("entry: nop\n\nnop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    bytes_editor = grid.bytes
    empty = bytes_editor.document().findBlockByNumber(1)
    cursor = QTextCursor(empty)
    cursor.setPosition(empty.position())
    bytes_editor.setTextCursor(cursor)

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert bytes_editor.document().blockCount() == 2
    assert grid.instructions.toPlainText().splitlines() == ["entry: nop", "nop"]


def test_binary_workbench_empty_bytes_row_removal_updates_all_columns_immediately(
    tmp_path: Path,
):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("\nspInit:\n\naddiu $sp, $sp, -0x60\nnop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    first_instruction = grid.bytes.document().findBlockByNumber(3)
    cursor = QTextCursor(first_instruction)
    cursor.setPosition(first_instruction.position())
    grid.bytes.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )

    expected_rows = 4
    editors = (
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    )
    assert all(editor.document().blockCount() == expected_rows for editor in editors)
    assert [line.lower() for line in grid.instructions.toPlainText().splitlines()] == [
        "",
        "spinit:",
        "addiu $sp, $sp, -0x60",
        "nop",
    ]
    assert grid.bytes.toPlainText().splitlines() == [
        "",
        "",
        "A0 FF BD 27",
        "00 00 00 00",
    ]
    assert grid.raw_instructions.toPlainText().splitlines() == [
        "",
        "",
        "addiu $sp, $sp, -0x60",
        "nop",
    ]
    assert grid._offset_editors["File"].toPlainText().splitlines() == [
        "-",
        "-",
        "0x00000000",
        "0x00000004",
    ]
    assert len(grid._consistency_coordinator._model_rows) == expected_rows

    grid._consistency_coordinator.prioritize_viewport()
    grid.instructions.setFocus()
    QTest.qWait(100)
    _app().processEvents()
    assert grid.instructions.document().blockCount() == expected_rows
    assert grid.bytes.toPlainText().splitlines() == [
        "",
        "",
        "A0 FF BD 27",
        "00 00 00 00",
    ]


def test_binary_workbench_completes_new_bytes_row_without_clearing_context(
    tmp_path: Path,
):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    assembly_path = tmp_path / "bytes-insert.asm"
    assembly_path.write_text(
        "\nspInit:\n\naddiu $sp, $sp, -0x60\nsw $a0, 0x0($sp)",
        encoding="utf-8",
    )
    tool.open_assembly_path(assembly_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    assert tool.tabs.current_context().active_version_name
    _app().processEvents()
    grid.flush_pending_rows_changed()
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
    assert grid.instructions.document().findBlockByNumber(2).text()
    current = tool.tabs.current_context()
    assert len(current.rows) == 5
    assert current.rows[2].bytes_text == "A0 FF BD 27"
    assert [row.offsets["File"] for row in current.rows] == [
        "-",
        "-",
        "0x00000000",
        "0x00000004",
        "0x00000008",
    ]
    active = next(
        version
        for version in current.versions
        if version.name == current.active_version_name
    )
    assert not active.rows
    QTest.qWait(100)
    _app().processEvents()
    assert grid.bytes.toPlainText().splitlines() == [
        "",
        "",
        "A0 FF BD 27",
        "A0 FF BD 27",
        "00 00 A4 AF",
    ]


def test_binary_workbench_bytes_edit_does_not_schedule_version_autosave(
    tmp_path: Path,
    monkeypatch,
):
    assembly_path = tmp_path / "bytes-no-autosave.asm"
    assembly_path.write_text("nop", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    scheduled: list[str] = []
    monkeypatch.setattr(tool.tabs._version_autosave, "schedule", scheduled.append)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]

    grid.bytes.setPlainText("01 00 00 00")
    _app().processEvents()

    assert scheduled == []


def test_binary_workbench_assembly_edit_schedules_deferred_version_autosave(
    tmp_path: Path,
    monkeypatch,
):
    assembly_path = tmp_path / "assembly-autosave.asm"
    assembly_path.write_text("nop", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    scheduled: list[str] = []
    monkeypatch.setattr(tool.tabs._version_autosave, "schedule", scheduled.append)
    current = tool.tabs.current_context()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]

    grid.instructions.setPlainText("addiu $t0, $zero, 1")
    QTest.qWait(250)
    _app().processEvents()

    assert scheduled == [current.tab_id]


def test_binary_workbench_bytes_cannot_remove_annotated_row_boundary(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.instructions.setPlainText("nop\nentry: nop ; keep")
    _app().processEvents()
    bytes_editor = grid.bytes
    annotated = bytes_editor.document().findBlockByNumber(1)
    cursor = QTextCursor(annotated)
    cursor.setPosition(annotated.position())
    bytes_editor.setTextCursor(cursor)
    original_bytes = bytes_editor.toPlainText()

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert bytes_editor.toPlainText() == original_bytes
    assert grid.instructions.toPlainText().splitlines()[1].startswith("entry:")


def test_binary_workbench_typing_bytes_keeps_same_line_label_and_comment(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("entry: nop ; keep")
    _app().processEvents()
    bytes_editor = grid.bytes
    bytes_editor.selectAll()
    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    for key, text in ((Qt.Key_1, "1"), (Qt.Key_2, "2"), (Qt.Key_3, "3"), (Qt.Key_4, "4")) * 2:
        QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text))
        _app().processEvents()

    instruction = grid.instructions.toPlainText()
    assert instruction.startswith("entry:")
    assert instruction.endswith("; keep")

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    _app().processEvents()

    assert grid.instructions.toPlainText().startswith("entry:")


def test_binary_workbench_retyping_nibble_keeps_inline_label(tmp_path: Path):
    assembly_path = tmp_path / "inline_label.asm"
    assembly_path.write_text(
        "spInit: addiu $sp, $sp, -0x60\n"
        "sw $a0, 0x0($sp)\n"
        "sw $a1, 0x4($sp)",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    bytes_editor = grid.bytes
    first = bytes_editor.document().findBlockByNumber(0)
    assert first.text() == "A0 FF BD 27"
    cursor = QTextCursor(first)
    cursor.setPosition(first.position() + len(first.text()))
    bytes_editor.setTextCursor(cursor)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)

    QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()
    assert bytes_editor.document().findBlockByNumber(0).text() == "A0 FF BD 2"
    assert grid.export_rows()[0].instruction == "spInit: addiu $sp, $sp, -0x60"
    assert warnings == []

    QApplication.sendEvent(
        bytes_editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_7, Qt.NoModifier, "7"),
    )
    _app().processEvents()

    assert bytes_editor.document().findBlockByNumber(0).text() == "A0 FF BD 27"
    assert grid.export_rows()[0].instruction == "spInit: addiu $sp, $sp, -0x60"
    assert warnings == []


def test_binary_workbench_bytes_typing_uses_configured_group_spacing():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.set_hex_input_mode(True, True, 2)

    for key, text in (
        (Qt.Key_A, "A"),
        (Qt.Key_A, "A"),
        (Qt.Key_B, "B"),
        (Qt.Key_B, "B"),
        (Qt.Key_C, "C"),
        (Qt.Key_C, "C"),
        (Qt.Key_D, "D"),
        (Qt.Key_D, "D"),
    ):
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text))

    assert editor.toPlainText() == "AABB CCDD"


def test_binary_workbench_bytes_undo_keeps_multiple_nibble_steps(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("nop")  # type: ignore[attr-defined]
    assert page.grid.ensure_consistent("test").success  # type: ignore[attr-defined]
    bytes_editor = page.grid.bytes  # type: ignore[attr-defined]
    bytes_editor.setPlainText("")
    _app().processEvents()
    bytes_editor.setFocus()

    for key, text in (
        (Qt.Key_A, "A"),
        (Qt.Key_B, "B"),
        (Qt.Key_C, "C"),
        (Qt.Key_D, "D"),
    ):
        QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text))
        _app().processEvents()

    assert "".join(bytes_editor.toPlainText().split()) == "ABCD"

    for expected in ("ABC", "AB", "A", ""):
        QApplication.sendEvent(bytes_editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
        _app().processEvents()
        assert "".join(bytes_editor.toPlainText().split()) == expected


def test_binary_workbench_large_binary_editor_keeps_ctrl_d_and_ctrl_q(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.setPosition(3, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_D, Qt.ControlModifier))
    _app().processEvents()
    assert len(editor.extraSelections()) == 2

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Q, Qt.ControlModifier))
    _app().processEvents()
    assert len(editor.extraSelections()) == 2


def test_binary_workbench_large_binary_instruction_line_replace_keeps_rows_and_undo(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("86 5B DE F2") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]

    editor.setFocus()
    original_lines = editor.toPlainText().splitlines()
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.setPosition(editor.document().findBlockByNumber(1).position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_X, Qt.NoModifier, "X"))
    _app().processEvents()

    changed_lines = editor.toPlainText().splitlines()
    assert changed_lines[0] == "X"
    assert changed_lines[1] == original_lines[1]
    assert len(changed_lines) == len(original_lines)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == original_lines


def test_binary_workbench_large_binary_instruction_backspace_keeps_cursor_line(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("86 5B DE F2") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    first = editor.document().findBlockByNumber(0)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(first.position() + len(first.text()))
    editor.setTextCursor(cursor)
    expected_position = cursor.position() - 1

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert editor.textCursor().blockNumber() == 0
    assert editor.textCursor().position() == expected_position


def test_binary_workbench_ctrl_c_copies_entire_raw_virtual_selection(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid._virtual_selection_range = (  # type: ignore[attr-defined]
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        0,
        0xE0,
    )
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.KeyboardModifier.ControlModifier)
    QApplication.sendEvent(page.grid.raw_instructions, event)  # type: ignore[attr-defined]
    _app().processEvents()

    copied = QApplication.clipboard().text().splitlines()
    assert len(copied) == 57
    assert copied == ["nop"] * 57


def test_binary_workbench_assembly_tabs_default_ctrl_s_target_is_instruction(tmp_path: Path):
    assembly_path = tmp_path / "call_umi.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)

    assert tool.tabs.focused_editor_kind() == BINARY_WORKBENCH_TEXT.INSTRUCTION


def test_binary_workbench_find_offsets_are_cached_in_context(tmp_path: Path):
    assembly_path = tmp_path / "find.asm"
    assembly_path.write_text("nop\naddiu $sp,$sp,-0x10\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    results = tool.tabs.find_offsets("Assembly instruction", "nop")
    current = tool.tabs.current_context()

    assert results == [0, 8]
    assert current is not None
    assert current.search_cache["Assembly instruction:nop"] == ["0x00000000", "0x00000008"]
    assert (tmp_path / "data" / "binary_workbench" / "search_cache.json").exists()


def test_binary_workbench_find_dialog_limits_length_and_prefills_start():
    _app()
    captured: list[tuple[int | None, int | None, int | None]] = []

    def search(_mode, _query, start, end, limit):
        captured.append((start, end, limit))
        return [0]

    dialog = BinaryWorkbenchFindDialog(search, lambda: captured[-1][1])
    dialog.length.setText(str(BINARY_WORKBENCH_FIND_MAX_LENGTH_KB + 1))

    dialog.refresh_results()

    max_length_bytes = BINARY_WORKBENCH_FIND_MAX_LENGTH_KB * 1024
    assert captured == [(0, max_length_bytes - 1, None)]
    assert dialog.length.text() == str(BINARY_WORKBENCH_FIND_MAX_LENGTH_KB)
    assert dialog.start.text() == f"0x{max_length_bytes - 1:08X}"
    assert dialog.width() == BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_DIALOG_WIDTH
    assert dialog.height() == BINARY_WORKBENCH_LAYOUT.SEARCH_FIND_DIALOG_HEIGHT


def test_binary_workbench_find_dialog_empty_length_defaults_to_two_mb():
    _app()
    captured: list[tuple[int | None, int | None]] = []

    def search(_mode, _query, start, end, _limit):
        captured.append((start, end))
        return []

    dialog = BinaryWorkbenchFindDialog(search, lambda: captured[-1][1])

    dialog.refresh_results()

    default_bytes = BINARY_WORKBENCH_FIND_DEFAULT_LENGTH_KB * 1024
    assert captured == [(0, default_bytes - 1)]


def test_binary_workbench_find_decoded_text_ansi_respects_offset_range(tmp_path: Path):
    binary_path = tmp_path / "decoded.bin"
    binary_path.write_bytes(bytes.fromhex("00 48 45 4C 4C 4F 00 E7 E3 6F 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)

    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "HELLO") == [1]
    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "Ã§Ã£o") == [7]
    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "HELLO", end_offset=5) == [1]
    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "HELLO", start_offset=2) == []


def test_binary_workbench_find_assembly_mnemonic_uses_partial_byte_search(tmp_path: Path):
    binary_path = tmp_path / "partial_instruction.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00 F0 FF BD 27 00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)

    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY, "ADDIU") == [4]


def test_binary_workbench_ctrl_s_persists_open_assembly_source(tmp_path: Path):
    assembly_path = tmp_path / "edited.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("addiu $sp,$sp,-0x10")  # type: ignore[attr-defined]
    _app().processEvents()

    assert tool.tabs.save_current_source_file() is True
    assert assembly_path.read_text(encoding="utf-8") == "ADDIU $sp,$sp,-0x10"


def test_binary_workbench_ctrl_s_exports_versioned_assembly_without_mutating_versions(
    tmp_path: Path,
    monkeypatch,
):
    assembly_path = tmp_path / "call_umi.asm"
    output_path = tmp_path / "call_umi_default.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("jal 0x80010000")  # type: ignore[attr-defined]
    _app().processEvents()
    before = list(tool.tabs.current_context().versions)
    captured = {}

    def save_dialog(*args):
        captured["initial"] = args[2]
        return str(output_path), ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", save_dialog)
    monkeypatch.setattr(
        tool.tabs._workspace_repository,  # type: ignore[attr-defined]
        "save_tab_workspace",
        lambda *args, **kwargs: pytest.fail("Ctrl+S must not persist Versions"),
    )

    tool._save_current_tab()

    assert Path(captured["initial"]).name == "call_umi_default.asm"
    assert assembly_path.read_text(encoding="utf-8") == "nop\n"
    assert output_path.read_text(encoding="utf-8") == "JAL 0x80010000"
    assert tool.tabs.current_context().versions == before


def test_binary_workbench_save_uses_last_focused_editor_after_focus_moves(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setFocus()  # type: ignore[attr-defined]
    _app().processEvents()
    page.grid.instructions.clearFocus()  # type: ignore[attr-defined]

    assert tool.tabs.focused_editor_kind() == BINARY_WORKBENCH_TEXT.INSTRUCTION


def test_binary_workbench_search_menu_hides_select_all_action(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    search_button = next(
        button for button in tool.toolbar.findChildren(QToolButton) if button.text().strip() == "Search"
    )
    action_names = [action.text() for action in search_button.menu().actions()]

    assert BINARY_WORKBENCH_TEXT.SELECT_ALL not in action_names
    assert tool.toolbar.select_all_action.shortcut().toString() == "Ctrl+A"


def test_binary_workbench_ctrl_a_selects_entire_binary_content(tmp_path: Path):
    binary_path = tmp_path / "wide.bin"
    binary_path.write_bytes(bytes(range(256)) * 20)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid.bytes.setFocus()  # type: ignore[attr-defined]
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_A, Qt.KeyboardModifier.ControlModifier)
    QApplication.sendEvent(page.grid.bytes, event)  # type: ignore[attr-defined]
    _app().processEvents()

    assert page.length_summary.text() == "Length (bytes): 5120"  # type: ignore[attr-defined]


def test_binary_workbench_ctrl_a_uses_focus_and_limit_for_all_virtual_code_columns(tmp_path: Path):
    binary_path = tmp_path / "selection_limit.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * ((1024 * 1024 // 4) + 8))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.set_selection_limit_bytes(1024 * 1024)
    expected = {
        BINARY_WORKBENCH_TEXT.BYTES: 1024 * 1024 - 1,
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: 1024 * 1024 - 4,
        BINARY_WORKBENCH_TEXT.INSTRUCTION: 1024 * 1024 - 4,
    }
    editors = {
        BINARY_WORKBENCH_TEXT.BYTES: grid.bytes,
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: grid.raw_instructions,
        BINARY_WORKBENCH_TEXT.INSTRUCTION: grid.instructions,
    }
    grid.raw_shell.setVisible(True)
    grid.set_visible_offset(0x200)
    grid.bytes.setFocus()
    _app().processEvents()
    tool.toolbar.select_all_action.trigger()
    _app().processEvents()
    assert grid._virtual_selection_range == (
        BINARY_WORKBENCH_TEXT.BYTES,
        0,
        expected[BINARY_WORKBENCH_TEXT.BYTES],
    )
    assert grid.scrollbar.value() == 0
    assert grid.bytes.textCursor().hasSelection()

    for kind, editor in editors.items():
        grid._set_last_editor(kind)
        editor.setFocus()
        _app().processEvents()
        QApplication.sendEvent(
            editor,
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key_A,
                Qt.ControlModifier,
                "a",
            ),
        )
        _app().processEvents()
        assert grid._virtual_selection_range == (kind, 0, expected[kind])
        assert grid.scrollbar.value() == 0
        assert editor.textCursor().hasSelection()


def test_binary_workbench_ctrl_a_selection_survives_multiple_viewports(tmp_path: Path):
    binary_path = tmp_path / "ctrl_a_scroll.bin"
    source = bytes(range(256)) * 8
    binary_path.write_bytes(source)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    editor = grid.bytes
    editor.setFocus()
    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_A, Qt.ControlModifier, "a"),
    )
    _app().processEvents()
    expected = (BINARY_WORKBENCH_TEXT.BYTES, 0, len(source) - 1)

    for offset in (0x100, 0x300, 0x700, 0x40):
        grid.set_visible_offset(offset)
        _app().processEvents()
        assert grid._virtual_selection_range == expected
        assert grid._viewport_line_selection is None
        assert editor.textCursor().hasSelection()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.ControlModifier),
    )
    assert "".join(QApplication.clipboard().text().split()) == source.hex().upper()


def test_binary_workbench_select_block_survives_multiple_viewports(tmp_path: Path):
    binary_path = tmp_path / "select_block_scroll.bin"
    source = bytes(range(256)) * 8
    binary_path.write_bytes(source)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.bytes.setFocus()
    page.select_block(0x20, 0x307)
    _app().processEvents()
    expected = (BINARY_WORKBENCH_TEXT.BYTES, 0x20, 0x307)

    for offset in (0x100, 0x280, 0x40):
        grid.set_visible_offset(offset)
        _app().processEvents()
        assert grid._virtual_selection_range == expected
        assert grid._viewport_line_selection is None
        assert grid.bytes.textCursor().hasSelection()

    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.ControlModifier),
    )
    copied = "".join(QApplication.clipboard().text().split())
    assert copied == source[0x20:0x308].hex().upper()


def _select_editor_line(editor, line: int) -> None:
    block = editor.document().findBlockByNumber(line)
    assert block.isValid()
    cursor = editor.textCursor()
    cursor.setPosition(block.position())
    cursor.setPosition(block.position() + len(block.text()), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    editor.setFocus()


def _selected_grid_row_offset(grid, editor) -> int | None:
    cursor = editor.textCursor()
    if not cursor.hasSelection():
        return None
    block = editor.document().findBlock(cursor.selectionStart())
    return grid._row_offset(block.blockNumber())


@pytest.mark.parametrize(
    "column",
    [
        "File",
        "ram_offset",
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        BINARY_WORKBENCH_TEXT.BYTES,
        BINARY_WORKBENCH_TEXT.INSTRUCTION,
    ],
)
def test_binary_workbench_virtual_selection_stays_with_exact_offset_line(tmp_path: Path, column: str):
    binary_path = tmp_path / f"line_selection_{column}.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 1024)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    if column == "ram_offset":
        tool.tabs.set_current_reference_offsets(
            ["File", "ram_offset"],
            {"File": "0x00000000", "ram_offset": "0x80010000"},
            {"File": True, "ram_offset": True},
        )
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.raw_shell.setVisible(True)
    grid.set_visible_offset(0x40)
    _app().processEvents()
    editors = {
        "File": grid._offset_editors["File"],
        "ram_offset": grid._offset_editors.get("ram_offset"),
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: grid.raw_instructions,
        BINARY_WORKBENCH_TEXT.BYTES: grid.bytes,
        BINARY_WORKBENCH_TEXT.INSTRUCTION: grid.instructions,
    }
    editor = editors[column]
    assert editor is not None
    selected_offset = 0x64
    row = next(index for index in range(len(grid._rows)) if grid._row_offset(index) == selected_offset)
    _select_editor_line(editor, row)

    grid.set_visible_offset(0x44)
    _app().processEvents()
    assert _selected_grid_row_offset(grid, editor) == selected_offset

    grid.set_visible_offset(0x200)
    _app().processEvents()
    assert not editor.textCursor().hasSelection()
    assert grid._viewport_line_selection is not None

    grid.set_visible_offset(0x40)
    _app().processEvents()
    assert grid._viewport_line_selection is not None
    assert _selected_grid_row_offset(grid, editor) == selected_offset


def test_binary_workbench_file_offset_selection_stays_on_offset_c8(tmp_path: Path):
    binary_path = tmp_path / "file_offset_selection.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 1024)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.set_visible_offset(0xA0)
    _app().processEvents()
    editor = grid._offset_editors["File"]
    selected_offset = 0xC8
    row = next(index for index in range(len(grid._rows)) if grid._row_offset(index) == selected_offset)
    _select_editor_line(editor, row)

    grid.set_visible_offset(0xA4)
    _app().processEvents()

    assert _selected_grid_row_offset(grid, editor) == selected_offset


def test_binary_workbench_virtual_instruction_comment_selection_stays_on_source_line(tmp_path: Path):
    binary_path = tmp_path / "comment_line_selection.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 1024)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.set_visible_offset(0x40)
    _app().processEvents()
    editor = grid.instructions
    lines = editor.toPlainText().splitlines()
    lines.insert(5, "; selected comment")
    editor.setPlainText("\n".join(lines))
    _app().processEvents()
    grid.flush_pending_rows_changed()
    _app().processEvents()
    _select_editor_line(editor, 5)

    grid.set_visible_offset(0x44)
    _app().processEvents()
    assert editor.textCursor().selection().toPlainText() == "; selected comment"
    assert editor.textCursor().blockNumber() == 4

    grid.set_visible_offset(0x200)
    _app().processEvents()
    assert not editor.textCursor().hasSelection()

    grid.set_visible_offset(0x40)
    _app().processEvents()
    assert editor.textCursor().selection().toPlainText() == "; selected comment"
    assert editor.textCursor().blockNumber() == 5


def test_binary_workbench_bytes_and_raw_clipboard_ignore_empty_lines(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.raw_instructions.setPlainText("nop\n\naddiu $v0, $zero, 1")
    grid.raw_instructions.selectAll()
    QApplication.sendEvent(
        grid.raw_instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.ControlModifier),
    )
    assert QApplication.clipboard().text() == "nop\naddiu $v0, $zero, 1"

    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.set_bytes_line_shift_allowed(True)
    QApplication.clipboard().setText("AA BB\n\nCC DD")
    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )
    assert editor.toPlainText() == "AA BB\nCC DD"


def test_binary_workbench_mouse_wheel_preserves_virtual_selection(tmp_path: Path):
    binary_path = tmp_path / "wheel_selection.bin"
    binary_path.write_bytes(bytes(range(256)) * 4096)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.select_offsets(0x20, 0x27)
    wheel = QWheelEvent(
        QPointF(8, 8),
        QPointF(8, 8),
        QPoint(),
        QPoint(0, -120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )

    grid.bytes.wheelEvent(wheel)
    _app().processEvents()

    assert grid.scrollbar.value() > 0
    assert grid._virtual_selection_range == (BINARY_WORKBENCH_TEXT.BYTES, 0x20, 0x27)
    assert _selected_grid_row_offset(grid, grid.bytes) == 0x20
    QApplication.sendEvent(
        grid.bytes,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.ControlModifier),
    )
    assert QApplication.clipboard().text().splitlines() == [
        "20 21 22 23",
        "24 25 26 27",
    ]


def test_binary_workbench_wheel_and_page_down_extend_held_mouse_selection(tmp_path: Path):
    binary_path = tmp_path / "held_mouse_selection.bin"
    binary_path.write_bytes(bytes(range(256)) * 16)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    editor = grid.bytes
    _select_editor_line(editor, 0)
    editor._left_mouse_selecting = True
    editor.wheelEvent(
        QWheelEvent(
            QPointF(8, 8),
            QPointF(8, 8),
            QPoint(),
            QPoint(0, -120),
            Qt.LeftButton,
            Qt.NoModifier,
            Qt.ScrollUpdate,
            False,
        )
    )
    _app().processEvents()

    first_range = grid._virtual_selection_range
    assert first_range is not None
    assert first_range[0] == BINARY_WORKBENCH_TEXT.BYTES
    assert first_range[1] == 0
    assert first_range[2] > 3

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageDown, Qt.NoModifier),
    )
    _app().processEvents()
    editor._left_mouse_selecting = False

    assert grid._virtual_selection_range is not None
    assert grid._virtual_selection_range[1] == 0
    assert grid._virtual_selection_range[2] > first_range[2]


def test_binary_workbench_raw_selection_scroll_keeps_all_visible_lines(tmp_path: Path):
    binary_path = tmp_path / "raw_selection_visual.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 256)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    editor = grid.raw_instructions
    _select_editor_line(editor, 0)
    editor._left_mouse_selecting = True

    for _ in range(6):
        editor.wheelEvent(
            QWheelEvent(
                QPointF(8, editor.viewport().height() - 1),
                QPointF(8, editor.viewport().height() - 1),
                QPoint(),
                QPoint(0, -120),
                Qt.LeftButton,
                Qt.NoModifier,
                Qt.ScrollUpdate,
                False,
            )
        )
        _app().processEvents()
        lines = editor.toPlainText().splitlines()
        assert len(lines) == len(grid._rows)
        assert all(line.lower() == "nop" for line in lines)
        assert editor.textCursor().hasSelection()
        assert editor.verticalScrollBar().value() == 0

    editor._left_mouse_selecting = False


def test_binary_workbench_bytes_selection_expands_across_multiple_viewports(tmp_path: Path):
    binary_path = tmp_path / "multiple_viewport_selection.bin"
    source = bytes(range(256)) * 16
    binary_path.write_bytes(source)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    editor = grid.bytes
    grid.select_offsets(0x20, 0x27)
    grid._capture_virtual_selection_anchor(editor)

    for visible_offset in (0x100, 0x200, 0x300):
        grid.set_visible_offset(visible_offset)
        _app().processEvents()
        positions = grid._byte_selection_positions(
            visible_offset + 7,
            visible_offset + 7,
        )
        assert positions is not None
        cursor = editor.textCursor()
        cursor.setPosition(positions[1])
        editor.setTextCursor(cursor)
        grid._restore_virtual_selection(editor)
        assert grid._virtual_selection_range == (
            BINARY_WORKBENCH_TEXT.BYTES,
            0x20,
            visible_offset + 7,
        )

    expected_range = (BINARY_WORKBENCH_TEXT.BYTES, 0x20, 0x307)
    for visible_offset in (0x180, 0x80, 0x280):
        grid.set_visible_offset(visible_offset)
        _app().processEvents()
        assert grid._virtual_selection_range == expected_range
        assert editor.textCursor().hasSelection()

    for delta in (-120, 120):
        editor.wheelEvent(
            QWheelEvent(
                QPointF(8, 8),
                QPointF(8, 8),
                QPoint(),
                QPoint(0, delta),
                Qt.NoButton,
                Qt.NoModifier,
                Qt.ScrollUpdate,
                False,
            )
        )
        _app().processEvents()
        assert grid._virtual_selection_range == expected_range
        assert editor.textCursor().hasSelection()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.ControlModifier),
    )
    copied = "".join(QApplication.clipboard().text().split())
    assert copied == source[0x20:0x308].hex().upper()


def test_binary_workbench_page_keys_use_standard_direction_and_preserve_typing_cursor(tmp_path: Path):
    assembly_path = tmp_path / "page_navigation.asm"
    assembly_path.write_text("\n".join("nop" for _ in range(2048)), encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    editor = grid.instructions
    cursor = editor.textCursor()
    block = editor.document().findBlockByNumber(2)
    cursor.setPosition(block.position() + 1)
    editor.setTextCursor(cursor)
    page_size = grid.scrollbar.pageStep()
    steps = 4

    for _ in range(steps):
        QApplication.sendEvent(
            editor,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageDown, Qt.NoModifier),
        )
        _app().processEvents()
    assert grid.scrollbar.value() == min(steps * page_size, grid.scrollbar.maximum())
    assert editor.textCursor().blockNumber() == 2
    assert editor.textCursor().positionInBlock() == 1

    for _ in range(steps):
        QApplication.sendEvent(
            editor,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageUp, Qt.NoModifier),
        )
        _app().processEvents()
    assert grid.scrollbar.value() == 0
    assert editor.textCursor().blockNumber() == 2
    assert editor.textCursor().positionInBlock() == 1


def test_binary_workbench_wheel_scroll_is_not_limited_by_typing_cursor(tmp_path: Path):
    assembly_path = tmp_path / "wheel_navigation.asm"
    assembly_path.write_text("\n".join("nop" for _ in range(512)), encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    editor = grid.instructions
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(2).position() + 1)
    editor.setTextCursor(cursor)
    steps = 40

    for index in range(steps):
        editor.wheelEvent(
            QWheelEvent(
                QPointF(8, 8),
                QPointF(8, 8),
                QPoint(),
                QPoint(0, -120),
                Qt.NoButton,
                Qt.NoModifier,
                Qt.ScrollUpdate,
                False,
            )
        )
        _app().processEvents()
        if index == 0:
            wheel_step = grid.scrollbar.value()

    assert grid.scrollbar.value() == min(
        steps * wheel_step,
        grid.scrollbar.maximum(),
    )
    assert editor.textCursor().blockNumber() == 2
    assert editor.textCursor().positionInBlock() == 1


def test_binary_workbench_virtual_columns_stay_synchronized_with_focused_editor(tmp_path: Path):
    binary_path = tmp_path / "synchronized_viewports.bin"
    binary_path.write_bytes(bytes(range(256)) * 32)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    assert grid._virtual

    navigation_editors = [
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.instructions,
    ]
    for editor in navigation_editors:
        editor.setFocus()
        cursor = editor.textCursor()
        last_block = editor.document().lastBlock()
        cursor.setPosition(last_block.position() + len(last_block.text()))
        editor.setTextCursor(cursor)
        before = grid.scrollbar.value()

        QApplication.sendEvent(
            editor,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageDown, Qt.NoModifier),
        )
        _app().processEvents()
        QTest.qWait(20)

        assert grid.scrollbar.value() > before
        assert grid._visible_start_offset == grid.scrollbar.value()
        visible_editors = [
            *grid._offset_editors.values(),
            grid.raw_instructions,
            grid.bytes,
            grid.decoded_text,
            grid.instructions,
        ]
        assert all(candidate.document().blockCount() == len(grid._rows) for candidate in visible_editors)
        assert all(candidate.verticalScrollBar().value() == 0 for candidate in visible_editors)
        assert all(candidate.firstVisibleBlock().blockNumber() == 0 for candidate in visible_editors)

        if editor in {grid.bytes, grid.instructions}:
            cursor = editor.textCursor()
            last_block = editor.document().lastBlock()
            cursor.setPosition(last_block.position())
            editor.setTextCursor(cursor)
            before_offset = grid._visible_start_offset
            before_line = (before_offset // 4) + cursor.blockNumber()
            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Down, Qt.NoModifier),
            )
            _app().processEvents()
            assert grid._visible_start_offset == before_offset + 4
            assert (grid._visible_start_offset // 4) + editor.textCursor().blockNumber() == before_line + 1
            assert all(candidate.firstVisibleBlock().blockNumber() == 0 for candidate in visible_editors)

            cursor = editor.textCursor()
            cursor.setPosition(editor.document().firstBlock().position())
            editor.setTextCursor(cursor)
            before_offset = grid._visible_start_offset
            before_line = before_offset // 4
            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Up, Qt.NoModifier),
            )
            _app().processEvents()
            assert grid._visible_start_offset == before_offset - 4
            assert (grid._visible_start_offset // 4) + editor.textCursor().blockNumber() == before_line - 1
            assert all(candidate.firstVisibleBlock().blockNumber() == 0 for candidate in visible_editors)


def test_binary_workbench_assembly_columns_stay_synchronized_after_page_navigation(tmp_path: Path):
    assembly_path = tmp_path / "synchronized_assembly.asm"
    assembly_path.write_text(
        "\n".join(
            "; comment" if index % 9 == 0 else f"addiu $t0, $t0, 0x{index:X}"
            for index in range(180)
        ),
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    assert not grid._virtual

    visible_editors = [
        *grid._offset_editors.values(),
        grid.raw_instructions,
        grid.bytes,
        grid.decoded_text,
        grid.instructions,
    ]
    navigation_editors = [
        editor
        for editor in (
            *grid._offset_editors.values(),
            grid.raw_instructions,
            grid.bytes,
            grid.instructions,
        )
        if editor.isVisible()
    ]
    for editor in navigation_editors:
        grid.set_visible_offset(0)
        _app().processEvents()
        editor.setFocus()
        cursor = editor.textCursor()
        block = editor.document().findBlockByNumber(2)
        cursor.setPosition(block.position() + min(1, len(block.text())))
        editor.setTextCursor(cursor)

        for _ in range(2):
            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageDown, Qt.NoModifier),
            )
            _app().processEvents()
        QTest.qWait(20)

        expected = grid._visible_block_position(grid.scrollbar.value() // 4)
        assert grid.scrollbar.value() > 0
        assert all(candidate.verticalScrollBar().value() == expected for candidate in visible_editors)
        assert len({candidate.firstVisibleBlock().blockNumber() for candidate in visible_editors}) == 1

        if editor in {grid.bytes, grid.instructions}:
            middle_block = editor.firstVisibleBlock().next().next()
            cursor = editor.textCursor()
            cursor.setPosition(middle_block.position())
            editor.setTextCursor(cursor)
            before_arrow = grid.scrollbar.value()
            before_block = cursor.blockNumber()
            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Down, Qt.NoModifier),
            )
            _app().processEvents()
            assert editor.textCursor().blockNumber() == before_block + 1
            assert grid.scrollbar.value() == before_arrow

            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Up, Qt.NoModifier),
            )
            _app().processEvents()
            assert editor.textCursor().blockNumber() == before_block
            assert grid.scrollbar.value() == before_arrow

            bottom_block = editor.cursorForPosition(
                QPoint(4, editor.viewport().height() - 2)
            ).block()
            cursor = editor.textCursor()
            cursor.setPosition(bottom_block.position())
            editor.setTextCursor(cursor)
            before_arrow = grid.scrollbar.value()
            before_block = cursor.blockNumber()
            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Down, Qt.NoModifier),
            )
            _app().processEvents()
            assert editor.textCursor().blockNumber() == before_block + 1
            assert grid.scrollbar.value() > before_arrow
            assert len({candidate.firstVisibleBlock().blockNumber() for candidate in visible_editors}) == 1

            top_block = editor.firstVisibleBlock()
            cursor = editor.textCursor()
            cursor.setPosition(top_block.position())
            editor.setTextCursor(cursor)
            before_arrow = grid.scrollbar.value()
            before_block = cursor.blockNumber()
            QApplication.sendEvent(
                editor,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Up, Qt.NoModifier),
            )
            _app().processEvents()
            assert editor.textCursor().blockNumber() == before_block - 1
            assert grid.scrollbar.value() < before_arrow
            assert len({candidate.firstVisibleBlock().blockNumber() for candidate in visible_editors}) == 1

        before_wheel = grid.scrollbar.value()
        editor.wheelEvent(
            QWheelEvent(
                QPointF(8, 8),
                QPointF(8, 8),
                QPoint(),
                QPoint(0, -120),
                Qt.NoButton,
                Qt.NoModifier,
                Qt.ScrollUpdate,
                False,
            )
        )
        _app().processEvents()
        QTest.qWait(20)
        assert grid.scrollbar.value() > before_wheel
        assert len({candidate.firstVisibleBlock().blockNumber() for candidate in visible_editors}) == 1


def test_binary_workbench_shift_backspace_deletes_without_inserting_control_character():
    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("nop")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.ShiftModifier, "\b"),
    )

    assert editor.toPlainText() == "no"


def test_binary_workbench_page_navigation_preserves_virtual_undo_history(tmp_path: Path):
    binary_path = tmp_path / "page_undo.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 2048)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    editor = grid.bytes
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(2, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    QApplication.clipboard().setText("FF")
    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier),
    )
    _app().processEvents()
    assert editor.toPlainText().splitlines()[0] == "FF 00 00 00"
    assert editor.document().isUndoAvailable()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageDown, Qt.NoModifier),
    )
    _app().processEvents()
    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageUp, Qt.NoModifier),
    )
    _app().processEvents()
    assert editor.toPlainText().splitlines()[0] == "FF 00 00 00"
    assert editor.document().isUndoAvailable()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
    )
    _app().processEvents()
    assert editor.toPlainText().splitlines()[0] == "00 00 00 00"

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Y, Qt.ControlModifier),
    )
    _app().processEvents()
    assert editor.toPlainText().splitlines()[0] == "FF 00 00 00"


def test_binary_workbench_symbols_rows_use_one_symbol_type():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog(
        {"var": "20"},
        {},
        {},
        symbol_offsets={"var": ["0x00000000", "0x0000000C"]},
    )
    combos = dialog.findChildren(QComboBox, "binary-workbench-dialog-input")
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}

    assert combos == []
    assert BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS in buttons
    variables, _, labels = dialog.values()

    assert variables == {"var": "20"}
    assert labels == {}


def test_binary_workbench_symbols_dialog_cells_are_editable_without_permanent_inputs():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"original": "0x20"}, {}, {})
    name_index = dialog.symbols_model.index(0, dialog.symbols_model.NAME_COLUMN)
    value_index = dialog.symbols_model.index(0, dialog.symbols_model.VALUE_COLUMN)

    assert dialog.table.indexWidget(dialog.symbols_proxy.index(0, 0)) is None
    assert bool(dialog.symbols_model.flags(name_index) & Qt.ItemIsEditable)
    assert bool(dialog.symbols_model.flags(value_index) & Qt.ItemIsEditable)

    assert dialog.symbols_model.setData(name_index, "renamed") is True
    assert dialog.symbols_model.setData(value_index, "0x40") is True

    assert dialog.values() == ({"renamed": "0x40"}, {}, {})
    assert dialog.symbols_model.rowCount() == 1


def test_binary_workbench_clicking_editor_symbol_edits_its_local_definition(
    tmp_path: Path,
    monkeypatch,
):
    from src.presentation.ui.components.binary_workbench.tabs import (
        tab_libraries as tab_libraries_module,
    )

    class Dialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, _title, value, _parent, *, name, editable_value):
            assert value == "0x20"
            assert name == "original"
            assert editable_value is True

        def exec(self):
            return self.DialogCode.Accepted

        def symbol_name(self):
            return "renamed"

        def symbol_value(self):
            return "0x40"

    monkeypatch.setattr(tab_libraries_module, "ImmediateSymbolNameDialog", Dialog)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    tool.tabs.set_current_symbols({"original": "0x20"}, {}, {})
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("addiu $v0, $zero, @original")
    _app().processEvents()
    block = editor.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position() + block.text().index("original") + 2)
    position = editor.cursorRect(cursor).center()

    assert editor._symbol_token_at_position(position) == "@original"
    editor.symbolEditRequested.emit("original")
    _app().processEvents()

    assert tool.tabs.local_symbols() == {"renamed": "0x40"}
    assert "@renamed" in editor.toPlainText()
    assert "@original" not in editor.toPlainText()


def test_binary_workbench_clicking_editor_global_symbol_keeps_global_ownership(
    tmp_path: Path,
    monkeypatch,
):
    from src.presentation.ui.components.binary_workbench.tabs import (
        tab_libraries as tab_libraries_module,
    )

    class Dialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, _title, _value, _parent, *, name, editable_value):
            assert name == "shared"
            assert editable_value is True

        def exec(self):
            return self.DialogCode.Accepted

        def symbol_name(self):
            return "shared_renamed"

        def symbol_value(self):
            return "0x80"

    monkeypatch.setattr(tab_libraries_module, "ImmediateSymbolNameDialog", Dialog)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    tool.tabs.set_global_symbols({"shared": "0x20"})
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.symbolEditRequested.emit("shared")
    _app().processEvents()

    assert tool.tabs.local_symbols() == {}
    assert tool.tabs.global_symbols() == {"shared_renamed": "0x80"}


def test_binary_workbench_symbol_offsets_dialog_lists_offsets():
    _app()
    dialog = BinaryWorkbenchSymbolOffsetsDialog(
        "var",
        ["0x00000000", "0x0000000C"],
    )
    selected: list[int] = []
    dialog.goToRequested.connect(selected.append)
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    labels = [label.text() for label in dialog.findChildren(QLabel) if label.text()]

    assert [dialog.offsets.item(index).text() for index in range(dialog.offsets.count())] == [
        "0x00000000",
        "0x0000000C",
    ]
    assert labels == ["var"]
    assert "OK" not in buttons
    assert dialog.offsets.objectName() == "binary-workbench-symbol-offsets"

    dialog.offsets.itemClicked.emit(dialog.offsets.item(1))

    assert selected == [0xC]
    assert dialog.result() == 0


def test_binary_workbench_symbol_offsets_empty_item_is_not_clickable():
    _app()
    dialog = BinaryWorkbenchSymbolOffsetsDialog("var", [])
    selected: list[int] = []
    dialog.goToRequested.connect(selected.append)
    item = dialog.offsets.item(0)

    dialog.offsets.itemClicked.emit(item)

    assert item.text() == BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_EMPTY
    assert not item.flags() & Qt.ItemIsEnabled
    assert dialog.offsets.cursor().shape() == Qt.ArrowCursor
    assert selected == []


def test_binary_workbench_symbols_inputs_are_aligned_and_symmetric():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"var": "20"}, {}, {"label_1": "0x34"})
    dialog.show()
    _app().processEvents()
    combos = dialog.findChildren(QComboBox, "binary-workbench-dialog-input")
    fields = dialog.findChildren(QLineEdit, "binary-workbench-dialog-input")
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    add_button = buttons[BINARY_WORKBENCH_TEXT.SYMBOL_ADD]
    footer = dialog.findChild(QWidget, "binary-workbench-symbol-footer")
    table = dialog.findChild(QTableView, "binary-workbench-symbols-table")
    shell = dialog.findChild(QWidget, "workspace-table-shell")
    content_widgets = [dialog.name.parentWidget(), table, footer]
    rows = dialog.findChildren(QWidget, "workspace-row")
    symbol_fields = [dialog.name, dialog.value]
    non_empty_labels = [label.text() for label in dialog.findChildren(QLabel) if label.text()]

    assert dialog.filter_input.placeholderText() == BINARY_WORKBENCH_TEXT.FILTER
    assert dialog.filter_input.width() >= BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH
    assert "Library Name" not in {field.placeholderText() for field in fields}
    assert non_empty_labels == []
    assert dialog.minimumWidth() == 880
    assert dialog.width() == 880
    assert shell is not None
    assert {widget.mapTo(dialog, QPoint()).x() for widget in content_widgets if widget is not None} == {
        dialog.name.parentWidget().mapTo(dialog, QPoint()).x()
    }
    assert dialog.name.parentWidget().mapTo(dialog, QPoint()).x() == shell.mapTo(dialog, QPoint()).x() + BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN
    assert {
        widget.layout().contentsMargins().left()
        for widget in content_widgets
        if widget is not None and widget.layout() is not None
    } == {0}
    assert combos == []
    assert {field.width() for field in symbol_fields} == {232}
    assert {field.height() for field in fields} == {
        BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT
    }
    assert add_button.width() == BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH
    assert dialog.value.mapTo(dialog, QPoint()).x() - dialog.name.mapTo(dialog, QPoint()).x() == (
        BINARY_WORKBENCH_LAYOUT.SYMBOL_FIELD_WIDTH + BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN
    )
    assert dialog.remove_button.mapTo(dialog, QPoint()).x() > (
        add_button.mapTo(dialog, QPoint()).x()
        + BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH
    )
    assert table is not None
    assert dialog.findChild(QScrollArea, "workspace-table-body-scroll") is None
    assert rows == []
    assert table.indexWidget(dialog.symbols_proxy.index(0, 0)) is None
    assert table.model().headerData(0, Qt.Horizontal) == BINARY_WORKBENCH_TEXT.SYMBOL_NAME
    assert table.model().headerData(1, Qt.Horizontal) == BINARY_WORKBENCH_TEXT.SYMBOL_VALUE
    assert footer is not None
    assert buttons["Load"].mapTo(dialog, QPoint()).x() == table.mapTo(dialog, QPoint()).x()
    assert footer.layout().count() == 4
    assert len([button for button in dialog.findChildren(QPushButton) if button.text() == BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS]) == 1
    assert len([button for button in dialog.findChildren(QPushButton) if button.text() == BINARY_WORKBENCH_TEXT.SYMBOL_REMOVE]) == 1
    assert BINARY_WORKBENCH_TEXT.OK not in buttons
    assert buttons["Load"].mapTo(dialog, QPoint()).x() < buttons["Save"].mapTo(dialog, QPoint()).x()
    assert buttons["Save"].mapTo(dialog, QPoint()).x() < dialog.offsets_button.mapTo(dialog, QPoint()).x()
    assert dialog.offsets_button.mapTo(dialog, QPoint()).x() < dialog.filter_input.mapTo(dialog, QPoint()).x()
    assert dialog.filter_input.mapTo(dialog, QPoint()).x() + dialog.filter_input.width() == table.mapTo(dialog, QPoint()).x() + table.width()
    assert buttons["Load"].mapTo(dialog, QPoint()).y() == dialog.filter_input.mapTo(dialog, QPoint()).y()
    assert dialog.offsets_button.parentWidget() is footer
    assert dialog.remove_button.parentWidget() is dialog.name.parentWidget()
    assert dialog.offsets_button.isEnabled() is False
    assert dialog.remove_button.isEnabled() is False
    assert all(button.focusPolicy() == Qt.NoFocus for button in dialog.findChildren(QPushButton))

    dialog.resize(dialog.maximumWidth(), dialog.height())
    _app().processEvents()
    assert (
        dialog.remove_button.mapTo(dialog, QPoint()).x()
        + dialog.remove_button.width()
        == table.mapTo(dialog, QPoint()).x() + table.width()
    )


def test_binary_workbench_view_uses_rules_checkbox_presentation():
    _app()
    dialog = BinaryWorkbenchViewDialog(
        [BINARY_WORKBENCH_TEXT.FILE],
        {
            BINARY_WORKBENCH_TEXT.BYTES: True,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: True,
            BINARY_WORKBENCH_TEXT.DECODED_TEXT: False,
            BINARY_WORKBENCH_TEXT.FILE: True,
        },
    )
    checks = dialog.findChildren(QCheckBox, "binary-workbench-dialog-check")

    assert len(checks) == 4
    assert all(check.cursor().shape() == Qt.PointingHandCursor for check in checks)
    assert all(check.height() == BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT for check in checks)


def test_binary_workbench_labels_dialog_filters_and_navigates():
    _app()
    dialog = BinaryWorkbenchLabelsDialog({"loop": "0x00000008", "exit": "0x00000020"})
    selected: list[int] = []
    dialog.goToRequested.connect(selected.append)
    dialog.filter_input.setText("loop")
    dialog.show()
    _app().processEvents()

    assert dialog.labels_proxy.rowCount() == 1
    assert dialog.width() == BINARY_WORKBENCH_LAYOUT.LABELS_DIALOG_WIDTH
    assert dialog.findChildren(QPushButton) == []
    margins = dialog.shell.layout().contentsMargins()
    assert dialog.filter_input.width() == dialog.shell.width() - margins.left() - margins.right()
    filter_right = dialog.filter_input.mapTo(dialog.shell, QPoint()).x() + dialog.filter_input.width()
    assert filter_right == dialog.shell.width() - margins.right()
    assert dialog.findChild(QScrollArea, "workspace-table-body-scroll") is None
    assert dialog.findChildren(QWidget, "workspace-row") == []
    center = dialog.table.visualRect(dialog.labels_proxy.index(0, 0)).center()
    QTest.mouseClick(dialog.table.viewport(), Qt.LeftButton, pos=center)
    QTest.mouseDClick(dialog.table.viewport(), Qt.LeftButton, pos=center)

    assert selected == [0x8]


def test_binary_workbench_labels_action_indexes_lazy_source_without_assembly(
    tmp_path: Path,
    monkeypatch,
):
    source = tmp_path / "labels.asm"
    source.write_text(
        "entry:\naddiu $t0, $zero, 1\nloop: addiu $t1, $zero, 2\nexit:\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window
    assert tool is not None
    tool.open_assembly_path(source)
    page = tool.tabs.currentWidget()
    page.grid._labels = {}
    monkeypatch.setattr(
        page.grid,
        "_instruction_rows_from_lines",
        lambda _lines: pytest.fail("Labels must not assemble the complete source."),
    )
    captured: dict[str, str] = {}

    def capture(dialog):
        for row in range(dialog.labels_model.rowCount()):
            record = dialog.labels_model.record_at(row)
            captured[record.cells[0]] = record.cells[1]
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(BinaryWorkbenchLabelsDialog, "exec", capture)
    tool._open_labels()

    assert captured == {
        "entry": "0x00000000",
        "loop": "0x00000004",
        "exit": "0x00000008",
    }
    assert tool.tabs.current_metadata_context().labels == captured


def test_labels_dialog_navigates_by_label_identity_when_offsets_are_lazy(
    tmp_path: Path,
    monkeypatch,
):
    source = tmp_path / "many_labels.asm"
    instructions = [
        f"ori $t0, $zero, _local_symbol_{index:04d}"
        for index in range(600)
    ]
    source.write_text(
        "entry:\n" + "\n".join(instructions) + "\ntail:\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window
    assert tool is not None
    tool.open_assembly_path(source)
    page = tool.tabs.currentWidget()
    requested: list[str] = []
    monkeypatch.setattr(tool.tabs, "go_to_label", requested.append)

    def choose_tail(dialog):
        matches = [
            row
            for row in range(dialog.labels_model.rowCount())
            if dialog.labels_model.record_at(row).cells[0] == "tail"
        ]
        assert matches
        source_index = dialog.labels_model.index(matches[0], 0)
        dialog.table.setCurrentIndex(dialog.labels_proxy.mapFromSource(source_index))
        dialog._go_to_selected()
        assert dialog.labels_model.record_at(matches[0]).cells[1] == "0x00000960"
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(BinaryWorkbenchLabelsDialog, "exec", choose_tail)
    tool._open_labels()

    assert requested == ["tail"]


def test_binary_workbench_go_to_label_preserves_instruction_symbols(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    page.grid.instructions.setPlainText("loop: ADDIU $S1, $ZERO, _VARIABLE1\nJ loop\nADDIU $S2, $ZERO, @EQUATE1")  # type: ignore[attr-defined]
    _app().processEvents()

    page.go_to_instruction_offset(0)
    text = page.grid.instructions.toPlainText()  # type: ignore[attr-defined]

    assert "loop:" in text
    assert "_VARIABLE1" in text
    assert "@EQUATE1" in text


def test_binary_workbench_go_to_offset_preserves_instruction_symbols(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    page.grid.instructions.setPlainText("LOOP: ADDIU $S1, $ZERO, _VARIABLE1\nJ LOOP\nADDIU $S2, $ZERO, @EQUATE1")  # type: ignore[attr-defined]
    _app().processEvents()

    page.go_to_offset(0)
    text = page.grid.instructions.toPlainText()  # type: ignore[attr-defined]

    assert "LOOP:" in text
    assert "_VARIABLE1" in text
    assert "@EQUATE1" in text


def test_binary_workbench_go_to_after_stale_bytes_focus_preserves_symbols(tmp_path: Path):
    binary_path = tmp_path / "long.bin"
    binary_path.write_bytes(b"\x00\x00\x00\x00" * 200)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    page.grid.instructions.setPlainText("LOOP: ADDIU $S1, $ZERO, _VARIABLE1\nJ LOOP\nADDIU $S2, $ZERO, @EQUATE1")  # type: ignore[attr-defined]
    _app().processEvents()
    page.grid._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES)  # type: ignore[attr-defined]

    page.go_to_offset(0x100)
    page.go_to_instruction_offset(0)
    text = page.grid.instructions.toPlainText()  # type: ignore[attr-defined]
    current = tool.tabs.current_context()

    assert current is not None
    assert current.instruction_overlays["0x00000000"].startswith("LOOP:")
    assert "LOOP:" in text
    assert "_VARIABLE1" in text
    assert "@EQUATE1" in text


def test_binary_workbench_context_menu_uses_white_icons():
    _app()
    menu = QMenu()
    actions = [
        menu.addAction("Undo"),
        menu.addAction(BINARY_WORKBENCH_TEXT.ADD_VARIABLE_FROM_IMMEDIATE),
        menu.addAction(BINARY_WORKBENCH_TEXT.ADD_EQUATE_FROM_IMMEDIATE),
        menu.addAction(BINARY_WORKBENCH_TEXT.OPEN_LABEL_NEW_TAB),
    ]

    use_white_menu_icons(menu)

    for action in actions:
        pixmap = action.icon().pixmap(BINARY_WORKBENCH_LAYOUT.CONTEXT_MENU_ICON_SIZE)
        image = pixmap.toImage()
        white_pixels = [
            image.pixelColor(x, y)
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y).alpha() > 0
        ]
        assert not pixmap.isNull()
        assert all(pixel.red() == 255 and pixel.green() == 255 and pixel.blue() == 255 for pixel in white_pixels)


def test_binary_workbench_internal_file_dialog_uses_standard_minimal_layout():
    _app()
    dialog = BinaryWorkbenchInternalFileDialog([BinaryWorkbenchInternalFileDTO("WA_MRG.MRG", 24)])
    dialog.show()
    _app().processEvents()
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    items = dialog.findChild(QListWidget, "binary-workbench-internal-files")

    assert dialog.windowTitle() == "Internal Files"
    assert dialog.findChildren(QLabel) == []
    assert dialog.layout().getContentsMargins() == BINARY_WORKBENCH_DIALOG_LAYOUT.DIALOG_MARGINS
    assert items is not None
    assert items.item(0).text() == "WA_MRG.MRG"
    assert items.currentItem() is None
    assert items.selectionMode().name == "SingleSelection"
    assert dialog.minimumSize() == dialog.maximumSize()
    assert items.height() == (
        BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.ITEM_HEIGHT
        + BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.LIST_FRAME_WIDTH
    )
    items.setCurrentRow(0)
    assert dialog.selected_name() == "WA_MRG.MRG"
    assert set(buttons) == {"Cancel", "OK"}
    assert buttons["Cancel"].mapTo(dialog, QPoint()).x() < buttons["OK"].mapTo(dialog, QPoint()).x()


def test_binary_workbench_lba_filesystem_uses_editable_rows():
    _app()
    dialog = BinaryWorkbenchLbaFilesystemDialog([BinaryWorkbenchInternalFileDTO("SLUS", 24)])
    selected: list[int] = []
    dialog.goToRequested.connect(selected.append)
    dialog.show()
    _app().processEvents()
    fields = dialog.findChildren(QLineEdit, "binary-workbench-dialog-input")
    combos = dialog.findChildren(QComboBox, "binary-workbench-dialog-input")
    table = dialog.findChild(QTableView, "binary-workbench-environment-table")
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    labels = [label.text() for label in dialog.findChildren(QLabel)]
    text_buttons = [button for button in dialog.findChildren(QPushButton) if button.text()]

    assert len(fields) == 2
    assert dialog.minimumWidth() == BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MIN_WIDTH
    assert dialog.minimumHeight() == BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MIN_HEIGHT
    assert dialog.width() == BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_WIDTH
    assert dialog.height() == BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_HEIGHT
    assert table is not None
    assert dialog.findChild(QScrollArea, "workspace-table-body-scroll") is None
    assert dialog.findChildren(QWidget, "workspace-row") == []
    assert labels == ["LBA Sector"]
    assert "Library Name" not in {field.placeholderText() for field in fields}
    assert {combo.width() for combo in combos} == {BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH}
    assert {field.height() for field in fields} == {BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT}
    assert {button.width() for button in text_buttons} == {BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH}
    assert buttons["Load"].mapTo(dialog, QPoint()).y() == buttons["Save"].mapTo(dialog, QPoint()).y()
    assert BINARY_WORKBENCH_TEXT.OK not in buttons
    assert table.model().rowCount() == 1
    assert table.indexWidget(table.model().index(0, 0)) is None
    table.selectRow(0)
    buttons["Go to"].click()
    dialog.lba_model.setData(dialog.lba_model.index(0, 0), "WA_MRG.MRG")
    dialog.lba_model.setData(dialog.lba_model.index(0, 1), "10010")
    _app().clipboard().setText("SYSTEM.CNF")
    dialog.name.setFocus()
    QApplication.sendEvent(dialog.name, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))
    assert dialog.name.text() == "SYSTEM.CNF"
    dialog.name.selectAll()
    QApplication.sendEvent(dialog.name, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_C, Qt.ControlModifier))
    assert _app().clipboard().text() == "SYSTEM.CNF"
    QApplication.sendEvent(dialog.name, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    assert dialog.name.text() == ""
    mappings = dialog.mappings()

    dialog.name.setText("SYSTEM.CNF")
    assert dialog.name.hasAcceptableInput() is True
    assert dialog.name.contextMenuPolicy() == Qt.CustomContextMenu
    assert selected == [24 * 2352]
    assert mappings[0].name == "WA_MRG.MRG"
    assert mappings[0].start_lba == 10010


def test_binary_workbench_advanced_configuration_uses_confirm_and_block_size_options():
    _app()
    dialog = BinaryWorkbenchAdvancedConfigDialog(
        "PSX - Mips R3000A",
        BINARY_WORKBENCH_TEXT.AUTO_READ_MODE,
        2048,
        8000,
        2 * 1024 * 1024,
    )
    dialog.show()
    _app().processEvents()
    combos = dialog.findChildren(QComboBox, "advanced-config-dropdown")
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    labels = dialog.findChildren(QLabel)

    assert dialog.findChild(QLabel, "preferences-title") is None
    assert dialog.findChild(QLabel, "preferences-subtitle") is None
    assert [label.text() for label in labels] == [
        "CPU Arch",
        "Read Mode",
        "Block Size",
        "Cache Max Blocks",
        "Selection Limit",
    ]
    assert [combos[2].itemText(index) for index in range(combos[2].count())] == [
        "256",
        "512",
        "1024",
        "2048",
        "4096",
    ]
    assert [combos[3].itemText(index) for index in range(combos[3].count())] == [
        "1000",
        "2000",
        "4000",
        "8000",
        "16000",
    ]
    assert [combos[4].itemText(index) for index in range(combos[4].count())] == [
        "1MB",
        "2MB",
        "4MB",
        "6MB",
        "8MB",
        "12MB",
        "16MB",
        "24MB",
        "32MB",
        "48MB",
        "64MB",
        "80MB",
        "128MB",
    ]
    assert dialog.selected_block_size() == 2048
    assert dialog.selected_cache_max_blocks() == 8000
    assert dialog.selected_selection_limit_bytes() == 2 * 1024 * 1024
    assert "Confirm" in buttons
    assert "OK" not in buttons
    assert {combo.width() for combo in combos} == {260}
    assert buttons["Confirm"].width() == 130
    assert buttons["Confirm"].mapTo(dialog, QPoint()).x() == 95
    geometries = [combo.geometry() for combo in combos]
    for combo, geometry in zip(combos, geometries):
        combo.showPopup()
        _app().processEvents()
        combo.hidePopup()
        assert combo.geometry() == geometry


def test_binary_workbench_advanced_configuration_preserves_in_memory_code(tmp_path: Path):
    binary_path = tmp_path / "advanced_config.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 64)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    lines = editor.toPlainText().splitlines()
    lines[0] = "addiu $v0, $zero, 1 ; keep edit"
    editor.setPlainText("\n".join(lines))
    _app().processEvents()
    page.grid.flush_pending_rows_changed()  # type: ignore[attr-defined]
    before = page.current_context()

    tool.tabs.set_current_advanced_config(
        before.cpu_arch,
        before.read_mode,
        256,
        1000,
        tool.tabs.preferences().selection_limit_bytes,
    )
    _app().processEvents()
    after = tool.tabs.current_context()

    assert after.byte_overlays == before.byte_overlays
    assert after.instruction_overlays == before.instruction_overlays
    assert after.file_size == before.file_size
    assert "keep edit" in tool.tabs.currentWidget().grid.instructions.toPlainText()  # type: ignore[attr-defined]


def test_binary_workbench_advanced_configuration_keeps_empty_offsets_aligned(tmp_path: Path):
    assembly_path = tmp_path / "offset_alignment.asm"
    assembly_path.write_text("nop\n; comment\ninvalid\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    before = tool.tabs.current_context()
    tool.tabs.set_current_advanced_config(
        before.cpu_arch,
        before.read_mode,
        256,
        1000,
        tool.tabs.preferences().selection_limit_bytes,
    )
    _app().processEvents()
    page = tool.tabs.currentWidget()
    offsets = page.grid._offset_editors[BINARY_WORKBENCH_TEXT.FILE]  # type: ignore[attr-defined]

    assert offsets.toPlainText().splitlines() == [
        "0x00000000",
        "-",
        "-",
        "0x00000004",
    ]


def test_binary_workbench_lba_filesystem_dialog_loads_json_library(tmp_path: Path):
    _app()
    library_path = tmp_path / "disc-map.json"
    library_path.write_text(
        '{"name":"disc-map","sector_size":2048,"internal_files":[{"name":"SLUS","start_lba":24}]}',
        encoding="utf-8",
    )
    dialog = BinaryWorkbenchLbaFilesystemDialog([])

    assert dialog.load_library_json(library_path) is True

    assert dialog.selected_lba_sector_size() == 2048
    assert dialog.loaded_library_name() == "disc-map"
    assert dialog.mappings() == [BinaryWorkbenchInternalFileDTO("SLUS", 24)]


def test_binary_workbench_lba_filesystem_dialog_saves_json_library(tmp_path: Path):
    _app()
    library_path = tmp_path / "disc-map.json"
    dialog = BinaryWorkbenchLbaFilesystemDialog(
        [BinaryWorkbenchInternalFileDTO("SLUS", 24)],
        2048,
        default_library_name="disc-map",
    )

    assert dialog.save_library_json(library_path) is True

    assert dialog.result() == 0
    assert dialog.should_save_library() is True
    assert dialog.saved_library_name() == "disc-map"
    assert '"sector_size": 2048' in library_path.read_text(encoding="utf-8")
    assert '"start_lba": 24' in library_path.read_text(encoding="utf-8")


def test_binary_workbench_lba_filesystem_does_not_match_different_directory(tmp_path: Path):
    first = tmp_path / "one" / "disc.bin"
    second = tmp_path / "two" / "disc.bin"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(bytes(4096))
    second.write_bytes(bytes(4096))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(first)
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO("slus", 24)], 2048)
    tool.tabs.save_current_lba_filesystem("shared-disc")
    tool.open_binary_path(second)
    current = tool.tabs.current_context()

    assert current is not None
    assert current.lba_sector_size == 2352
    assert current.internal_files == []


def test_binary_workbench_symbols_resolve_labels_and_multiple_offsets(tmp_path: Path):
    assembly_path = tmp_path / "symbols.asm"
    assembly_path.write_text(
        "label1: addiu $v1, $v0, _variable1\n"
        "addiu $v1, $v0, @equate1\n"
        "j label1\n"
        "addiu $v1, $v0, _variable1\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(assembly_path)
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {"label1": "0x00000000"})
    current = tool.tabs.current_context()

    assert current is not None
    assert current.symbol_offsets["label1"] == ["0x00000000"]
    assert tool.tabs.symbol_offsets_for(current.tab_id, "variable1") == [
        "0x00000000",
        "0x0000000C",
    ]
    assert tool.tabs.symbol_offsets_for(current.tab_id, "equate1") == [
        "0x00000004"
    ]
    dialog = BinaryWorkbenchGoToDialog(
        current,
        symbol_offsets_provider=lambda name: tool.tabs.symbol_offsets_for(
            current.tab_id,
            name,
        ),
    )
    dialog.target.setCurrentText(BINARY_WORKBENCH_TEXT.SYMBOL_TARGET)
    dialog.value.setText("variable1")
    dialog.refresh_results()

    assert dialog.results.count() == 2
    assert dialog.selected_offsets() == [0, 12]


def test_binary_workbench_symbols_dialog_loads_json_library(tmp_path: Path):
    _app()
    library_path = tmp_path / "shared-symbols.json"
    library_path.write_text(
        (
            '{"name":"shared-symbols","variables":{"variable1":"20"},'
            '"equates":{"equate1":"0x34"},"labels":{"label1":"0x00000000"}}'
        ),
        encoding="utf-8",
    )
    dialog = BinaryWorkbenchSymbolsDialog(
        {"keep": "0x1", "variable1": "old"},
        {},
        {},
    )

    assert dialog.load_library_json(library_path) is True

    assert dialog.values() == (
        {"keep": "0x1", "variable1": "20", "equate1": "0x34"},
        {},
        {},
    )
    assert dialog.loaded_library_name() == "shared-symbols"


def test_binary_workbench_symbols_dialog_saves_json_library(tmp_path: Path):
    _app()
    library_path = tmp_path / "shared-symbols.json"
    dialog = BinaryWorkbenchSymbolsDialog(
        {"variable1": "20"},
        {"equate1": "0x34"},
        {"label1": "0x00000000"},
        default_library_name="shared-symbols",
    )

    assert dialog.save_library_json(library_path) is True

    payload = library_path.read_text(encoding="utf-8")
    assert dialog.result() == 0
    assert dialog.should_save_library() is True
    assert dialog.saved_library_name() == "shared-symbols"
    assert '"variable1": "20"' in payload
    assert '"equate1": "0x34"' in payload
    assert '"symbols"' in payload
    assert '"variables"' not in payload
    assert '"equates"' not in payload
    assert '"label1": "0x00000000"' not in payload


def test_binary_workbench_symbol_completion_starts_from_prefix_markers():
    _app()
    editor = WorkbenchEditor()
    editor.set_symbol_helpers({"label1": "0x0"}, {"variable1": "20"}, {"equate1": "0x34"})
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Underscore, Qt.NoModifier, "_"))

    assert editor._current_completion_prefix() == "_"
    assert editor._completion_model.stringList() == []
    assert editor._symbol_completion_timer.isActive() is True
    assert editor._symbol_completion_timer.interval() == 400
    editor._symbol_completion_timer.stop()
    editor._refresh_completions()
    assert editor._completion_model.stringList() == ["_variable1"]
    assert editor._candidates_for_prefix("_") == ["_variable1"]
    assert editor._candidates_for_prefix("_VAR") == ["_variable1"]
    assert editor._candidates_for_prefix("_variable1") == []
    assert editor._candidates_for_prefix("@") == ["@equate1"]
    assert editor._candidates_for_prefix("@EQU") == ["@equate1"]
    assert editor._candidates_for_prefix("@equate1") == []


def test_binary_workbench_editor_undo_restores_backspace_one_key_at_a_time():
    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("WORD 0x3078302C")
    cursor = editor.textCursor()
    cursor.setPosition(len(editor.toPlainText()))
    editor.setTextCursor(cursor)

    for _ in range(3):
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))

    assert editor.toPlainText() == "WORD 0x30783"

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    assert editor.toPlainText() == "WORD 0x307830"

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    assert editor.toPlainText() == "WORD 0x3078302"


def test_binary_workbench_instruction_casing_normalization_preserves_cursor_and_undo():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.set_uppercase_instruction_hover(True)

    for key, text in ((Qt.Key_N, "N"), (Qt.Key_O, "O"), (Qt.Key_P, "P")):
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text))

    assert editor.toPlainText() == "nop"
    assert editor.textCursor().position() == len("nop")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))

    assert editor.toPlainText() == "NO"
    assert editor.textCursor().position() == len("NO")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    assert editor.toPlainText() == "N"


def test_binary_workbench_assembly_alt_enter_inserts_nop_as_one_undo_step(tmp_path: Path):
    assembly_path = tmp_path / "alt_enter.asm"
    assembly_path.write_text("addiu $v0, $zero, 1", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.EndOfBlock)
    editor.setTextCursor(cursor)
    original = editor.toPlainText()
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier, " "))
    before_alt_enter = editor.toPlainText()

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.AltModifier))

    assert editor.toPlainText() == f"{before_alt_enter}\nnop\n"
    assert editor.textCursor().blockNumber() == 2
    assert editor.textCursor().positionInBlock() == 0

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    assert editor.toPlainText() == before_alt_enter

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier))
    assert editor.toPlainText() == original


def test_binary_workbench_editor_ctrl_q_keeps_previous_ctrl_d_selections():
    _app()
    editor = WorkbenchEditor()
    editor.setPlainText("ADDIU $zero\nNOP\nADDIU $zero\nNOP\nADDIU $zero\nNOP\nADDIU $zero")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(5, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)

    for _ in range(2):
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_D, Qt.ControlModifier))

    assert len(editor.extraSelections()) == 3

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Q, Qt.ControlModifier))

    assert len(editor.extraSelections()) == 3
    assert editor._occurrence_ranges[0] == (0, 5)
    assert editor._occurrence_ranges[1] == (16, 21)
    assert editor._occurrence_ranges[2] == (48, 53)


def test_binary_workbench_ctrl_d_replaces_selected_occurrences():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("NOP\nADD\nNOP")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(3, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_D, Qt.ControlModifier))
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_X, Qt.NoModifier, "X"))

    assert editor.toPlainText().splitlines() == ["X", "ADD", "X"]
    assert len(editor.multicursor_positions()) == 2
    assert all(start == end for start, end in editor._occurrence_ranges)


def test_binary_workbench_multiple_selected_occurrences_delete_without_removing_lines():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("WORD 0x582D0112\nWORD 0x33333333")
    first_end = len("WORD 0x582D0112")
    second_start = first_end + 1
    second_end = second_start + len("WORD 0x33333333")
    editor._occurrence_ranges = [(0, first_end), (second_start, second_end)]
    editor._apply_occurrence_selection((second_start, second_end))

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))

    assert editor.toPlainText().split("\n") == ["", ""]


def test_binary_workbench_instruction_paste_replaces_selection_and_inserts_at_cursor():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("WORD 0x582D0112\nWORD 0x33333333")
    first_end = len("WORD 0x582D0112")
    second_start = first_end + 1
    editor._occurrence_ranges = [(0, first_end), (second_start, second_start)]
    editor._apply_occurrence_selection((second_start, second_start))
    app.clipboard().setText("WORD 0xAAAAAAAA")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText().splitlines() == [
        "WORD 0xAAAAAAAA",
        "WORD 0xAAAAAAAAWORD 0x33333333",
    ]
    assert editor.multicursor_positions() == [
        len("WORD 0xAAAAAAAA"),
        len("WORD 0xAAAAAAAA\nWORD 0xAAAAAAAA"),
    ]


def test_binary_workbench_bytes_paste_replaces_multiple_selected_ranges():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.setPlainText("AA BB\n11 22")
    editor._occurrence_ranges = [(0, 2), (6, 8)]
    editor._apply_occurrence_selection((6, 8))
    app.clipboard().setText("FF")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText().splitlines() == ["FF BB", "FF 22"]


def test_binary_workbench_instruction_alt_click_edits_multiple_lines():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.resize(320, 120)
    editor.show()
    editor.setPlainText("NOP\nNOP\nNOP")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    _alt_click_editor_line(editor, 1, 0)
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_A, Qt.NoModifier, "A"))
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_D, Qt.NoModifier, "D"))
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_D, Qt.NoModifier, "D"))

    assert editor.toPlainText().splitlines() == ["ADDNOP", "ADDNOP", "NOP"]
    assert len(editor.multicursor_positions()) == 2


def test_binary_workbench_bytes_alt_click_edits_multiple_lines():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.resize(320, 120)
    editor.show()
    editor.setPlainText("AA BB\n11 22")
    cursor = editor.textCursor()
    cursor.setPosition(2)
    editor.setTextCursor(cursor)

    _alt_click_editor_line(editor, 1, 2)
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_F, Qt.NoModifier, "F"))

    assert editor.toPlainText().splitlines() == ["AAF BB", "11F 22"]
    assert len(editor.multicursor_positions()) == 2


def test_binary_workbench_bytes_rejects_non_hex_and_ninth_character():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.setPlainText("AA BB CC DD")
    cursor = editor.textCursor()
    cursor.setPosition(len(editor.toPlainText()))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_G, Qt.NoModifier, "G"))
    assert editor.toPlainText() == "AA BB CC DD"

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_F, Qt.NoModifier, "F"))
    assert editor.toPlainText() == "AA BB CC DD"


def test_binary_workbench_bytes_pastes_spaced_four_byte_row():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.setPlainText("00 00 00 00")
    cursor = editor.textCursor()
    cursor.select(QTextCursor.Document)
    editor.setTextCursor(cursor)
    app.clipboard().setText("AA BB CC DD")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText() == "AA BB CC DD"


def test_binary_workbench_bytes_pastes_eight_bytes_over_two_locked_rows():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.setPlainText("00 00 00 00\n11 11 11 11")
    cursor = editor.textCursor()
    cursor.select(QTextCursor.Document)
    editor.setTextCursor(cursor)
    app.clipboard().setText("AA BB CC DD\n22 33 44 55")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText() == "AA BB CC DD\n22 33 44 55"


def test_binary_workbench_bytes_locked_paste_removes_clipboard_line_breaks():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.setPlainText("00 00 00 00")
    cursor = editor.textCursor()
    cursor.select(QTextCursor.Document)
    editor.setTextCursor(cursor)
    app.clipboard().setText("AA BB\nCC DD")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText() == "AA BB CC DD"


def test_binary_workbench_bytes_shift_paste_keeps_offsets_with_line_limit():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.set_bytes_line_shift_allowed(True)
    editor.setPlainText("")
    app.clipboard().setText("AA BB CC DD 22 33 44 55")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText() == "AA BB CC DD\n22 33 44 55"


def test_binary_workbench_bytes_multicursor_rejects_full_lines():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.resize(320, 120)
    editor.show()
    editor.setPlainText("AA BB CC DD\n11 22 33 44")
    cursor = editor.textCursor()
    cursor.setPosition(len("AA BB CC DD"))
    editor.setTextCursor(cursor)

    _alt_click_editor_line(editor, 1, len("11 22 33 44"))
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_F, Qt.NoModifier, "F"))

    assert editor.toPlainText().splitlines() == ["AA BB CC DD", "11 22 33 44"]
    assert len(editor.multicursor_positions()) == 2


def test_binary_workbench_bytes_backspace_does_not_join_lines():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.setPlainText("AA\nBB")
    cursor = editor.textCursor()
    cursor.setPosition(len("AA\n"))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))

    assert editor.toPlainText() == "AA\nBB"


def test_binary_workbench_bytes_backspace_joins_lines_when_shift_allowed():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-bytes-panel")
    editor.set_bytes_line_shift_allowed(True)
    editor.setPlainText("AA\nBB")
    cursor = editor.textCursor()
    cursor.setPosition(len("AA\n"))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))

    assert editor.toPlainText() == "AABB"


def test_binary_workbench_multicursors_clear_on_escape_and_plain_click():
    _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.resize(320, 120)
    editor.show()
    editor.setPlainText("NOP\nNOP\nNOP")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    _alt_click_editor_line(editor, 1, 0)
    assert editor.has_multicursor_ranges() is True

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert editor.has_multicursor_ranges() is False

    _alt_click_editor_line(editor, 1, 0)
    assert editor.has_multicursor_ranges() is True

    _mouse_press_editor_line(editor, 2, 0, Qt.NoModifier)
    assert editor.has_multicursor_ranges() is False


def test_binary_workbench_large_binary_alt_click_backspace_keeps_lines(tmp_path: Path):
    binary_path = tmp_path / "large.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 80)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    original_lines = editor.toPlainText().splitlines()
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    _alt_click_editor_line(editor, 1, 0)
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == original_lines
    assert len(page.grid.export_rows()) == len(original_lines)  # type: ignore[attr-defined]


def _alt_click_editor_line(editor: WorkbenchEditor, line: int, column: int) -> None:
    _mouse_press_editor_line(editor, line, column, Qt.AltModifier)


def _mouse_press_editor_line(
    editor: WorkbenchEditor,
    line: int,
    column: int,
    modifiers: Qt.KeyboardModifier,
) -> None:
    block = editor.document().findBlockByNumber(line)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(block.position() + column)
    point = editor.cursorRect(cursor).center()
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(point),
        Qt.LeftButton,
        Qt.LeftButton,
        modifiers,
    )
    editor.mousePressEvent(event)


def test_binary_workbench_symbol_completion_popup_selects_first_match():
    app = _app()
    editor = WorkbenchEditor()
    editor.resize(320, 120)
    editor.show()
    editor.set_symbol_helpers({}, {"variable1": "20"}, {"equate1": "0x34"})

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Underscore, Qt.NoModifier, "_"))
    app.processEvents()

    assert editor._completer.popup().isVisible() is False
    assert editor._symbol_completion_timer.isActive() is True
    assert editor._symbol_completion_timer.interval() == (
        BINARY_WORKBENCH_TIMING.EDITOR_SYMBOL_COMPLETION_INSERT_DEBOUNCE_MS
    )
    editor._symbol_completion_timer.stop()
    editor._refresh_completions()
    popup = editor._completer.popup()
    assert popup.currentIndex().data() == "_variable1"
    assert popup.width() >= BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_MIN_WIDTH


def test_binary_workbench_symbol_completion_debounces_delete_and_bounds_large_catalog():
    _app()
    editor = WorkbenchEditor()
    variables = {f"global_symbol_{index:05d}": hex(index) for index in range(10_000)}
    variable_map = {
        f"_{name}".casefold(): value
        for name, value in variables.items()
    }
    editor.set_symbol_helpers({}, variables, {}, ({}, variable_map, {}))
    editor.setPlainText("_global_symbol_09999")
    cursor = editor.textCursor()
    cursor.setPosition(len(editor.toPlainText()))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier),
    )

    assert editor._symbol_completion_timer.isActive() is True
    assert editor._symbol_completion_timer.interval() == (
        BINARY_WORKBENCH_TIMING.EDITOR_SYMBOL_COMPLETION_DELETE_DEBOUNCE_MS
    )
    assert editor._completion_items["variable"] == []
    editor._symbol_completion_timer.stop()
    editor.setPlainText("_global_symbol_")
    cursor = editor.textCursor()
    cursor.setPosition(len(editor.toPlainText()))
    editor.setTextCursor(cursor)
    editor._refresh_completions()

    assert editor._completion_items["variable"] == []
    assert editor._completion_model.rowCount() == (
        BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_MAX_CANDIDATES
    )


def test_binary_workbench_arrow_navigation_hides_and_debounces_completion_popup():
    app = _app()
    editor = WorkbenchEditor()
    editor.resize(320, 120)
    editor.show()
    editor.set_symbol_helpers({"target": "0x0"}, {}, {})
    editor.setPlainText("tar\nnop")
    cursor = editor.textCursor()
    cursor.setPosition(3)
    editor.setTextCursor(cursor)
    editor._refresh_completions()
    editor._completer.popup().show()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Down, Qt.NoModifier),
    )
    app.processEvents()

    assert editor.textCursor().blockNumber() == 1
    assert editor._completer.popup().isVisible() is False
    assert editor._completion_navigation_timer.isActive() is True
    assert editor._completion_navigation_timer.interval() == 1500


@pytest.mark.parametrize("key", [Qt.Key_Left, Qt.Key_Right])
def test_binary_workbench_horizontal_navigation_debounces_completion_popup(key):
    app = _app()
    editor = WorkbenchEditor()
    editor.resize(320, 120)
    editor.show()
    editor.set_symbol_helpers({"target": "0x0"}, {}, {})
    editor.setPlainText("tar")
    cursor = editor.textCursor()
    cursor.setPosition(2)
    editor.setTextCursor(cursor)
    editor._refresh_completions()
    editor._completer.popup().show()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier),
    )
    app.processEvents()

    assert editor._completer.popup().isVisible() is False
    assert editor._completion_navigation_timer.isActive() is True
    assert editor._completion_navigation_timer.interval() == 1500


def test_binary_workbench_symbol_completion_accepts_current_symbol():
    _app()
    editor = WorkbenchEditor()
    editor.set_symbol_helpers({}, {"variable1": "20"}, {})
    editor.setPlainText("_VAR")
    cursor = editor.textCursor()
    cursor.setPosition(4)
    editor.setTextCursor(cursor)
    editor._refresh_completions()
    editor._completer.popup().show()

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Tab, Qt.NoModifier))

    assert editor.toPlainText() == "_variable1"


def test_binary_workbench_symbol_completion_enter_keeps_cursor_line():
    _app()
    editor = WorkbenchEditor()
    editor.set_symbol_helpers({}, {"variable1": "20"}, {})
    editor.setPlainText("NOP\nADDIU $S1, $S1, _\nNOP\nNOP")
    cursor = editor.textCursor()
    cursor.setPosition(len("NOP\nADDIU $S1, $S1, _"))
    editor.setTextCursor(cursor)
    editor._refresh_completions()
    moved = editor.textCursor()
    moved.setPosition(len(editor.toPlainText()))
    editor.setTextCursor(moved)
    editor._completer.popup().show()

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier))

    assert editor.toPlainText().splitlines()[1] == "ADDIU $S1, $S1, _variable1"
    assert editor.textCursor().blockNumber() == 1


def test_binary_workbench_grid_completion_enter_keeps_instruction_line(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    tool.tabs.set_current_symbols({"variable1": "20"}, {}, {})
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("NOP\nADDIU $S1, $S1, _\nNOP\nNOP")
    cursor = editor.textCursor()
    cursor.setPosition(len("NOP\nADDIU $S1, $S1, _"))
    editor.setTextCursor(cursor)
    editor._refresh_completions()

    QApplication.sendEvent(editor._completer.popup(), QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier))
    _app().processEvents()

    assert editor.textCursor().blockNumber() == 1
    assert "ADDIU $S1, $S1, _variable1" in editor.toPlainText()




def test_binary_workbench_highlighter_register_aliases_share_colors():
    assert psx_mips_highlight_color("registers", "$s1") == psx_mips_highlight_color("registers", "r17")
    assert psx_mips_highlight_color("registers", "$zero") == psx_mips_highlight_color("registers", "$0")
    assert psx_mips_highlight_color("registers", "0") is None
    assert psx_mips_highlight_color("registers", "$fp") == psx_mips_highlight_color("registers", "$s8")


def test_instruction_edit_below_directives_does_not_schedule_global_rehighlight():
    _app()
    editor = WorkbenchEditor()
    editor.setPlainText(
        "* virtual_memory_range 0x80000000 0x801FFFFF\n"
        "* define $sp 0x801FFFF0\n"
        "nop\n"
        "nop"
    )
    highlighter = InstructionHighlighter(editor.document())
    highlighter.rehighlight()
    highlighter._directive_refresh_timer.stop()
    cursor = QTextCursor(editor.document().lastBlock())
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    cursor.insertBlock()

    assert highlighter._directive_refresh_timer.isActive() is False

def test_binary_workbench_highlighter_groups_use_distinct_colors():
    shared_symbol_color = PSX_MIPS_HIGHLIGHTER["equate"]
    distinct_colors = [
        psx_mips_highlight_color("mnemonic", "beq"),
        psx_mips_highlight_color("mnemonic", "lw"),
        psx_mips_highlight_color("mnemonic", "mfhi"),
        psx_mips_highlight_color("mnemonic", "addiu"),
        psx_mips_highlight_color("registers", "s0"),
        psx_mips_highlight_color("registers", "a0"),
        psx_mips_highlight_color("registers", "sp"),
        psx_mips_highlight_color("registers", "ra"),
    ]

    assert PSX_MIPS_HIGHLIGHTER["label"] == "#FF69B4"
    assert PSX_MIPS_HIGHLIGHTER["variable"] == shared_symbol_color
    assert shared_symbol_color == "#1E90FF"
    assert shared_symbol_color not in distinct_colors
    assert len(distinct_colors) == len(set(distinct_colors))


def test_binary_workbench_highlighter_colors_supported_pseudo_instructions():
    other_color = psx_mips_highlight_color("mnemonic", "addiu")
    branch_color = psx_mips_highlight_color("mnemonic", "beq")

    for mnemonic in ("li", "move", "clear", "neg", "negu"):
        assert psx_mips_highlight_color("mnemonic", mnemonic) == other_color
        assert invalid_instruction(f"{mnemonic} $a0, $s1") is False
    assert psx_mips_highlight_color("mnemonic", "b") == branch_color
    assert invalid_instruction("b loop") is False


def test_binary_workbench_highlighter_requires_branch_target_inside_current_file():
    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    highlighter.set_jump_reference_offsets({}, "", 8)

    highlighter.set_symbols({"target": "0x00000004"}, {}, {})
    assert highlighter._invalid_jump_target_range("beq $zero, $zero, target") is None

    highlighter.set_symbols({}, {}, {})
    assert highlighter._invalid_jump_target_range("beq $zero, $zero, 0x00000008") is not None

    highlighter.set_symbols({"target": "0x00000002"}, {}, {})
    assert highlighter._invalid_jump_target_range("beq $zero, $zero, target") is not None


@pytest.mark.parametrize(
    "instruction",
    (
        "beq $a1, $zero, target",
        "bne $a1, $zero, target",
        "bltz $a1, target",
        "bgez $a1, target",
    ),
)
def test_binary_workbench_highlighter_trusts_current_source_labels(
    instruction: str,
):
    """A current source label must not be rejected by a stale visual size."""

    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    highlighter.set_jump_reference_offsets({}, "", 4)
    highlighter.set_symbols({"target": "0x00000040"}, {}, {})

    assert highlighter._invalid_jump_target_range(instruction) is None


def test_binary_workbench_opening_recovers_missing_label_index_for_viewport():
    """A persisted Assembly must not briefly mark valid branch labels red."""

    _app()
    rows = [
        BinaryWorkbenchRowDTO(
            offsets={BINARY_WORKBENCH_TEXT.FILE: "0x00000000"},
            instruction="BEQ $a1, $zero, target",
            bytes_text="01 00 A0 10",
        ),
        BinaryWorkbenchRowDTO(
            offsets={BINARY_WORKBENCH_TEXT.FILE: "-"},
            instruction="target:",
            bytes_text="",
        ),
        BinaryWorkbenchRowDTO(
            offsets={BINARY_WORKBENCH_TEXT.FILE: "0x00000004"},
            instruction="NOP",
            bytes_text="00 00 00 00",
        ),
    ]
    page = BinaryWorkbenchEditorPage(
        BinaryWorkbenchTabContextDTO(
            tab_id="missing-label-cache",
            kind=BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
            display_name="labels.asm",
            rows=rows,
            labels={},
        )
    )

    assert page.current_context().labels == {"target": "0x00000004"}
    assert (
        page.grid._instruction_highlighter._invalid_jump_target_range(
            "BEQ $a1, $zero, target"
        )
        is None
    )


def test_binary_workbench_highlighter_marks_misaligned_load_store_addresses():
    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    highlighter.set_symbols({}, {"word_address": "0x2($zero)"}, {})

    for instruction in (
        "lw $t0, 0x2($zero)",
        "sw $t0, _word_address",
        "lh $t0, 0x1($zero)",
        "lhu $t0, -0x3($zero)",
        "sh $t0, 3($zero)",
    ):
        assert highlighter._invalid_memory_alignment_range(instruction) is not None

    for instruction in (
        "lw $t0, 0x4($zero)",
        "sw $t0, 0($zero)",
        "lh $t0, 0x2($zero)",
        "lbu $t0, 0x1($zero)",
        "lwl $t0, 0x1($zero)",
        "lw $t0, 0x2($sp)",
    ):
        assert highlighter._invalid_memory_alignment_range(instruction) is None


def test_binary_workbench_highlighter_uses_effective_register_address_for_loads():
    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    editor.setPlainText(
        "LUI t1, 0x801A\n"
        "ORI t1, t1, 0xB363\n"
        "LHU t2, 0x0(t1)"
    )
    highlighter.rehighlight()

    register_values = highlighter._known_register_values_by_block[1]
    assert register_values[9] == 0x801AB363
    assert highlighter._invalid_memory_alignment_range(
        "LHU t2, 0x0(t1)",
        register_values,
    ) == (8, 15)


def test_binary_workbench_offset_placeholders_are_centered_in_every_offset_column():
    from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
    from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid
    from src.presentation.ui.components.binary_workbench.editor.grid_offsets import OffsetWorkbenchEditor

    _app()
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
    grid.load_rows(
        [
            BINARY_WORKBENCH_TEXT.FILE,
            "RAM",
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        [
            BinaryWorkbenchRowDTO(
                offsets={BINARY_WORKBENCH_TEXT.FILE: "-", "RAM": "-"},
                instruction="; comment",
                bytes_text="",
            ),
            BinaryWorkbenchRowDTO(
                offsets={BINARY_WORKBENCH_TEXT.FILE: "0x00000000", "RAM": "0x80000000"},
                instruction="nop",
                bytes_text="00 00 00 00",
            ),
        ],
    )
    grid.resize(600, 300)
    grid.show()
    _app().processEvents()

    for editor in grid._offset_editors.values():
        assert isinstance(editor, OffsetWorkbenchEditor)
        placeholder = editor.document().findBlockByNumber(0)
        assert placeholder.text() == "-"
        assert abs(editor.centered_dash_x() - editor.viewport().width() // 2) <= editor.fontMetrics().horizontalAdvance("-")
        source_x = editor.cursorRect(QTextCursor(placeholder)).x()
        assert source_x < editor.centered_dash_x()
        assert editor._dash_blocks == {0}

def test_binary_workbench_jump_highlighter_separates_labels_symbols_and_addresses():
    _app()
    editor = QPlainTextEdit()
    highlighter = InstructionHighlighter(editor.document())
    highlighter.set_symbols(
        {"label_teste": "0x1D9200"},
        {"jump_symbol": "0x1D9200"},
        {"jump_symbol": "0x1D9200"},
    )
    highlighter.set_jump_reference_offsets(
        {"RAM": "0x80000000"},
        "RAM",
        8,
    )

    assert highlighter._target_file_offset("j", "label_teste") == 0x1D9200
    assert highlighter._target_file_offset("j", "0x1D9200") == 0x1C9A00
    assert highlighter._target_file_offset("jal", "@jump_symbol") == 0x1C9A00
    assert highlighter._target_file_offset("j", "&0x801D9200") == 0x1D9200
    for instruction in (
        "j label_teste",
        "j 0x1D9200",
        "jal 0x1D9200",
        "jal @jump_symbol",
        "j &0x801D9200",
        "jal &0x801D9200",
    ):
        assert highlighter._invalid_jump_target_range(instruction) is None


def test_binary_workbench_reference_jump_normalizes_and_assembles_valid_target():
    from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
    from src.presentation.ui.components.binary_workbench.editor.table import (
        BinaryWorkbenchGrid,
    )

    _app()
    codec = PsxMipsR3000ACodec()
    grid = BinaryWorkbenchGrid(codec)
    grid._jump_reference_offset = "RAM"
    grid._reference_offset_bases = {"RAM": "0x80000000"}
    grid._total_size = 8

    for mnemonic in ("j", "jal"):
        normalized = grid._reference_jump_line(
            f"{mnemonic} &0x801D9200",
            {},
        )
        assert normalized == f"{mnemonic} 0x001E8A00"
        assert grid._invalid_standard_jump_target(normalized) is False
        assert grid._invalid_standard_jump_target(f"{mnemonic} 0x1D9200") is False
        assert codec.assemble(normalized, 0) is not None


def test_binary_workbench_symbols_do_not_match_different_directory(tmp_path: Path):
    first = tmp_path / "one" / "shared.asm"
    second = tmp_path / "two" / "shared.asm"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("nop\n", encoding="utf-8")
    second.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(first)
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    tool.tabs.save_current_symbols("shared-symbols")
    tool.open_assembly_path(second)
    current = tool.tabs.current_context()

    assert current is not None
    assert current.variables == {}
    assert current.equates == {}
    assert current.labels == {}


def test_binary_workbench_instruction_tab_inserts_three_spaces(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.clear()
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Tab, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(editor, event)

    assert editor.toPlainText() == "   "


def test_binary_workbench_instruction_editor_preserves_space_and_tab_indentation(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("ADDIU")
    cursor = editor.textCursor()
    cursor.setPosition(len("ADDIU"))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier, " "))
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Tab, Qt.NoModifier))

    assert editor.toPlainText() == "ADDIU    "
    assert editor.textCursor().position() == len("ADDIU    ")


def test_binary_workbench_detects_unsaved_changes_before_closing_tab(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    assert tool.tabs.has_unsaved_changes(0) is False
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("addiu $sp,$sp,-0x10")  # type: ignore[attr-defined]
    _app().processEvents()

    assert tool.tabs.has_unsaved_changes(0) is True


def test_binary_workbench_closes_tab_without_prompt_for_whitespace_only_overlay(tmp_path: Path, monkeypatch):
    binary_path = tmp_path / "source.bin"
    binary_path.write_bytes(bytes.fromhex("00 FF FF FF"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs._append_tab(
        BinaryWorkbenchTabContextDTO(
            tab_id="whitespace",
            kind="binary",
            display_name=binary_path.name,
            source_path=str(binary_path),
            byte_overlays={"0x00000000": "00 00 00 00"},
            instruction_overlays={"0x00000000": "\t"},
            version_dirty=True,
        )
    )
    monkeypatch.setattr(
        tool,
        "_native_close_question",
        lambda: pytest.fail("Whitespace-only overlays must not request saving"),
    )

    tool._request_tab_close(tool.tabs.currentIndex())

    assert tool.tabs.count() == 0


def test_binary_workbench_detects_workspace_module_changes_before_closing_tab(tmp_path: Path):
    binary_path = tmp_path / "source.bin"
    binary_path.write_bytes(bytes(4096))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    assert tool.tabs.has_unsaved_changes(0) is False

    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO("slus", 24)])

    assert tool.tabs.has_unsaved_changes(0) is True
    assert tool.tabs.save_current_workspace() is True
    assert tool.tabs.has_unsaved_changes(0) is False


def test_binary_workbench_detects_deleted_instruction_rows(tmp_path: Path):
    assembly_path = tmp_path / "trimmed.asm"
    assembly_path.write_text("nop\naddiu $sp,$sp,-0x10\njr $ra\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("nop\njr $ra")  # type: ignore[attr-defined]
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert len(current.rows) == 2
    assert current.rows[0].offsets["File"] == "0x00000000"
    assert current.rows[1].offsets["File"] == "0x00000004"
    assert current.rows[1].instruction == "JR $ra"
    assert tool.tabs.has_unsaved_changes(0) is True


def test_binary_workbench_instruction_delete_keeps_raw_bytes_and_offsets_synced(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("jal 0x8\njal 0x8\nlbu $s1, 0xC($gp)\nnop")  # type: ignore[attr-defined]
    _app().processEvents()

    page.grid.instructions.setPlainText("beqz $s1, 0x8\nnop")  # type: ignore[attr-defined]
    QTest.qWait(350)
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert [line.upper() for line in page.grid.instructions.toPlainText().splitlines()] == ["BEQZ $S1, 0X8", "NOP"]  # type: ignore[attr-defined]
    assert [row.offsets["File"] for row in current.rows] == ["0x00000000", "0x00000004"]
    assert page.grid.raw_instructions.toPlainText().splitlines() == [  # type: ignore[attr-defined]
        "beq $s1, $zero, 0x0001",
        "nop",
    ]
    assert page.grid.bytes.toPlainText().splitlines() == ["01 00 20 12", "00 00 00 00"]  # type: ignore[attr-defined]


def test_binary_workbench_bytes_editor_auto_formats_and_uppercases(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("nop")  # type: ignore[attr-defined]
    assert page.grid.ensure_consistent("test").success  # type: ignore[attr-defined]
    page.grid.bytes.setPlainText("aa55ccdd")  # type: ignore[attr-defined]
    _app().processEvents()

    assert page.grid.bytes.toPlainText() == "AA 55 CC DD"  # type: ignore[attr-defined]


def test_binary_workbench_instruction_hex_prefix_keeps_lowercase_x(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("jal 0x80010000")  # type: ignore[attr-defined]
    _app().processEvents()

    assert page.grid.instructions.toPlainText() == "JAL 0x80010000"  # type: ignore[attr-defined]


def test_binary_workbench_instruction_uppercase_affects_only_mnemonics(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    tool.tabs.set_current_symbols({"variable1": "20"}, {"equate1": "0x34"}, {})
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("Label_1: addiu $s1,$s1,0x1f4 ; keep 0xbeef")  # type: ignore[attr-defined]
    _app().processEvents()

    assert page.grid.instructions.toPlainText() == "Label_1: ADDIU $s1,$s1,0x1F4 ; keep 0xbeef"  # type: ignore[attr-defined]


def test_binary_workbench_bytes_formatter_has_separate_uppercase_preferences(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    tool.tabs.set_current_bytes_formatter(2, False, False)
    current = tool.tabs.current_context()
    preferences = tool.tabs.preferences()

    assert current is not None
    assert preferences.group_bytes == 2
    assert preferences.uppercase_bytes is False
    assert preferences.uppercase_instructions is False
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("nop")  # type: ignore[attr-defined]
    assert page.grid.ensure_consistent("test").success  # type: ignore[attr-defined]
    editor = page.grid.bytes  # type: ignore[attr-defined]
    editor.clear()
    editor.setFocus()
    for key, text in (
        (Qt.Key_A, "a"),
        (Qt.Key_A, "a"),
        (Qt.Key_B, "b"),
        (Qt.Key_B, "b"),
        (Qt.Key_C, "c"),
        (Qt.Key_C, "c"),
        (Qt.Key_D, "d"),
        (Qt.Key_D, "d"),
    ):
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, key, Qt.NoModifier, text))

    assert editor.toPlainText() == "aabb ccdd"


def test_binary_workbench_native_close_dialog_maps_windows_buttons():
    assert _map_windows_response(6).name == "Save"
    assert _map_windows_response(7).name == "Discard"
    assert _map_windows_response(2).name == "Cancel"

def test_binary_workbench_version_switch_keeps_tab_symbols_shared_in_memory(
    tmp_path: Path,
    monkeypatch,
):
    binary_path = tmp_path / "versions.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    base_name = tool.tabs.current_context().active_version_name
    assert base_name
    tool.tabs.set_current_symbols({"base_var": "0x10"}, {"base_eq": "0x20"}, {})
    assert tool.tabs.create_version("v1") is True
    tool.tabs.set_current_symbols({"v1_var": "0x30"}, {"v1_eq": "0x40"}, {})
    monkeypatch.setattr(
        tool.tabs._workspace_repository,  # type: ignore[attr-defined]
        "save_tab_workspace",
        lambda *args, **kwargs: pytest.fail("version switch must not write JSON"),
    )

    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("addiu $v0,$zero,0x1")
    _app().processEvents()
    assert tool.tabs.load_version(base_name) is True
    assert editor.toPlainText().lower() == "nop"
    current = tool.tabs.current_context()
    assert current.symbols == {"v1_var": "0x30", "v1_eq": "0x40"}
    assert current.variables == current.symbols
    assert current.equates == current.symbols
    tool.tabs.set_current_symbols({"base_var": "0x11"}, {"base_eq": "0x21"}, {})

    editor.setPlainText("ori $v0,$zero,0x2")
    _app().processEvents()
    assert tool.tabs.load_version("v1") is True
    assert editor.toPlainText().lower() == "addiu $v0,$zero,0x1"
    current = tool.tabs.current_context()
    assert current.symbols == {"base_var": "0x11", "base_eq": "0x21"}
    assert current.variables == current.symbols
    assert current.equates == current.symbols
    assert tool.tabs.load_version(base_name) is True
    assert editor.toPlainText().lower() == "ori $v0,$zero,0x2"
    current = tool.tabs.current_context()
    assert current.symbols == {"base_var": "0x11", "base_eq": "0x21"}
    assert current.variables == current.symbols
    assert current.equates == current.symbols


def test_binary_workbench_assembly_version_switch_keeps_each_version_isolated_in_memory(
    tmp_path: Path,
    monkeypatch,
):
    assembly_path = tmp_path / "versions.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    base_name = tool.tabs.current_context().active_version_name
    assert base_name
    assert tool.tabs.create_version("v1") is True
    monkeypatch.setattr(
        tool.tabs._workspace_repository,  # type: ignore[attr-defined]
        "save_tab_workspace",
        lambda *args, **kwargs: pytest.fail("version switch must not write JSON"),
    )

    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("addiu $v0,$zero,0x1")
    _app().processEvents()
    assert tool.tabs.load_version(base_name) is True
    assert editor.toPlainText().lower() == "nop"

    editor.setPlainText("ori $v0,$zero,0x2")
    _app().processEvents()
    assert tool.tabs.load_version("v1") is True
    assert editor.toPlainText().lower() == "addiu $v0,$zero,0x1"

    assert tool.tabs.load_version(base_name) is True
    assert editor.toPlainText().lower() == "ori $v0,$zero,0x2"
    assert assembly_path.read_text(encoding="utf-8") == "nop\n"


def test_binary_workbench_every_third_version_update_refreshes_default_backup(tmp_path: Path):
    binary_path = tmp_path / "default_backup.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    assert tool.tabs.create_version("experiment") is True
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("addiu $v0, $zero, 1 ; backup comment")
    _app().processEvents()

    results = []
    for _ in range(3):
        assert tool.tabs.update_current_version(
            "experiment",
            mark_dirty=False,
            reload_page=False,
        )
        results.append(tool.tabs.backup_default_version_if_due())

    current = tool.tabs.current_context()
    backup = next(version for version in current.versions if version.name == "default")
    assert results == [False, False, True]
    assert current.active_version_name == "experiment"
    assert backup.rows[0].bytes_text == "01 00 02 24"
    assert "backup comment" in backup.instruction_overlays["0x00000000"]


def test_binary_workbench_scratch_symbols_wait_for_first_version_update(tmp_path: Path, monkeypatch):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    scratch = tool.tabs.current_context()
    assert tool.tabs.scratch_initial_version_required(scratch)
    warnings: list[str] = []
    monkeypatch.setattr(tool, "_show_warning_status", warnings.append)
    tool._open_local_symbols()
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_SYMBOLS_VERSION_REQUIRED]

    target = tmp_path / "saved_scratch.asm"
    assert tool.tabs.save_current_assembly_copy(target, adopt_source=True)
    assembly = tool.tabs.current_context()
    assert tool.tabs.scratch_initial_version_required(assembly)

    assert tool.tabs.update_current_version(
        assembly.active_version_name,
        mark_dirty=False,
        reload_page=False,
    )
    tool.tabs.mark_initial_version_saved(assembly.tab_id)
    assert not tool.tabs.scratch_initial_version_required(tool.tabs.current_context())


def test_binary_workbench_external_symbols_are_copied_after_initial_scratch_save(tmp_path: Path):
    from src.presentation.repository.binary_workbench_workspace.constants import SYMBOLS

    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window
    external = tmp_path / "external_symbols.json"
    external.write_text('{"name":"external","symbols":{"value":"0x20"}}', encoding="utf-8")

    assert tool is not None
    tool.tabs.new_scratch_tab()
    assert tool.tabs.save_current_assembly_copy(tmp_path / "scratch.asm", adopt_source=True)
    current = tool.tabs.current_context()
    assert tool.tabs.update_current_version(current.active_version_name, mark_dirty=False, reload_page=False)
    tool.tabs.mark_initial_version_saved(current.tab_id)

    tool.tabs.set_current_symbols({"value": "0x20"}, {}, current.labels)
    tool.tabs.set_current_module_path(SYMBOLS, external)
    current = tool.tabs.current_context()
    assert tool.tabs.update_current_version(
        current.active_version_name,
        mark_dirty=False,
        reload_page=False,
    )
    assert tool.tabs.save_current_workspace()
    current = tool.tabs.current_context()
    imported = Path(current.module_paths[SYMBOLS])

    assert imported != external
    assert imported.parent.name == "Symbols"
    assert imported.is_file()
    assert json.loads(imported.read_text(encoding="utf-8"))["symbols"] == {"value": "0x20"}
    assert external.read_text(encoding="utf-8") == '{"name":"external","symbols":{"value":"0x20"}}'
    tool._native_close_question = lambda: QMessageBox.StandardButton.Save
    tool._request_tab_close(0)
    assert tool.tabs.count() == 0


def test_binary_workbench_uppercase_waits_for_next_line_without_moving_cursor(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    editor.setPlainText("addiu $v0,$zero,0x1f")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    before = cursor.position()

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier),
    )
    _app().processEvents()

    assert editor.toPlainText().split("\n")[0] == "ADDIU $v0,$zero,0x1F"
    assert editor.textCursor().position() == before + 1


def test_binary_workbench_label_with_space_before_colon_remains_invalid(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    editor.setPlainText("loop : addiu $v0,$zero,0x1f")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier),
    )
    _app().processEvents()

    assert editor.toPlainText().split("\n")[0] == "loop : addiu $v0,$zero,0x1F"
    assert "loop" not in tool.tabs.currentWidget().grid._labels  # type: ignore[attr-defined]


def test_binary_workbench_shift_enter_adds_assembly_comment_line(tmp_path: Path):
    assembly_path = tmp_path / "comments.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.ShiftModifier),
    )
    _app().processEvents()

    assert editor.toPlainText().endswith("\n; ")


def test_binary_workbench_command_expansion_can_be_undone(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.set_custom_commands({"pair": ["nop", "nop"]})  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    editor.setPlainText("/pair")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier),
    )
    _app().processEvents()
    assert editor.toPlainText() == "nop\nnop"

    QApplication.sendEvent(
        editor,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Z, Qt.ControlModifier),
    )
    _app().processEvents()
    assert editor.toPlainText() == "/pair"


def test_binary_workbench_sltu_uses_arithmetic_mnemonic_color():
    assert psx_mips_highlight_color("mnemonic", "sltu") == psx_mips_highlight_color(
        "mnemonic",
        "addiu",
    )


def test_binary_workbench_update_version_does_not_reload_current_binary_page(tmp_path: Path):
    binary_path = tmp_path / "no_reload.bin"
    binary_path.write_bytes(bytes.fromhex("11 00 04 24") + bytes.fromhex("00 00 00 00") * 16)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)
    page = tool.tabs.currentWidget()
    lines = page.grid.instructions.toPlainText().splitlines()  # type: ignore[attr-defined]
    lines[0] = "nop"
    page.grid.instructions.setPlainText("\n".join(lines))  # type: ignore[attr-defined]

    def fail_load_context(*args, **kwargs):
        pytest.fail("ALT+S must not reload the current binary page")

    page.load_context = fail_load_context  # type: ignore[method-assign]

    tool._update_version()
    current = tool.tabs.current_context()
    active = next(version for version in current.versions if version.name == current.active_version_name)

    assert page.grid.instructions.toPlainText().splitlines()[0] == "nop"  # type: ignore[attr-defined]
    assert active.rows or active.instruction_overlays or active.instructions_by_line


def test_binary_workbench_alt_s_persists_skipped_binary_lines(tmp_path: Path):
    binary_path = tmp_path / "skipped-line.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 8)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    lines = page.grid.instructions.toPlainText().splitlines()  # type: ignore[attr-defined]
    lines.insert(1, "")
    page.grid.instructions.setPlainText("\n".join(lines))  # type: ignore[attr-defined]
    _app().processEvents()

    tool._update_version()
    current = tool.tabs.current_context()
    active = next(version for version in current.versions if version.name == current.active_version_name)
    payload = json.loads(Path(current.module_paths["versions"]).read_text(encoding="utf-8"))

    assert active.instructions_by_line[1] == ""
    assert payload["versions"][active.name]["1"] == ""


def test_binary_workbench_update_version_does_not_reload_current_assembly_page(tmp_path: Path):
    assembly_path = tmp_path / "no_reload.asm"
    assembly_path.write_text("addiu $a0, $zero, 0x11\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    lines = page.grid.instructions.toPlainText().splitlines()  # type: ignore[attr-defined]
    lines[0] = "nop"
    page.grid.instructions.setPlainText("\n".join(lines))  # type: ignore[attr-defined]

    def fail_load_context(*args, **kwargs):
        pytest.fail("ALT+S must not reload the current assembly page")

    page.load_context = fail_load_context  # type: ignore[method-assign]

    tool._update_version()
    current = tool.tabs.current_context()
    active = next(version for version in current.versions if version.name == current.active_version_name)

    assert page.grid.instructions.toPlainText().splitlines()[0] == "nop"  # type: ignore[attr-defined]
    assert active.rows or active.instruction_overlays or active.instructions_by_line


def test_binary_workbench_update_version_preserves_bytes_highlighting(tmp_path: Path):
    """Keep the visible Bytes colors after the complete Alt+S workflow."""

    assembly_path = tmp_path / "bytes-highlight.asm"
    assembly_path.write_text("addiu $a0, $zero, 0x11\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    _app().processEvents()
    page.grid._bytes_highlighter.set_projection_window(0, 0)  # type: ignore[attr-defined]
    page.grid._bytes_highlighter.rehighlightBlock(  # type: ignore[attr-defined]
        page.grid.bytes.document().firstBlock()  # type: ignore[attr-defined]
    )

    def byte_colors() -> set[str]:
        return {
            item.format.foreground().color().name().casefold()
            for item in page.grid.bytes.document().firstBlock().layout().formats()  # type: ignore[attr-defined]
            if item.format.foreground().style() != Qt.NoBrush
        }

    expected = {"#eaeaf5", "#8fa6ff"}
    assert expected <= byte_colors()
    page.grid._bytes_highlighter.set_projection_window(100, 101)  # type: ignore[attr-defined]

    tool._update_version()
    QTest.qWait(200)
    _app().processEvents()

    assert expected <= byte_colors()


def test_binary_workbench_saved_assembly_version_comments_invalid_source(tmp_path: Path):
    """Persist invalid Assembly safely while leaving the active editor untouched."""

    assembly_path = tmp_path / "invalid-version.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    locked_rules = BinaryWorkbenchEditRulesDTO(allow_byte_shift=False)
    tool.tabs._preferences = BinaryWorkbenchPreferencesDTO(
        assembly_edit_rules=locked_rules,
    )
    page.grid.set_edit_rules(locked_rules)  # type: ignore[attr-defined]
    page.grid.instructions.setPlainText("bad $a0 ; keep this")  # type: ignore[attr-defined]
    _app().processEvents()

    tool._update_version()
    current = tool.tabs.current_context()
    active = next(
        version
        for version in current.versions
        if version.name == current.active_version_name
    )

    assert active.rows[0].instruction == (
        "nop; Incorrect Instruction: bad $a0 | keep this"
    )
    assert page.grid.instructions.toPlainText().splitlines()[0] == (  # type: ignore[attr-defined]
        "bad $a0 ; keep this"
    )


def test_binary_workbench_shift_enabled_keeps_invalid_version_source(tmp_path: Path):
    assembly_path = tmp_path / "shifted-invalid-version.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("bad $a0")  # type: ignore[attr-defined]
    _app().processEvents()

    tool._update_version()
    current = tool.tabs.current_context()
    active = next(
        version
        for version in current.versions
        if version.name == current.active_version_name
    )

    assert active.rows[0].instruction == "bad $a0"


def test_binary_workbench_close_flush_preserves_locked_source_without_assembly(
    tmp_path: Path,
):
    assembly_path = tmp_path / "locked-close.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    locked_rules = BinaryWorkbenchEditRulesDTO(allow_byte_shift=False)
    tool.tabs._preferences = BinaryWorkbenchPreferencesDTO(
        assembly_edit_rules=locked_rules,
    )
    page.grid.set_edit_rules(locked_rules)  # type: ignore[attr-defined]
    page.grid.instructions.setPlainText("broken")  # type: ignore[attr-defined]
    _app().processEvents()

    tool.tabs.flush_open_workspaces()
    current = tool.tabs.current_context()
    active = next(
        version
        for version in current.versions
        if version.name == current.active_version_name
    )

    assert active.rows[0].instruction == "broken"


def test_binary_workbench_saved_assembly_version_closes_without_original_file_prompt(
    tmp_path: Path,
    monkeypatch,
):
    assembly_path = tmp_path / "versioned-close.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("nop\n\nnop")  # type: ignore[attr-defined]
    _app().processEvents()
    tool._update_version()
    monkeypatch.setattr(
        tool,
        "_native_close_question",
        lambda: pytest.fail("A saved active version must close without prompting."),
    )

    tool._request_tab_close(0)

    assert tool.tabs.count() == 0

def test_binary_workbench_instruction_block_paste_replaces_mouse_selected_lines():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("nop\nnop\nnop\nnop")
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.setPosition(editor.document().findBlockByNumber(3).position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    app.clipboard().setText("addiu $a0, $zero, 0x1\naddiu $a1, $zero, 0x2\nnop")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText().splitlines() == [
        "addiu $a0, $zero, 0x1",
        "addiu $a1, $zero, 0x2",
        "nop",
        "nop",
    ]


def test_binary_workbench_instruction_block_paste_requires_exact_selected_line_count():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("nop\nnop\nnop\nnop")
    warnings: list[str] = []
    editor.navigationWarningRequested.connect(warnings.append)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.setPosition(editor.document().findBlockByNumber(3).position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    app.clipboard().setText("addiu $a0, $zero, 0x1\naddiu $a1, $zero, 0x2")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText().splitlines() == ["nop", "nop", "nop", "nop"]
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_MULTILINE_PASTE_LINE_MISMATCH]


def test_binary_workbench_instruction_block_paste_allows_mismatch_when_byte_shift_enabled():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.set_bytes_line_shift_allowed(True)
    editor.setPlainText("nop\nnop\nnop\nnop")
    warnings: list[str] = []
    editor.navigationWarningRequested.connect(warnings.append)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.setPosition(editor.document().findBlockByNumber(3).position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    app.clipboard().setText("addiu $a0, $zero, 0x1\naddiu $a1, $zero, 0x2")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert warnings == []
    assert editor.toPlainText() != "nop\nnop\nnop\nnop"


def test_binary_workbench_assembly_version_rows_ignore_duplicate_line_payload(tmp_path: Path):
    assembly_path = tmp_path / "teste_scra.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    versions_path = tmp_path / "teste_scra_versions.json"
    rows = [
        _version_row_payload("-", "; keep asm comment row", ""),
        _version_row_payload("0x00000000", "start: nop", "00 00 00 00"),
        _version_row_payload("0x00000004", "addiu $a0, $zero, 0x1", "01 00 04 24"),
    ]
    versions_path.write_text(
        json.dumps(
            {
                "active_version": "testando_Asm2",
                "versions": {
                    "testando_Asm2": {
                        "0": rows[0]["instruction"],
                        "1": rows[1]["instruction"],
                        "2": rows[2]["instruction"],
                        "rows": rows,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    assert tool.tabs.load_versions_file(versions_path) == "testando_Asm2"
    current = tool.tabs.current_context()
    page = tool.tabs.currentWidget()

    assert current is not None
    assert [row.offsets.get("File") for row in current.rows] == [
        "-",
        "0x00000000",
        "0x00000004",
    ]
    assert [row.instruction for row in current.rows] == [
        "; keep asm comment row",
        "start: nop",
        "addiu $a0, $zero, 0x1",
    ]
    assert page.grid.instructions.toPlainText().splitlines() == [  # type: ignore[attr-defined]
        "; keep asm comment row",
        "start: nop",
        "ADDIU $a0, $zero, 0x1",
    ]


def test_binary_workbench_new_editor_label_updates_symbol_state(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("fresh_label: nop\nnop")  # type: ignore[attr-defined]
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert current.labels["fresh_label"] == "0x00000000"
    assert current.symbol_offsets["fresh_label"] == ["0x00000000"]
    assert page.grid._labels["fresh_label"] == "0x00000000"  # type: ignore[attr-defined]


def test_binary_workbench_label_fold_hides_complete_rows_without_deleting_them(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText(  # type: ignore[attr-defined]
        "start: nop\naddiu $v0, $zero, 1\njr $ra\nnext: nop\nnop"
    )
    _app().processEvents()
    page.grid.flush_pending_rows_changed()  # type: ignore[attr-defined]
    original_text = page.grid.instructions.toPlainText()  # type: ignore[attr-defined]
    original_rows = page.grid.export_rows()  # type: ignore[attr-defined]

    page.grid.instructions.request_label_fold_toggle(0)  # type: ignore[attr-defined]

    editors = list(page.grid._fold_editors())  # type: ignore[attr-defined]
    assert page.grid.instructions._label_fold_gutter.isVisible() is True  # type: ignore[attr-defined]
    assert page.grid.instructions._label_fold_regions[0] == ("start", True)  # type: ignore[attr-defined]
    assert page.grid._offset_editors["File"].document().findBlockByNumber(0).text() == "0x00000000"  # type: ignore[attr-defined]
    assert page.grid.raw_instructions.document().findBlockByNumber(0).text()  # type: ignore[attr-defined]
    assert page.grid.bytes.document().findBlockByNumber(0).text()  # type: ignore[attr-defined]
    for editor in editors:
        assert editor.document().findBlockByNumber(0).isVisible() is True
        assert editor.document().findBlockByNumber(1).isVisible() is False
        assert editor.document().findBlockByNumber(2).isVisible() is False
        assert editor.document().findBlockByNumber(3).isVisible() is True
    assert page.grid.instructions.toPlainText() == original_text  # type: ignore[attr-defined]
    assert page.grid.export_rows() == original_rows  # type: ignore[attr-defined]

    page.grid.toggle_label_fold("start")  # type: ignore[attr-defined]
    assert all(editor.document().findBlockByNumber(1).isVisible() for editor in editors)
    assert all(editor.document().findBlockByNumber(2).isVisible() for editor in editors)


def test_binary_workbench_responsive_window_hides_bytes_below_800px(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid._configured_columns = [  # type: ignore[attr-defined]
        BINARY_WORKBENCH_TEXT.FILE,
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        BINARY_WORKBENCH_TEXT.BYTES,
        BINARY_WORKBENCH_TEXT.INSTRUCTION,
    ]
    page.grid._apply_bytes_visibility()  # type: ignore[attr-defined]
    _app().processEvents()
    assert BINARY_WORKBENCH_TEXT.BYTES in page.grid._configured_columns  # type: ignore[attr-defined]

    assert tool.minimumHeight() == BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT
    assert page.grid.raw_shell.width() == BINARY_WORKBENCH_LAYOUT.EDITOR_RAW_INSTRUCTION_WIDTH  # type: ignore[attr-defined]

    tool.resize(799, BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT)
    _app().processEvents()
    assert page.grid.bytes_shell.isVisible() is False  # type: ignore[attr-defined]

    tool.resize(800, BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT)
    _app().processEvents()
    assert page.grid.bytes_shell.isVisible() is True  # type: ignore[attr-defined]

    page.grid._configured_columns.remove(BINARY_WORKBENCH_TEXT.BYTES)  # type: ignore[attr-defined]
    page.grid._apply_bytes_visibility()  # type: ignore[attr-defined]
    assert page.grid.bytes_shell.isVisible() is False  # type: ignore[attr-defined]

    tool.resize(900, BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT)
    _app().processEvents()
    assert page.grid.bytes_shell.isVisible() is False  # type: ignore[attr-defined]

    page.grid._configured_columns.append(BINARY_WORKBENCH_TEXT.BYTES)  # type: ignore[attr-defined]
    page.grid._apply_bytes_visibility()  # type: ignore[attr-defined]
    assert page.grid.bytes_shell.isVisible() is True  # type: ignore[attr-defined]


def test_binary_workbench_fold_moves_cursor_after_hidden_label_body(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("start:\nnop\nnext: nop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    cursor = grid.instructions.textCursor()
    cursor.setPosition(grid.instructions.document().findBlockByNumber(1).position())
    grid.instructions.setTextCursor(cursor)

    grid.toggle_label_fold("start")

    assert grid.instructions.document().findBlockByNumber(1).isVisible() is False
    cursor = grid.instructions.textCursor()
    label = grid.instructions.document().findBlockByNumber(0)
    assert cursor.blockNumber() == 0
    assert cursor.position() == label.position() + len(label.text())


def test_binary_workbench_enter_on_collapsed_label_expands_and_inserts_after_label(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("start:\nnop\nnext: nop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    grid.toggle_label_fold("start")
    cursor = grid.instructions.textCursor()
    cursor.setPosition(grid.instructions.document().findBlockByNumber(0).position())
    grid.instructions.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier),
    )
    _app().processEvents()

    lines = grid.instructions.toPlainText().split("\n")
    assert lines == ["start:", "", "nop", "next: nop"]
    assert grid.instructions.textCursor().blockNumber() == 1
    assert grid.instructions.document().findBlockByNumber(2).isVisible() is True


def test_binary_workbench_shift_enter_on_collapsed_label_expands_and_inserts_after_label(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("start:\nnop\nnext: nop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    grid.toggle_label_fold("start")
    cursor = grid.instructions.textCursor()
    cursor.setPosition(grid.instructions.document().findBlockByNumber(0).position())
    grid.instructions.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.ShiftModifier),
    )
    _app().processEvents()

    lines = grid.instructions.toPlainText().split("\n")
    assert lines == ["start:", "; ", "nop", "next: nop"]
    assert grid.instructions.textCursor().blockNumber() == 1
    assert grid.instructions.document().findBlockByNumber(2).isVisible() is True


def test_binary_workbench_alt_enter_on_collapsed_label_expands_and_inserts_after_label(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("start:\nnop\nnext: nop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    grid.toggle_label_fold("start")
    cursor = grid.instructions.textCursor()
    cursor.setPosition(grid.instructions.document().findBlockByNumber(0).position())
    grid.instructions.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.AltModifier),
    )
    _app().processEvents()

    lines = grid.instructions.toPlainText().split("\n")
    assert lines == ["start:", "nop", "", "nop", "next: nop"]
    assert grid.instructions.document().findBlockByNumber(1).isVisible() is True


def test_binary_workbench_edit_on_collapsed_label_expands_before_typing(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("start:\nnop\nnext: nop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    grid.toggle_label_fold("start")
    cursor = grid.instructions.textCursor()
    cursor.setPosition(grid.instructions.document().findBlockByNumber(0).position() + len("start:"))
    grid.instructions.setTextCursor(cursor)

    QApplication.sendEvent(
        grid.instructions,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_X, Qt.NoModifier, "x"),
    )
    _app().processEvents()

    assert grid.instructions.toPlainText() == "start:x\nnop\nnext: nop"
    assert grid.instructions.document().findBlockByNumber(1).isVisible() is True


def test_binary_workbench_collapsed_label_at_end_keeps_cursor_on_label_line(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    grid.instructions.setPlainText("start:\nnop")
    _app().processEvents()
    grid.flush_pending_rows_changed()

    grid.toggle_label_fold("start")

    cursor = grid.instructions.textCursor()
    label = grid.instructions.document().findBlockByNumber(0)
    assert grid.instructions.toPlainText() == "start:\nnop"
    assert cursor.blockNumber() == 0
    assert cursor.position() == label.position() + len(label.text())


def test_binary_workbench_collapsed_label_projects_offset_and_uses_visible_scroll_rows(
    tmp_path: Path,
):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    body = ["nop"] * 40
    page.grid.instructions.setPlainText(  # type: ignore[attr-defined]
        "\n".join(["routine:", "jr $ra", "; delay slot", "nop", *body, "next: nop"])
    )
    _app().processEvents()
    page.grid.flush_pending_rows_changed()  # type: ignore[attr-defined]
    scrollbar = page.grid.scrollbar  # type: ignore[attr-defined]
    expanded_maximum = scrollbar.maximum()
    file_offsets = page.grid._offset_editors["File"]  # type: ignore[attr-defined]

    assert file_offsets.document().findBlockByNumber(0).text() == "-"

    page.grid.toggle_label_fold("routine")  # type: ignore[attr-defined]

    assert file_offsets.document().findBlockByNumber(0).text() == "0x00000000"
    assert page.grid.instructions.document().findBlockByNumber(3).isVisible() is False  # type: ignore[attr-defined]
    assert scrollbar.maximum() < expanded_maximum

    QApplication.sendEvent(
        page.grid.instructions,  # type: ignore[attr-defined]
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key_PageDown, Qt.NoModifier),
    )

    expected_page = min(scrollbar.pageStep(), scrollbar.maximum())
    assert scrollbar.value() == expected_page
    assert all(
        editor.verticalScrollBar().value() == expected_page // 4
        for editor in (
            *page.grid._offset_editors.values(),  # type: ignore[attr-defined]
            page.grid.raw_instructions,  # type: ignore[attr-defined]
            page.grid.bytes,  # type: ignore[attr-defined]
            page.grid.decoded_text,  # type: ignore[attr-defined]
            page.grid.instructions,  # type: ignore[attr-defined]
        )
        if editor.isVisible()
    )

    page.grid.toggle_label_fold("routine")  # type: ignore[attr-defined]

    assert file_offsets.document().findBlockByNumber(0).text() == "-"
    assert page.grid.instructions.document().findBlockByNumber(3).isVisible() is True  # type: ignore[attr-defined]


def test_binary_workbench_branch_navigation_expands_target_label(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText(  # type: ignore[attr-defined]
        "start: nop\nnop\njr $ra\ntarget: nop\nnop\njr $ra\nbeq $zero, $zero, target"
    )
    _app().processEvents()
    page.grid.flush_pending_rows_changed()  # type: ignore[attr-defined]
    page.grid.toggle_label_fold("target")  # type: ignore[attr-defined]
    target_body = page.grid.instructions.document().findBlockByNumber(4)  # type: ignore[attr-defined]
    assert target_body.isVisible() is False

    page.grid.jumpNavigationActivated.emit(0x0C, 0x18)  # type: ignore[attr-defined]
    _app().processEvents()

    assert target_body.isVisible() is True
    assert page.grid.instructions._label_fold_regions[3] == ("target", False)  # type: ignore[attr-defined]


def test_binary_workbench_label_declaration_is_not_clickable_but_branch_operand_is(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("target: nop\nbeq $zero, $zero, target")
    _app().processEvents()

    declaration = editor.document().findBlockByNumber(0)
    declaration_cursor = QTextCursor(declaration)
    declaration_cursor.setPosition(declaration.position() + 2)
    declaration_point = editor.cursorRect(declaration_cursor).center()
    branch = editor.document().findBlockByNumber(1)
    branch_cursor = QTextCursor(branch)
    branch_cursor.setPosition(branch.position() + branch.text().rfind("target") + 2)
    branch_point = editor.cursorRect(branch_cursor).center()

    assert editor._jump_target_at_position(declaration_point) is None
    assert editor._jump_target_at_position(branch_point) == 0


@pytest.mark.parametrize(
    ("instruction", "labels"),
    [
        ("beq $zero, $zero, target", {"target": "0x2"}),
        ("j 0xF802", {}),
    ],
)
def test_binary_workbench_click_navigation_reports_misaligned_target(
    instruction: str,
    labels: dict[str, str],
):
    from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec

    _app()
    editor = WorkbenchEditor()
    editor.setPlainText(instruction)
    editor.set_jump_navigation(
        PsxMipsR3000ACodec(),
        labels,
        {},
        {},
    )
    block = editor.document().firstBlock()
    cursor = QTextCursor(block)
    token = instruction.rsplit(maxsplit=1)[-1]
    cursor.setPosition(block.position() + block.text().rfind(token) + 1)
    point = editor.cursorRect(cursor).center()

    assert editor._navigation_warning_at_position(point) == BINARY_WORKBENCH_TEXT.STATUS_TARGET_MISALIGNED


def test_binary_workbench_ctrl_click_edits_jump_symbol_without_navigating():
    from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec

    _app()
    editor = WorkbenchEditor()
    symbols = {"jump_symbol": "0x1D9200"}
    editor.setPlainText("jal @jump_symbol")
    editor.set_symbol_helpers({}, symbols, symbols)
    editor.set_jump_navigation(PsxMipsR3000ACodec(), {}, symbols, symbols)
    editor.resize(320, 100)
    editor.show()
    _app().processEvents()
    block = editor.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position() + block.text().index("jump_symbol") + 2)
    point = editor.cursorRect(cursor).center()
    navigated: list[int] = []
    edited: list[str] = []
    editor.jumpNavigationActivated.connect(lambda target, _source: navigated.append(target))
    editor.symbolEditRequested.connect(edited.append)

    QTest.mouseClick(editor.viewport(), Qt.LeftButton, Qt.NoModifier, point)
    QTest.mouseClick(editor.viewport(), Qt.LeftButton, Qt.ControlModifier, point)

    assert navigated == [0x1C9A00]
    assert edited == ["jump_symbol"]


def test_binary_workbench_new_label_updates_highlighter_and_branch_target_immediately(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    editor = grid.instructions
    editor.setPlainText("nop\nnop\nnop\nnop\nbeq $zero, $zero, label2")
    _app().processEvents()
    editor.setPlainText("nop\nnop\nnop\nlabel2: nop\nbeq $zero, $zero, label2")
    _app().processEvents()

    declaration = editor.document().findBlockByNumber(3)
    declaration_cursor = QTextCursor(declaration)
    declaration_cursor.setPosition(declaration.position() + 2)
    declaration_point = editor.cursorRect(declaration_cursor).center()
    branch = editor.document().findBlockByNumber(4)
    branch_cursor = QTextCursor(branch)
    branch_cursor.setPosition(branch.position() + branch.text().rfind("label2") + 2)
    branch_point = editor.cursorRect(branch_cursor).center()

    assert grid.current_labels() == {"label2": "0x0000000C"}
    assert page.current_context().labels == {"label2": "0x0000000C"}
    assert grid._instruction_highlighter._labels == {"label2": "0x0000000C"}
    assert "label2" in editor._jump_label_symbols
    assert editor._jump_target_at_position(declaration_point) is None
    assert editor._jump_target_at_position(branch_point) == 0x0C


def test_binary_workbench_label_target_resolves_outside_loaded_viewport(tmp_path: Path):
    binary_path = tmp_path / "far_label.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 512)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    assert all(grid._row_offset(index) != 0x400 for index in range(len(grid._rows)))
    grid.set_symbols({"far_target": "0x00000400"}, {}, {})

    assert grid.label_navigation_target("far_target") == 0x400


def test_binary_workbench_pseudo_branches_point_to_first_valid_label_instruction(
    tmp_path: Path,
):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText(
        "target:\n; comment\nlui $t0, 0x801A\nb target\nbeqz $t0, target\nbnez $t1, target"
    )
    _app().processEvents()

    for line_number in (3, 4, 5):
        block = editor.document().findBlockByNumber(line_number)
        cursor = QTextCursor(block)
        cursor.setPosition(block.position() + block.text().rfind("target") + 2)
        assert editor._jump_target_at_position(editor.cursorRect(cursor).center()) == 0

    page.grid.jumpNavigationActivated.emit(0, 4)  # type: ignore[attr-defined]
    _app().processEvents()

    assert editor.textCursor().blockNumber() == 2
    assert editor.textCursor().hasSelection() is False


def test_binary_workbench_label_tab_mirrors_parent_without_recursive_refresh(
    tmp_path: Path,
):
    assembly_path = tmp_path / "teste_new_v23.asm"
    assembly_path.write_text("test4: nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    parent = tool.tabs.currentWidget()
    tool.tabs.open_label_tab("test4", 0)
    label_page = tool.tabs.currentWidget()

    assert tool.tabs.tabText(1) == assembly_path.name
    assert tool.tabs.current_context().display_name == assembly_path.name

    label_editor = label_page.grid.instructions  # type: ignore[attr-defined]
    label_editor.moveCursor(QTextCursor.End)
    for _ in range(8):
        label_editor.insertPlainText("nop\n")
        _app().processEvents()

    tool.tabs.setCurrentIndex(0)
    _app().processEvents()
    parent_text = parent.grid.instructions.toPlainText()  # type: ignore[attr-defined]
    assert parent_text == label_editor.toPlainText()

    parent_editor = parent.grid.instructions  # type: ignore[attr-defined]
    parent_editor.moveCursor(QTextCursor.End)
    parent_editor.insertPlainText("addiu $v0, $zero, 1\n")
    _app().processEvents()
    tool.tabs.setCurrentIndex(1)
    _app().processEvents()

    assert label_editor.toPlainText() == parent_editor.toPlainText()


def test_binary_workbench_instruction_edit_blocks_synchronous_reentry(
    tmp_path: Path,
    monkeypatch,
):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    original_render_offsets = grid._render_offsets
    reentry_attempts = 0

    def render_offsets_with_reentry():
        nonlocal reentry_attempts
        reentry_attempts += 1
        grid._on_instructions_changed()
        original_render_offsets()

    monkeypatch.setattr(grid, "_render_offsets", render_offsets_with_reentry)
    grid.instructions.setPlainText("target: nop\naddiu $v0, $zero, 1")
    _app().processEvents()

    assert reentry_attempts == 1
    assert grid.instructions.toPlainText() == "target: nop\nADDIU $v0, $zero, 1"


def test_binary_workbench_local_and_global_symbols_have_separate_ownership(
    tmp_path: Path,
):
    first = tmp_path / "first.asm"
    second = tmp_path / "second.asm"
    first.write_text("addiu $v0, $zero, @global_value\n", encoding="utf-8")
    second.write_text("addiu $v1, $zero, @global_value\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(first)
    tool.tabs.set_current_symbols({"local_value": "0x10"}, {}, {})
    tool.tabs.set_global_symbols({"global_value": "0x20"})
    first_context = tool.tabs.current_context()

    assert first_context.symbols == {"local_value": "0x10"}
    assert first_context.variables == {
        "global_value": "0x20",
        "local_value": "0x10",
    }
    assert first_context.equates == first_context.variables
    first_editor = tool.tabs.currentWidget().grid.instructions  # type: ignore[attr-defined]
    assert first_editor._candidates_for_prefix("@g") == ["@global_value"]
    assert first_editor._candidates_for_prefix("@l") == ["@local_value"]
    assert first_editor._symbol_tooltips["@global_value"].endswith("0x20")
    first_grid = tool.tabs.currentWidget().grid  # type: ignore[attr-defined]
    assert first_grid._instruction_highlighter._equates["@global_value"] == "0x20"

    local_only_context = BinaryWorkbenchTabContextDTO(
        **{
            **first_context.__dict__,
            "variables": dict(first_context.symbols),
            "equates": dict(first_context.symbols),
        }
    )
    reloaded_context = tool.tabs._with_symbol_offsets(local_only_context)
    assert reloaded_context.symbols == {"local_value": "0x10"}
    assert reloaded_context.variables == first_context.variables
    assert reloaded_context.rows[0].bytes_text == "20 00 02 24"
    assert tool.tabs.symbol_offsets_for(
        reloaded_context.tab_id,
        "global_value",
    ) == ["0x00000000"]

    tool.open_assembly_path(second)
    second_context = tool.tabs.current_context()
    assert second_context.symbols == {}
    assert second_context.variables == {"global_value": "0x20"}
    assert second_context.rows[0].bytes_text == "20 00 03 24"

    tool.tabs.set_current_symbols({"second_local": "0x30"}, {}, {})
    tool.tabs.setCurrentIndex(0)
    _app().processEvents()
    first_context = tool.tabs.current_context()
    assert first_context.symbols == {"local_value": "0x10"}
    assert "second_local" not in first_context.variables
    assert "global_value" not in first_context.symbols
    payload = binary_workbench_state_to_payload(tool.export_state())
    first_stored = tool.export_state().tabs[0]
    if first_stored.module_paths.get("symbols"):
        assert payload["tabs"][0]["symbols"] == {}
    else:
        assert payload["tabs"][0]["symbols"] == {"local_value": "0x10"}
    assert "global_value" not in payload["tabs"][0]["symbols"]
    assert payload["global_symbols"] == {"global_value": "0x20"}

    restored = binary_workbench_state_from_payload(payload)
    assert restored.global_symbols == {"global_value": "0x20"}


def test_definition_only_symbols_refresh_the_active_viewport_without_global_work(
    tmp_path: Path,
    monkeypatch,
):
    """Resolve newly added local/global Symbols already visible on screen."""

    assembly = tmp_path / "visible-symbols.asm"
    assembly.write_text(
        "ori $t0, $zero, _visible_local\n"
        "ori $t1, $zero, @visible_global\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly)
    page = tool.tabs.currentWidget()
    page.show()
    _app().processEvents()
    coordinator = page.grid._consistency_coordinator
    semantic_schedules: list[dict[str, object]] = []
    monkeypatch.setattr(
        coordinator,
        "_schedule_semantic",
        lambda **kwargs: semantic_schedules.append(kwargs),
    )

    tool.tabs.set_current_symbols(
        {"visible_local": "0x20"}, {}, {}, apply_existing=False
    )
    tool.tabs.set_global_symbols(
        {"visible_global": "0x30"}, apply_existing=False
    )
    _app().processEvents()

    assert page.grid._rows[0].bytes_text == "20 00 08 34"
    assert page.grid._rows[1].bytes_text == "30 00 09 34"
    assert semantic_schedules == []


def test_binary_workbench_closing_symbols_dialog_commits_direct_cell_edits(
    tmp_path: Path,
    monkeypatch,
):
    assembly_path = tmp_path / "symbols.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)

    def edit_and_close(dialog):
        value_index = dialog.symbols_model.index(0, dialog.symbols_model.VALUE_COLUMN)
        dialog.symbols_model.setData(value_index, "0x40")
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(BinaryWorkbenchSymbolsDialog, "exec", edit_and_close)
    tool.tabs.set_current_symbols({"local_symbol": "0x20"}, {}, {})
    tool._open_local_symbols()

    assert tool.tabs.local_symbols() == {"local_symbol": "0x40"}

    tool.tabs.set_global_symbols({"global_symbol": "0x20"})
    tool._open_global_symbols()

    assert tool.tabs.global_symbols() == {"global_symbol": "0x40"}


def test_binary_workbench_global_symbols_emit_and_persist_on_add_load_and_save(tmp_path: Path):
    source = tmp_path / "globals.json"
    source.write_text(
        json.dumps({"name": "globals", "symbols": {"loaded": "0x20"}}),
        encoding="utf-8",
    )
    target = tmp_path / "saved-globals.json"
    dialog = BinaryWorkbenchSymbolsDialog({}, {}, {}, default_directory=str(tmp_path))
    changes: list[dict[str, str]] = []
    dialog.symbolsChanged.connect(lambda symbols: changes.append(dict(symbols)))

    dialog.name.setText("created")
    dialog.value.setText("0x10")
    dialog._append_from_entry()
    assert changes[-1] == {"created": "0x10"}

    assert dialog.load_library_json(source) is True
    assert changes[-1] == {"created": "0x10", "loaded": "0x20"}

    assert dialog.save_library_json(target) is True
    assert changes[-1] == {"created": "0x10", "loaded": "0x20"}
    assert json.loads(target.read_text(encoding="utf-8"))["symbols"] == changes[-1]


def test_binary_workbench_reopens_linked_global_symbols_after_blank_project(
    tmp_path: Path,
    monkeypatch,
):
    source = tmp_path / "linked.asm"
    source.write_text("ori $t0, $zero, @shared\n", encoding="utf-8")
    external = tmp_path / "outside" / "shared.json"
    external.parent.mkdir()
    external.write_text(
        json.dumps({"name": "shared", "symbols": {"shared": "0x20"}}),
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(source)

    def load_and_close(dialog):
        assert dialog.load_library_json(external) is True
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(BinaryWorkbenchSymbolsDialog, "exec", load_and_close)
    tool._open_global_symbols()
    canonical = Path(tool.tabs.global_symbols_library_path())
    linked = tool.tabs.current_metadata_context()

    assert canonical.parent.name == "Global Symbols"
    assert linked is not None
    assert linked.module_paths[GLOBAL_SYMBOLS] == str(canonical)

    tool.tabs.load_state(BinaryWorkbenchStateDTO())
    assert tool.tabs.global_symbols() == {}
    tool.open_assembly_path(source)

    restored = tool.tabs.current_context()
    assert tool.tabs.global_symbols() == {"shared": "0x20"}
    assert restored is not None
    assert restored.variables["shared"] == "0x20"
    assert restored.module_paths[GLOBAL_SYMBOLS] == str(canonical)


def test_binary_workbench_first_tab_global_symbols_link_wins(tmp_path: Path):
    first_library = tmp_path / "first.json"
    second_library = tmp_path / "second.json"
    first_library.write_text(
        json.dumps({"name": "first", "symbols": {"first": "0x10"}}),
        encoding="utf-8",
    )
    second_library.write_text(
        json.dumps({"name": "second", "symbols": {"second": "0x20"}}),
        encoding="utf-8",
    )
    state = BinaryWorkbenchStateDTO(
        tabs=[
            BinaryWorkbenchTabContextDTO(
                tab_id="first",
                kind="scratch",
                display_name="first.asm",
                module_paths={GLOBAL_SYMBOLS: str(first_library)},
            ),
            BinaryWorkbenchTabContextDTO(
                tab_id="second",
                kind="scratch",
                display_name="second.asm",
                module_paths={GLOBAL_SYMBOLS: str(second_library)},
            ),
        ],
        active_tab_id="second",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.load_state(state)

    assert tool.tabs.global_symbols_library_path() == str(first_library)
    assert tool.tabs.global_symbols() == {"first": "0x10"}


def test_binary_workbench_lazy_local_payload_still_receives_global_symbols(tmp_path: Path):
    """Global lookup remains available without materializing lazy Local Symbols."""

    global_library = tmp_path / "globals.json"
    global_library.write_text(
        json.dumps({"name": "globals", "symbols": {"shared": "0x20"}}),
        encoding="utf-8",
    )
    state = BinaryWorkbenchStateDTO(
        tabs=[BinaryWorkbenchTabContextDTO(
            tab_id="lazy",
            kind="scratch",
            display_name="lazy.asm",
            module_paths={GLOBAL_SYMBOLS: str(global_library)},
            lazy_symbol_payload={"symbols": {"local": "0x10"}},
            symbol_migration_pending=True,
        )],
        active_tab_id="lazy",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.load_state(state)
    restored = tool.tabs.current_context()

    assert restored is not None
    assert restored.variables["shared"] == "0x20"
    assert tool.tabs.global_symbols() == {"shared": "0x20"}


def _version_row_payload(offset: str, instruction: str, bytes_text: str) -> dict[str, object]:
    return {
        "offset": offset,
        "offsets": {"File": offset},
        "instruction": instruction,
        "bytes_text": bytes_text,
        "original_instruction": instruction,
        "original_bytes_text": bytes_text,
    }


def test_binary_workbench_instruction_block_paste_blocks_multiline_clipboard_into_single_line():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("nop\nnop\nnop")
    warnings: list[str] = []
    editor.navigationWarningRequested.connect(warnings.append)
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.setPosition(len("nop"), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    app.clipboard().setText("addiu $a0, $zero, 0x1\naddiu $a1, $zero, 0x2")

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText().splitlines() == ["nop", "nop", "nop"]
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_MULTILINE_PASTE_LINE_MISMATCH]


def test_binary_workbench_instruction_multicursor_paste_maps_clipboard_lines_once():
    app = _app()
    editor = WorkbenchEditor()
    editor.setObjectName("binary-workbench-instructions-panel")
    editor.setPlainText("nop\nnop\nnop\nnop")
    ranges = []
    for index in range(4):
        block = editor.document().findBlockByNumber(index)
        ranges.append((block.position(), block.position() + len(block.text())))
    editor._occurrence_ranges = ranges
    editor._occurrence_query = "nop"
    editor._apply_occurrence_selection(ranges[-1])
    app.clipboard().setText(
        "addiu $a0, $zero, 0x1\n"
        "addiu $a1, $zero, 0x2\n"
        "addiu $a2, $zero, 0x3\n"
        "addiu $a3, $zero, 0x4"
    )

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_V, Qt.ControlModifier))

    assert editor.toPlainText().splitlines() == [
        "addiu $a0, $zero, 0x1",
        "addiu $a1, $zero, 0x2",
        "addiu $a2, $zero, 0x3",
        "addiu $a3, $zero, 0x4",
    ]


def test_binary_workbench_shift_enter_adds_comment_in_binary_with_byte_shift_enabled(tmp_path: Path):
    binary_path = tmp_path / "comments.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 8)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.EndOfBlock)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.ShiftModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines()[1] == "; "


def test_binary_workbench_binary_comment_line_survives_visible_reload(tmp_path: Path):
    binary_path = tmp_path / "comments.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 32)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    editor = page.grid.instructions  # type: ignore[attr-defined]
    lines = editor.toPlainText().splitlines()
    lines.insert(1, "; keep this comment")
    editor.setPlainText("\n".join(lines))
    _app().processEvents()
    page.grid.flush_pending_rows_changed()  # type: ignore[attr-defined]
    current = page.current_context()
    active = next(version for version in current.versions if version.name == current.active_version_name)

    assert active.instructions_by_line.get(1) == "; keep this comment"

    page._load_visible_rows(0, page.grid.visible_size(), 1)  # type: ignore[attr-defined]

    assert page.grid.instructions.toPlainText().splitlines()[1] == "; keep this comment"  # type: ignore[attr-defined]


def test_binary_workbench_binary_byte_shift_comment_extra_keeps_original_offsets(tmp_path: Path):
    binary_path = tmp_path / "offsets.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 8)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.EndOfBlock)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.ShiftModifier))
    _app().processEvents()

    offsets = [line.strip() for line in page.grid._offset_editors["File"].toPlainText().splitlines()]  # type: ignore[attr-defined]
    assert offsets[:3] == [
        "0x00000000",
        "-",
        "0x00000004",
    ]
    assert page.grid._total_size == binary_path.stat().st_size  # type: ignore[attr-defined]


def test_binary_workbench_binary_byte_shift_valid_extra_gets_offset(tmp_path: Path):
    binary_path = tmp_path / "offsets.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 8)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    lines = editor.toPlainText().splitlines()
    lines.insert(1, "addiu $a0, $zero, 0x1")
    editor.setPlainText("\n".join(lines))
    _app().processEvents()

    offsets = [line.strip() for line in page.grid._offset_editors["File"].toPlainText().splitlines()]  # type: ignore[attr-defined]
    assert offsets[:3] == ["0x00000000", "0x00000004", "0x00000008"]


def test_binary_workbench_appended_final_nop_stays_visible_after_scroll(tmp_path: Path):
    binary_path = tmp_path / "final_nop.bin"
    binary_path.write_bytes(bytes.fromhex("00 00 00 00") * 109)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.set_visible_offset(grid.scrollbar.maximum())
    _app().processEvents()
    editor = grid.instructions
    editor.setPlainText(f"{editor.toPlainText()}\nnop")
    _app().processEvents()
    grid.flush_pending_rows_changed()
    grid.set_visible_offset(grid.scrollbar.maximum())
    _app().processEvents()

    current = page.current_context()
    active = next(version for version in current.versions if version.name == current.active_version_name)
    assert current.file_size == 440
    assert any(row.offsets.get("File") == "0x000001B4" for row in active.rows)
    assert grid._rows[-1].offsets["File"] == "0x000001B4"
    assert grid._rows[-1].bytes_text == "00 00 00 00"
    assert grid.raw_instructions.toPlainText().splitlines()[-1].lower() == "nop"
    assert grid.instructions.toPlainText().splitlines()[-1].lower() == "nop"

    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    editor.setPlainText("\n".join(editor.toPlainText().splitlines()[:-1]))
    _app().processEvents()
    grid.flush_pending_rows_changed()

    current = page.current_context()
    assert current.file_size == 436
    assert "0x000001B4" not in current.byte_overlays
    assert "0x000001B4" not in current.instruction_overlays


def test_binary_workbench_assembly_no_byte_shift_extra_line_never_gets_offset(tmp_path: Path):
    assembly_path = tmp_path / "offsets.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("nop\naddiu $a0, $zero, 0x1\nnop")
    _app().processEvents()

    offsets = [line.strip() for line in page.grid._offset_editors["File"].toPlainText().splitlines()]  # type: ignore[attr-defined]
    assert offsets == ["0x00000000", "-", "0x00000004"]
    assert page.grid.bytes.toPlainText().splitlines()[1] == ""  # type: ignore[attr-defined]


def test_binary_workbench_assembly_no_byte_shift_backspace_deletes_invalid_offset_line(tmp_path: Path):
    assembly_path = tmp_path / "locked_delete.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("nop\n; extra\nnop")
    _app().processEvents()
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position())
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == ["nop", "nop"]


def test_binary_workbench_assembly_no_byte_shift_delete_deletes_invalid_offset_line(tmp_path: Path):
    assembly_path = tmp_path / "locked_delete.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("nop\n; extra\nnop")
    _app().processEvents()
    block = editor.document().findBlockByNumber(0)
    cursor = editor.textCursor()
    cursor.setPosition(block.position() + len(block.text()))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == ["nop", "nop"]


def test_binary_workbench_assembly_no_byte_shift_selection_clears_only_content(tmp_path: Path):
    assembly_path = tmp_path / "locked_selection.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    editor.setPlainText("nop\n; extra\nnop")
    _app().processEvents()
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position())
    cursor.setPosition(editor.document().findBlockByNumber(2).position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == ["nop", "", "nop"]


def test_binary_workbench_assembly_no_byte_shift_backspace_preserves_valid_offset_line(tmp_path: Path):
    assembly_path = tmp_path / "locked_valid.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position())
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == ["nop", "nop"]


def test_binary_workbench_assembly_no_byte_shift_delete_preserves_valid_offset_line(tmp_path: Path):
    assembly_path = tmp_path / "locked_valid.asm"
    assembly_path.write_text("nop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=False))  # type: ignore[attr-defined]
    editor = page.grid.instructions  # type: ignore[attr-defined]
    block = editor.document().findBlockByNumber(0)
    cursor = editor.textCursor()
    cursor.setPosition(block.position() + len(block.text()))
    editor.setTextCursor(cursor)

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier))
    _app().processEvents()

    assert editor.toPlainText().splitlines() == ["nop", "nop"]


def test_binary_workbench_alt_g_action_returns_to_clicked_jump_origin(tmp_path: Path):
    assembly_path = tmp_path / "jump_history.asm"
    assembly_path.write_text("nop\nnop\nnop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.go_to_instruction_offset(4)  # type: ignore[attr-defined]
    assert page._jump_return_history_by_version == {}  # type: ignore[attr-defined]

    page.go_to_clicked_instruction_offset(8, 0)  # type: ignore[attr-defined]
    history_key = page._jump_return_history_key()  # type: ignore[attr-defined]
    assert page._jump_return_history_by_version[history_key] == [0]  # type: ignore[attr-defined]

    tool._return_jump_action.trigger()  # type: ignore[attr-defined]
    _app().processEvents()

    assert page._jump_return_history_by_version[history_key] == []  # type: ignore[attr-defined]
    assert page.grid.instructions.textCursor().blockNumber() == 0  # type: ignore[attr-defined]


def test_binary_workbench_jump_return_history_is_limited_and_version_scoped(tmp_path: Path):
    assembly_path = tmp_path / "jump_history_versions.asm"
    assembly_path.write_text("nop\n" * 64, encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    current = page.current_context()  # type: ignore[attr-defined]
    page.replace_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, "active_version_name": "v1"}))  # type: ignore[attr-defined]

    for index in range(55):
        page.go_to_clicked_instruction_offset(8, index * 4)  # type: ignore[attr-defined]

    v1_history = page._jump_return_history_by_version["v1"]  # type: ignore[attr-defined]
    assert len(v1_history) == 50
    assert v1_history[0] == 20
    assert v1_history[-1] == 216

    current = page.current_context()  # type: ignore[attr-defined]
    page.replace_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, "active_version_name": "v2"}))  # type: ignore[attr-defined]
    page.go_to_clicked_instruction_offset(8, 4)  # type: ignore[attr-defined]

    assert page._jump_return_history_by_version["v2"] == [4]  # type: ignore[attr-defined]
    assert page.return_to_previous_jump_offset() is True  # type: ignore[attr-defined]
    assert page._jump_return_history_by_version["v2"] == []  # type: ignore[attr-defined]
    assert page._jump_return_history_by_version["v1"][-1] == 216  # type: ignore[attr-defined]


def test_binary_workbench_hazards_window_uses_find_fields_and_navigates(tmp_path: Path):
    assembly_path = tmp_path / "hazards.asm"
    assembly_path.write_text(
        "lw $v0, 0x10($sp)\n"
        "addiu $a0, $v0, 0x1\n"
        "j 0x00000010\n"
        "jal 0x00000014\n"
        "nop\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    assert [(item.offset, item.instruction.lower()) for item in tool.tabs.refresh_hazards(0, 20)] == [
        (4, "addiu $a0, $v0, 0x1"),
        (12, "jal 0x00000014"),
    ]

    tool.show()
    tool.activateWindow()
    tool.setFocus()
    QTest.keyClick(tool, Qt.Key_H, Qt.AltModifier)
    _app().processEvents()
    hazards_window = tool._hazards_window
    assert hazards_window is not None
    assert hazards_window.findChild(QLabel, "preferences-title") is None
    assert hazards_window.findChild(QComboBox) is None
    assert all(editor.placeholderText() != BINARY_WORKBENCH_TEXT.VALUE for editor in hazards_window.findChildren(QLineEdit))
    assert tool.toolbar.hazards_action.shortcut().toString() == "Alt+H"
    buttons = {button.text(): button for button in hazards_window.findChildren(QPushButton)}
    assert set(buttons) == {BINARY_WORKBENCH_TEXT.CANCEL, BINARY_WORKBENCH_TEXT.FIND_HAZARDS}
    assert "OK" not in buttons
    assert buttons[BINARY_WORKBENCH_TEXT.FIND_HAZARDS].mapTo(hazards_window, QPoint()).x() < buttons[
        BINARY_WORKBENCH_TEXT.CANCEL
    ].mapTo(hazards_window, QPoint()).x()
    assert hazards_window.start.placeholderText() == BINARY_WORKBENCH_TEXT.START_OFFSET
    assert hazards_window.end.placeholderText() == BINARY_WORKBENCH_TEXT.END_OFFSET
    assert hazards_window.length.placeholderText() == BINARY_WORKBENCH_TEXT.FIND_LENGTH
    assert hazards_window.results.count() == 2
    assert hazards_window.results.item(0).text().lower() == "0x00000004    addiu $a0, $v0, 0x1"

    requested_offsets: list[int] = []
    hazards_window.goToRequested.connect(requested_offsets.append)
    hazards_window.results.itemClicked.emit(hazards_window.results.item(0))
    _app().processEvents()

    assert requested_offsets == [4]
    assert hazards_window.isVisible()


def test_binary_workbench_hazards_search_range_limit_and_cache_persist(tmp_path: Path):
    assembly_path = tmp_path / "hazards_cache.asm"
    assembly_path.write_text(
        "lw $v0, 0x10($sp)\n"
        "addiu $a0, $v0, 0x1\n"
        "nop\n"
        "lw $a1, 0x20($sp)\n"
        "addiu $a2, $a1, 0x2\n",
        encoding="utf-8",
    )
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    tool.show()
    tool.activateWindow()
    tool.setFocus()
    QTest.keyClick(tool, Qt.Key_H, Qt.AltModifier)
    _app().processEvents()
    hazards_window = tool._hazards_window
    assert hazards_window is not None
    hazards_window.start.setText("0x00000000")
    hazards_window.length.setText(str(BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_KB + 1))
    hazards_window.refresh_results()

    cache_path = tmp_path / "data" / "binary_workbench" / "hazard_cache.json"
    payload = json.loads(cache_path.read_text(encoding="utf-8"))

    assert hazards_window.length.text() == str(BINARY_WORKBENCH_HAZARDS_MAX_LENGTH_KB)
    assert [item["offset"] for item in payload["entries"][0]["items"]] == [
        "0x00000004",
        "0x00000010",
    ]

    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText(  # type: ignore[attr-defined]
        "lw $v0, 0x10($sp)\n"
        "nop\n"
        "nop\n"
        "lw $a1, 0x20($sp)\n"
        "addiu $a2, $a1, 0x2"
    )
    _app().processEvents()
    hazards_window.end.setText("0x00000008")
    hazards_window.length.setText("")
    hazards_window.refresh_results()
    payload = json.loads(cache_path.read_text(encoding="utf-8"))

    assert [item["offset"] for item in payload["entries"][0]["items"]] == ["0x00000010"]
