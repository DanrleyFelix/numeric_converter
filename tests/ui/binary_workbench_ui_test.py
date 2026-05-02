import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QTableWidget

from src.main import create_main_window
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TAB_KIND,
)


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
    assert state.tabs[0].rows != []
    assert state.tabs[0].rows[0].offsets["File"] == "0x00000000"


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
    assert restored_tool.tabs.currentWidget() is not None


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


def test_binary_workbench_uses_editable_grid_without_visual_grid_lines(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    grid = tool.findChild(QTableWidget, "binary-workbench-grid")
    summary = tool.findChild(QLabel, "binary-workbench-selection")

    assert grid is not None
    assert summary is not None
    assert grid.showGrid() is False
    assert grid.selectionBehavior() == grid.SelectionBehavior.SelectItems
    assert grid.selectionMode() == grid.SelectionMode.ExtendedSelection
    assert not bool(grid.item(0, 0).flags() & Qt.ItemIsEditable)
    assert bool(grid.item(0, 2).flags() & Qt.ItemIsEditable)
    assert bool(grid.item(0, 3).flags() & Qt.ItemIsEditable)
    assert summary.text() == "Selected: none | Length: 0 bytes"


def test_binary_workbench_instruction_and_bytes_edit_roundtrip(tmp_path: Path):
    window = _window(tmp_path)
    window._open_binary_workbench()
    tool = window._binary_workbench_window

    assert tool is not None
    tool.tabs.new_scratch_tab()
    page = tool.tabs.currentWidget()
    grid = page.grid  # type: ignore[attr-defined]
    grid.item(0, 2).setText("word 0x246301F4")
    _app().processEvents()

    assert grid.item(0, 3).text() == "F4 01 63 24"
    grid.item(0, 3).setText("0C 00 23 96")
    _app().processEvents()
    assert grid.item(0, 2).text() != ""
