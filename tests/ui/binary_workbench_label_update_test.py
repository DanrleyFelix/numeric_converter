import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import build_rows_from_instructions
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.table import (
    BinaryWorkbenchGrid,
)
from src.presentation.ui.components.binary_workbench.window import BinaryWorkbenchWindow

_APP = None


def _app() -> QApplication:
    """Return the application instance required by the isolated grid."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _grid(lines: list[str]) -> BinaryWorkbenchGrid:
    """Create an assembly grid without opening the main window or workspace."""

    _app()
    codec = PsxMipsR3000ACodec()
    rows = build_rows_from_instructions(lines, [BINARY_WORKBENCH_TEXT.FILE])
    grid = BinaryWorkbenchGrid(codec)
    grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    grid.set_symbols(labels_from_rows(rows), {}, {}, {})
    grid.load_rows(
        [
            BINARY_WORKBENCH_TEXT.FILE,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
        ],
        rows,
    )
    return grid


def test_labels_refresh_only_when_file_offset_layout_changes():
    grid = _grid([
        "entry: nop",
        "target: nop",
        "beq $zero, $zero, target",
    ])
    coordinator = grid._consistency_coordinator
    initial_structural_revision = coordinator.structural_revision
    grid.instructions.setPlainText(
        "entry: addu $zero, $zero, $zero\n"
        "target: nop\n"
        "beq $zero, $zero, target"
    )
    _app().processEvents()
    assert coordinator.structural_revision == initial_structural_revision

    grid.instructions.setPlainText(
        "entry: addu $zero, $zero, $zero\n"
        "nop\n"
        "target: nop\n"
        "beq $zero, $zero, target"
    )
    _app().processEvents()
    assert coordinator.ensure_consistent("test").success
    assert coordinator.structural_revision == initial_structural_revision + 1
    assert grid.current_labels()["target"] == "0x00000008"
    assert grid.instructions._jump_symbols["target"] == "0x00000008"
    assert grid._codec.jump_navigation_target(
        "beq $zero, $zero, target",
        "target",
        grid.instructions._jump_symbols,
    ) == 0x08

    grid.instructions.setPlainText(
        "entry: addu $zero, $zero, $zero\n"
        "target: nop\n"
        "beq $zero, $zero, target"
    )
    _app().processEvents()
    assert coordinator.ensure_consistent("test").success
    assert coordinator.structural_revision == initial_structural_revision + 2
    assert grid.current_labels()["target"] == "0x00000004"


def test_label_navigation_uses_first_valid_offset_at_or_after_label():
    rows = [
        BinaryWorkbenchRowDTO({"File": "-"}, "label_test:", ""),
        BinaryWorkbenchRowDTO({"File": "-"}, "; comment", ""),
        BinaryWorkbenchRowDTO({"File": "-"}, "; comment", ""),
        BinaryWorkbenchRowDTO({"File": "0x00000010"}, "nop", "00 00 00 00"),
        BinaryWorkbenchRowDTO({"File": "0x00000014"}, "inline: nop", "00 00 00 00"),
    ]

    labels = labels_from_rows(rows)

    assert labels == {
        "label_test": "0x00000010",
        "inline": "0x00000014",
    }
    assert PsxMipsR3000ACodec().jump_navigation_target(
        "beq $zero, $zero, label_test",
        "label_test",
        labels,
    ) == 0x10


def test_clicked_branch_resolves_current_label_row_instead_of_stale_snapshot():
    grid = _grid([
        "test:",
        ";comenta",
        "LUI t1, 0x801A",
        "ORI t1, t1, 0xB364",
        "BEQ $zero, $zero, test",
    ])
    grid._labels["test"] = "0x00000004"
    grid._refresh_jump_navigation()

    assert grid.instructions._jump_symbols["test"] == "0x00000004"
    assert grid.instructions._standard_target(QPoint(), "test") == 0x00000000


def test_equal_size_multi_line_edit_refreshes_labels_and_branch_displacement():
    """Refresh moved labels even when the final executable size is unchanged."""

    grid = _grid([
        "nop",
        "target: invalid",
        "nop",
        "beq $zero, $zero, target",
    ])

    grid.instructions.setPlainText(
        "invalid\n"
        "target: nop\n"
        "nop\n"
        "beq $zero, $zero, target"
    )
    _app().processEvents()
    assert grid.ensure_consistent("test").success

    assert grid.current_labels() == {"target": "0x00000000"}
    assert grid.export_rows()[-1].bytes_text == "FD FF 00 10"


def test_f1_shortcut_forces_active_grid_recalculation(monkeypatch):
    """Expose the safety refresh through one window-level F1 shortcut."""

    window = BinaryWorkbenchWindow(BinaryWorkbenchStateDTO())
    window.new_scratch_tab()
    grid = window.tabs.currentWidget().grid
    calls: list[bool] = []
    monkeypatch.setattr(grid, "recalculate_labels_and_branches", lambda: calls.append(True))

    shortcut = window.findChild(QShortcut, "binary-workbench-recalculate-shortcut")
    assert shortcut is not None
    assert shortcut.key().toString() == "F1"
    shortcut.activated.emit()

    assert calls == [True]
