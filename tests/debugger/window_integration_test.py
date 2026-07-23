import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import QEvent, Qt

from src.modules.binary_workbench_dtos import BinaryWorkbenchStateDTO
from src.presentation.ui.components.binary_workbench.window import BinaryWorkbenchWindow

_APP = None


def _app() -> QApplication:
    """Return the process-wide Qt application used by debugger UI tests."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _tool(tmp_path: Path, body: str) -> BinaryWorkbenchWindow:
    """Open one saved assembly file in a Binary Workbench window."""

    _app()
    source = tmp_path / "debug.asm"
    source.write_text(body, encoding="utf-8")
    tool = BinaryWorkbenchWindow(BinaryWorkbenchStateDTO(), tmp_path)
    tool.open_assembly_path(source)
    return tool


def _source(instructions: str = "nop") -> str:
    """Return a complete main debugger source around supplied instructions."""

    return "\n".join(
        (
            "* virtual_memory_range 0x80000000 0x801DFFFF",
            "* import current_file 0x80000000",
            "* define $sp 0x801FFFF0",
            "* define $pc 0x80000000",
            instructions,
        )
    )


def test_f5_flow_builds_one_window_and_reuses_shared_actions(tmp_path: Path):
    tool = _tool(tmp_path, _source("j 0x80000000\nnop"))

    window = tool._open_debugger_window()

    assert window is not None
    assert window.actions is tool.toolbar.debugger_actions
    assert [action.shortcut().toString() for action in window.actions.all()] == [
        "F5", "F6", "F7", "F8", "F9", "F10", "F11"
    ]
    assert [action.text() for action in window.actions.all()] == [
        "Run (F5)", "Pause (F6)", "Stop (F7)", "Restart (F8)",
        "Step (F9)", "Step Over (F10)", "Config (F11)",
    ]
    assert window.panels.lower.count() == 4
    assert tool._open_debugger_window() is window
    window.close()
    tool.close()


def test_f5_validation_reports_red_feedback_without_partial_window(tmp_path: Path):
    tool = _tool(tmp_path, "nop")

    window = tool._open_debugger_window()

    assert window is None
    assert tool._debugger_windows == {}
    assert tool.footer_status.property("statusKind") == "error"
    assert tool.footer_status.textInteractionFlags() & Qt.TextSelectableByMouse
    assert "first line" in tool.footer_status.text()
    tool.close()


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (("* virtual_memory_range 0x1000 0x1FFF", "* define $sp 0x1FF0", "* define $pc 0x1000"), "import current_file"),
        (("* virtual_memory_range 0x1000 0x1FFF", "* import current_file 0x1000", "* define $pc 0x1000"), "initial $sp"),
        (("* virtual_memory_range 0x1000 0x1FFF", "* import current_file 0x1000", "* define $sp 0x1FF0"), "initial $pc"),
    ],
)
def test_f5_reports_each_missing_required_configuration(tmp_path: Path, lines, expected):
    """Reject a partial debugger bootstrap and identify the missing setting."""

    tool = _tool(tmp_path, "\n".join((*lines, "nop")))
    assert tool._open_debugger_window() is None
    assert tool.footer_status.property("statusKind") == "error"
    assert expected in tool.footer_status.text()
    tool.close()


def test_step_refreshes_views_and_memory_edit_remains_volatile(tmp_path: Path):
    tool = _tool(tmp_path, _source("addiu $t0, $zero, 7\nnop"))
    window = tool._open_debugger_window()
    assert window is not None

    window.perform("step")
    memory = window.panels.lower.memory
    memory.navigate("0x80000000")
    original_source = (tmp_path / "debug.asm").read_text(encoding="utf-8")
    memory.table.item(0, 1).setText("00 00 00 00")
    rendered = memory.table.item(0, 1).text()
    memory.table.item(0, 1).setSelected(True)
    QApplication.sendEvent(
        memory.table,
        QKeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier),
    )
    memory.navigate("0x3000")

    assert window.debugger.registers.read("t0") == 7
    assert "Execution" in window.panels.lower.log.output.toPlainText()
    assert any(event.level == "Memory" for event in window.debugger.events)
    assert rendered == "00 00 00 00"
    assert QApplication.clipboard().text() == rendered
    assert "outside the debugger image" in tool.footer_status.text()
    assert (tmp_path / "debug.asm").read_text(encoding="utf-8") == original_source
    window.close()
    tool.close()


def test_breakpoint_gutter_and_window_state_are_persisted(tmp_path: Path):
    tool = _tool(tmp_path, _source())
    window = tool._open_debugger_window()
    assert window is not None
    window.resize(1010, 710)
    window.panels.instructions._cell_clicked(0, 0)
    key = window._workspace_key

    window.close()
    QApplication.processEvents()
    state = tool._debugger_state_repository.load(key)

    assert window.debugger.breakpoints[0].address == 0x80000000
    assert state.width == 1010
    assert state.height == 710
    assert state.horizontal_sizes
    tool.close()


def test_closing_window_finishes_active_execution_worker(tmp_path: Path):
    tool = _tool(tmp_path, _source("j 0x80000000\nnop"))
    window = tool._open_debugger_window()
    assert window is not None
    window.perform("run")
    worker = window._worker
    assert worker is not None

    window.close()

    assert not worker.isRunning()
    tool.close()
