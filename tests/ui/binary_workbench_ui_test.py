import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QPlainTextEdit, QScrollBar, QTabBar

from src.main import create_main_window
from src.modules.dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment import BinaryWorkbenchSymbolsDialog
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
    workspace_path = window._state_service.save_workspace(window._collect_context(), tmp_path / "workspace")
    restored = _window(tmp_path)
    workspace = restored._state_service.load_workspace(workspace_path)
    restored._apply_context(workspace.context)
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
    state = window._collect_context()
    missing.unlink()
    restored = _window(tmp_path)
    restored._apply_context(state)
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
    assert headers == ["File", "Bytes", "Instruction"]
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
    assert page.grid.instructions.toPlainText().splitlines()[0] == "addiu v1, v1, 0x1F4"  # type: ignore[attr-defined]
    assert page.grid.bytes.toPlainText().splitlines()[0] != ""  # type: ignore[attr-defined]


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
    assert len(current.rows) == 11
    assert current.rows[0].instruction.startswith("jal")
    assert current.rows[0].bytes_text != "00 00 00 00"
    assert current.rows[-1].bytes_text != "00 00 00 00"


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
    assert str(output_path) in tool.export_state().recent_files


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
    assert "addiu $sp,$sp,-0x10" in output_path.read_text(encoding="utf-8")
    assert tool.export_state().directories["save_assembly"] == str(output_path.parent)


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

    assert headers == ["File", "ram_offset", "Bytes", "Instruction"]
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
    assert assembly_path.read_text(encoding="utf-8") == "addiu $sp,$sp,-0x10"


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
