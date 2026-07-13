import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import build_rows_from_instructions
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchRowDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor import (
    grid_editing as grid_editing_module,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.table import (
    BinaryWorkbenchGrid,
)

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


def test_labels_refresh_only_when_final_valid_offset_changes(monkeypatch):
    grid = _grid([
        "entry: nop",
        "target: nop",
        "beq $zero, $zero, target",
    ])
    original = grid_editing_module.labels_from_rows
    original_folding_refresh = grid._refresh_label_folding
    calls: list[int] = []
    folding_refreshes: list[bool] = []

    def tracked_labels(rows):
        calls.append(len(rows))
        return original(rows)

    def tracked_folding_refresh():
        folding_refreshes.append(True)
        original_folding_refresh()

    monkeypatch.setattr(grid_editing_module, "labels_from_rows", tracked_labels)
    monkeypatch.setattr(grid, "_refresh_label_folding", tracked_folding_refresh)
    grid.instructions.setPlainText(
        "entry: addu $zero, $zero, $zero\n"
        "target: nop\n"
        "beq $zero, $zero, target"
    )
    assert calls == []
    assert folding_refreshes == []

    grid.instructions.setPlainText(
        "entry: addu $zero, $zero, $zero\n"
        "nop\n"
        "target: nop\n"
        "beq $zero, $zero, target"
    )
    assert calls == [4]
    assert folding_refreshes == [True]
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
    assert calls == [4, 3]
    assert folding_refreshes == [True, True]
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
