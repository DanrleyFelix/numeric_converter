import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMessageBox, QPushButton, QComboBox, QDialog, QLineEdit, QMenu, QPlainTextEdit, QScrollBar, QTabBar, QToolButton, QWidget

from src.main import create_main_window
from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchLbaFilesystemDTO,
    BinaryWorkbenchMemoryRegionDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
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
from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.binary_workbench.editor import (
    page_immediate_symbols as page_immediate_symbols_module,
)
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchLbaFilesystemDialog,
    BinaryWorkbenchMemoryRegionsDialog,
    BinaryWorkbenchVersionActionsDialog,
    BinaryWorkbenchVersionChangeDialog,
)
from src.presentation.ui.components.binary_workbench.native_dialogs import _map_windows_response
from src.presentation.ui.components.binary_workbench.search import BinaryWorkbenchGoToDialog


_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _window(root: Path | None = None):
    _app()
    return create_main_window(root or Path(tempfile.mkdtemp()))


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

    assert [button.text() for button in version_buttons] == ["v2 test", "v1_test_2"]
    assert version_buttons[1].objectName() == "binary-workbench-version-active"
    assert all(button.focusPolicy() == Qt.NoFocus for button in version_buttons)
    assert all(button.cursor().shape() == Qt.PointingHandCursor for button in version_buttons)


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
    assert [version.name for version in current.versions] == ["new_b", "new_a"]
    assert current.active_version_name == "new_b"
    assert current.module_paths["versions"] == str(versions_path)
    assert "version:old_a" not in current.module_paths
    assert "version:new_b" in current.module_paths


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
    page.grid.bytes.setPlainText("AABBCCDD\n1122\n00 00 00 00")  # type: ignore[attr-defined]
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert page.grid.bytes.toPlainText().splitlines()[0] == "AA BB CC DD"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[1] == "11 22 "  # type: ignore[attr-defined]
    assert current.rows[1].offsets["File"] == "-"
    assert current.rows[1].instruction == ""
    assert page.grid.raw_instructions.toPlainText().splitlines()[1] == ""  # type: ignore[attr-defined]

    page.grid.bytes.setPlainText("AA BB CC DD\n1122334455\n00 00 00 00")  # type: ignore[attr-defined]
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert page.grid.bytes.toPlainText().splitlines()[0] == "AA BB CC DD"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[1] == "11 22 33 44"  # type: ignore[attr-defined]
    assert current.rows[1].offsets["File"] == "0x00000004"
    assert current.rows[1].instruction != "; comment"
    assert current.byte_overlays["0x00000000"] == "AA BB CC DD"
    assert page.grid._offset_editors["File"].toPlainText().splitlines()[1].strip() == "0x00000004"  # type: ignore[attr-defined]
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
    close_button = tool.tabs.tabBar().tabButton(0, QTabBar.RightSide)
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
    surface.bytes.setPlainText("F4 01 63 24")
    _app().processEvents()
    instruction = surface.instructions.toPlainText().splitlines()[0]
    raw_instruction = surface.raw_instructions.toPlainText().splitlines()[0]

    assert instruction.startswith("ADDIU")
    assert "0x1F4" in instruction
    assert raw_instruction.startswith("addiu")
    assert "0x1f4" in raw_instruction


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


def test_binary_workbench_add_equate_replaces_immediate_text(tmp_path: Path, monkeypatch):
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
        BINARY_WORKBENCH_TEXT.EQUATE_TARGET,
        "0x71",
        start,
        start + len("0x71"),
    )
    current = tool.tabs.current_context()

    assert current is not None
    assert current.equates == {"card_id": "0x71"}
    assert page.grid.instructions.toPlainText() == "ADDIU $t1,$zero,@card_id"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText() == "71 00 09 24"  # type: ignore[attr-defined]


def test_binary_workbench_add_variable_replaces_memory_operand(tmp_path: Path, monkeypatch):
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
        BINARY_WORKBENCH_TEXT.VARIABLE_TARGET,
        "0x2CD($gp)",
        start,
        start + len("0x2CD($gp)"),
    )
    current = tool.tabs.current_context()

    assert current is not None
    assert current.variables == {"actor_hp": "0x2CD($gp)"}
    assert page.grid.instructions.toPlainText() == "LW $v0, _actor_hp"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText() == "CD 02 82 8F"  # type: ignore[attr-defined]


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


def test_binary_workbench_raw_instructions_mark_hazards(tmp_path: Path):
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
    assert len(page.grid.raw_instructions.extraSelections()) == 2  # type: ignore[attr-defined]


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

    assert len(tool.tabs.tabText(0)) <= 24
    assert tool.tabs.tabBar().tabToolTip(0) == path.name


def test_binary_workbench_symbols_dialog_tolerates_non_string_values(tmp_path: Path):
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"flag": True}, {"base": 2048}, {"loop": "0x8000"})

    assert dialog.values()[0]["flag"] == "True"
    assert dialog.values()[1]["base"] == "2048"


def test_binary_workbench_ignores_semicolon_comments_when_loading_assembly(tmp_path: Path):
    assembly_path = tmp_path / "hook.asm"
    assembly_path.write_text(
        "; 675 = 0x02A3\n"
        "; hook 1 em 0x8001b590\n"
        "jal    0x1D9200 ; call SPELL\n"
        "; VERSÃO ENCURTADA\n"
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
        "jal 0x1d9200",
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
    assert all(value.strip() == "-" for value in empty_offsets)
    assert all(value.startswith(" ") for value in empty_offsets)


def test_binary_workbench_opens_internal_file_from_configured_lba(tmp_path: Path):
    source = bytearray(2352)
    source[24:28] = bytes.fromhex("AA BB CC DD")
    binary_path = tmp_path / "disc.bin"
    binary_path.write_bytes(source)
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_binary_path(binary_path)
    tool.tabs.set_current_internal_files([BinaryWorkbenchInternalFileDTO(name="slus", start_lba=0)])
    tool.tabs.open_internal_tab("slus")
    state = tool.export_state()

    assert tool.tabs.count() == 2
    assert state.tabs[-1].kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL
    assert state.tabs[-1].display_name == "slus"
    assert state.tabs[-1].rows[0].offsets["File"] == "0x00000000"
    assert state.tabs[-1].rows[0].bytes_text == "AA BB CC DD"


def test_binary_workbench_lba_filesystem_allows_non_binary_file_backed_tabs(tmp_path: Path):
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

    assert state.tabs[-1].kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL
    assert state.tabs[-1].display_name == "chunk"
    assert state.tabs[-1].rows[0].bytes_text == "AA BB CC DD"


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

    version_path = tmp_path / "data" / "binary_workbench" / "workspaces" / "Versions" / "source_bin_workspace_manifest_versions.json"
    payload = version_path.read_text(encoding="utf-8")
    assert '"0"' in payload
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
    assert "ADDIU $sp,$sp,-0x10" in output_path.read_text(encoding="utf-8")
    assert (tmp_path / "data" / "binary_workbench" / "workspaces" / "closed_asm_workspace_manifest.json").exists()


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
    assert page.grid.scrollbar.value() == 0x22  # type: ignore[attr-defined]


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
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    before = page.grid.scrollbar.value()  # type: ignore[attr-defined]
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Down, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(editor, event)
    _app().processEvents()

    assert page.grid.scrollbar.value() > before  # type: ignore[attr-defined]
    assert editor.textCursor().blockNumber() == editor.document().blockCount() - 1


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

    assert "Length: 2 bytes" in page.summary.text()  # type: ignore[attr-defined]


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

    assert "Length: 256 bytes" in page.summary.text()  # type: ignore[attr-defined]


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
    assert copied == ["NOP"] * 57


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


def test_binary_workbench_find_decoded_text_ansi_respects_offset_range(tmp_path: Path):
    binary_path = tmp_path / "decoded.bin"
    binary_path.write_bytes(bytes.fromhex("00 48 45 4C 4C 4F 00 E7 E3 6F 00"))
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_file_path(binary_path)

    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "HELLO") == [1]
    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "ção") == [7]
    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "HELLO", end_offset=5) == [1]
    assert tool.tabs.find_offsets(BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT, "HELLO", start_offset=2) == []


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


def test_binary_workbench_save_current_assembly_source_uses_assembly_status(tmp_path: Path):
    assembly_path = tmp_path / "call_umi.asm"
    assembly_path.write_text("nop\n", encoding="utf-8")
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.open_assembly_path(assembly_path)
    page = tool.tabs.currentWidget()
    page.grid.instructions.setPlainText("jal 0x80010000")  # type: ignore[attr-defined]
    _app().processEvents()
    tool._save_current_tab()

    assert assembly_path.read_text(encoding="utf-8") == "JAL 0x80010000"
    assert tool.footer_status.text() == 'Saved assembly/code file "call_umi.asm".'


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

    assert "Length: 5120 bytes" in page.summary.text()  # type: ignore[attr-defined]


def test_binary_workbench_symbols_rows_keep_variable_equate_dropdown():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog(
        {"var": "20"},
        {},
        {},
        symbol_offsets={"var": ["0x00000000", "0x0000000C"]},
    )
    combos = dialog.findChildren(QComboBox, "binary-workbench-dialog-input")
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}

    assert len(combos) >= 2
    assert [combos[-1].itemText(index) for index in range(combos[-1].count())] == ["Variable", "Equate"]
    assert BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS in buttons
    variables, _, labels = dialog.values()

    assert variables == {"var": "20"}
    assert labels == {}


def test_binary_workbench_symbol_offsets_dialog_lists_offsets():
    _app()
    dialog = BinaryWorkbenchSymbolOffsetsDialog(
        "var",
        ["0x00000000", "0x0000000C"],
    )

    assert [dialog.offsets.item(index).text() for index in range(dialog.offsets.count())] == [
        "0x00000000",
        "0x0000000C",
    ]


def test_binary_workbench_symbols_inputs_are_aligned_and_symmetric():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"var": "20"}, {}, {"label_1": "0x34"})
    dialog.show()
    _app().processEvents()
    combos = dialog.findChildren(QComboBox, "binary-workbench-dialog-input")
    fields = dialog.findChildren(QLineEdit, "binary-workbench-dialog-input")
    add_button = dialog.findChildren(QPushButton, "preferences-ok")[0]
    first_row_fields = fields[-2:]

    assert fields[0].width() == 158
    assert fields[1].width() == 158
    assert dialog.minimumWidth() == 680
    assert dialog.width() == 760
    assert {combo.width() for combo in combos} == {132}
    assert {field.width() for field in fields[2:]} == {132}
    assert {combo.height() for combo in combos} == {46}
    assert {field.height() for field in fields} == {46}
    assert add_button.width() == BINARY_WORKBENCH_LAYOUT.SYMBOL_ADD_ACTION_WIDTH
    assert combos[1].mapTo(dialog, QPoint()).x() == combos[0].mapTo(dialog, QPoint()).x()
    assert first_row_fields[0].mapTo(dialog, QPoint()).x() == fields[2].mapTo(dialog, QPoint()).x()
    assert first_row_fields[1].mapTo(dialog, QPoint()).x() == fields[3].mapTo(dialog, QPoint()).x()
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    assert buttons["OK"].mapTo(dialog, QPoint()).x() - buttons["Save"].mapTo(dialog, QPoint()).x() < 190


def test_binary_workbench_labels_dialog_filters_and_navigates():
    _app()
    dialog = BinaryWorkbenchLabelsDialog({"loop": "0x00000008", "exit": "0x00000020"})
    selected: list[int] = []
    dialog.goToRequested.connect(selected.append)
    dialog.filter_input.setText("loop")
    _app().processEvents()
    buttons = [button for button in dialog.findChildren(QPushButton) if button.text() == BINARY_WORKBENCH_TEXT.GO_TO]

    assert len([row for row, _, _ in dialog._rows if not row.isHidden()]) == 1
    buttons[0].click()

    assert selected == [0x8]


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


def test_binary_workbench_lba_filesystem_uses_editable_rows():
    _app()
    dialog = BinaryWorkbenchLbaFilesystemDialog([BinaryWorkbenchInternalFileDTO("SLUS", 24)])
    dialog.show()
    _app().processEvents()
    fields = dialog.findChildren(QLineEdit, "binary-workbench-dialog-input")
    combos = dialog.findChildren(QComboBox, "binary-workbench-dialog-input")
    body = dialog.findChild(QWidget, "workspace-table-body")
    rows = dialog.findChildren(QWidget, "workspace-row")
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}

    assert len(fields) == 5
    assert dialog.minimumWidth() == 760
    assert dialog.width() == 820
    assert body is not None
    assert rows
    assert fields[0].width() == 288
    assert {field.width() for field in fields[1:]} == {240}
    assert {combo.width() for combo in combos} == {240}
    assert {field.height() for field in fields} == {46}
    assert buttons["Load"].mapTo(dialog, QPoint()).y() == buttons["Save"].mapTo(dialog, QPoint()).y()
    assert buttons["Load"].mapTo(dialog, QPoint()).y() == buttons["OK"].mapTo(dialog, QPoint()).y()
    assert buttons["OK"].mapTo(dialog, QPoint()).x() - buttons["Save"].mapTo(dialog, QPoint()).x() < 190
    assert fields[3].mapTo(dialog, QPoint()).x() == fields[1].mapTo(dialog, QPoint()).x()
    assert fields[4].mapTo(dialog, QPoint()).x() == fields[2].mapTo(dialog, QPoint()).x()
    fields[3].setText("WA_MRG.MRG")
    fields[4].setText("10010")
    mappings = dialog.mappings()

    assert mappings[0].name == "WA_MRG.MRG"
    assert mappings[0].start_lba == 10010


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


def test_binary_workbench_memory_regions_dialog_saves_decimal_offsets(tmp_path: Path):
    _app()
    library_path = tmp_path / "regions.json"
    dialog = BinaryWorkbenchMemoryRegionsDialog(
        [BinaryWorkbenchMemoryRegionDTO("SLUS code", 0x1C2400, 0x1C24FF)]
    )

    assert dialog.save_json(library_path) is True

    payload = library_path.read_text(encoding="utf-8")
    assert '"start_offset": 1844224' in payload
    assert '"end_offset": 1844479' in payload
    assert dialog.load_json(library_path) is True
    assert dialog.regions() == [
        BinaryWorkbenchMemoryRegionDTO("SLUS code", 0x1C2400, 0x1C24FF)
    ]


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
        "label1: add $v1, $v0, _variable1\n"
        "add $v1, $v0, @equate1\n"
        "j label1\n"
        "add $v1, $v0, _variable1\n",
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
    assert current.symbol_offsets["variable1"] == ["0x00000000", "0x0000000C"]
    assert current.symbol_offsets["equate1"] == ["0x00000004"]
    dialog = BinaryWorkbenchGoToDialog(current)
    dialog.target.setCurrentText(BINARY_WORKBENCH_TEXT.VARIABLE_TARGET)
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
    dialog = BinaryWorkbenchSymbolsDialog({}, {}, {})

    assert dialog.load_library_json(library_path) is True

    assert dialog.values() == (
        {"variable1": "20"},
        {"equate1": "0x34"},
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
    assert '"label1": "0x00000000"' not in payload


def test_binary_workbench_symbol_completion_starts_from_prefix_markers():
    _app()
    editor = WorkbenchEditor()
    editor.set_symbol_helpers({"label1": "0x0"}, {"variable1": "20"}, {"equate1": "0x34"})
    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Underscore, Qt.NoModifier, "_"))

    assert editor._current_completion_prefix() == "_"
    assert editor._completion_model.stringList() == ["_variable1"]
    assert editor._candidates_for_prefix("_") == ["_variable1"]
    assert editor._candidates_for_prefix("_VAR") == ["_variable1"]
    assert editor._candidates_for_prefix("@") == ["@equate1"]
    assert editor._candidates_for_prefix("@EQU") == ["@equate1"]


def test_binary_workbench_symbol_completion_popup_selects_first_match():
    app = _app()
    editor = WorkbenchEditor()
    editor.resize(320, 120)
    editor.show()
    editor.set_symbol_helpers({}, {"variable1": "20"}, {"equate1": "0x34"})

    QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Underscore, Qt.NoModifier, "_"))
    app.processEvents()

    popup = editor._completer.popup()
    assert popup.currentIndex().data() == "_variable1"
    assert popup.width() >= BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_MIN_WIDTH


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


def test_binary_workbench_highlighter_groups_use_distinct_colors():
    shared_symbol_color = PSX_MIPS_HIGHLIGHTER["equate"]
    distinct_colors = [
        PSX_MIPS_HIGHLIGHTER["label"],
        psx_mips_highlight_color("mnemonic", "beq"),
        psx_mips_highlight_color("mnemonic", "j"),
        psx_mips_highlight_color("mnemonic", "lw"),
        psx_mips_highlight_color("mnemonic", "mfhi"),
        psx_mips_highlight_color("mnemonic", "addiu"),
        psx_mips_highlight_color("registers", "s0"),
        psx_mips_highlight_color("registers", "a0"),
        psx_mips_highlight_color("registers", "sp"),
        psx_mips_highlight_color("registers", "ra"),
    ]

    assert PSX_MIPS_HIGHLIGHTER["variable"] == shared_symbol_color
    assert shared_symbol_color not in distinct_colors
    assert len(distinct_colors) == len(set(distinct_colors))


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
    tool.tabs.set_current_memory_regions(
        [BinaryWorkbenchMemoryRegionDTO("SLUS code", 0x1C2400, 0x1C24FF)]
    )

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
    _app().processEvents()
    current = tool.tabs.current_context()

    assert current is not None
    assert page.grid.instructions.toPlainText().splitlines() == ["BEQZ $s1, 0x8", "NOP"]  # type: ignore[attr-defined]
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


def test_binary_workbench_native_close_dialog_maps_windows_buttons():
    assert _map_windows_response(6).name == "Save"
    assert _map_windows_response(7).name == "Discard"
    assert _map_windows_response(2).name == "Cancel"
