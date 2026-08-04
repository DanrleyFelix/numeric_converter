import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import build_rows_from_instructions
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchEditRulesDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor import (
    grid_incremental_editing as incremental_module,
)
from src.core.binary_workbench import incremental_refresh as refresh_module
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.table import BinaryWorkbenchGrid

_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _grid(lines: list[str]) -> BinaryWorkbenchGrid:
    _app()
    rows = build_rows_from_instructions(lines, [BINARY_WORKBENCH_TEXT.FILE])
    grid = BinaryWorkbenchGrid(PsxMipsR3000ACodec())
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


def test_stable_edit_assembles_only_the_modified_line(monkeypatch):
    """Keep normal typing independent from the number of labels and rows."""

    lines = [
        item
        for index in range(150)
        for item in (
            f"label_{index}: lui $v0, 0x8B",
            f"beq $zero, $zero, label_{index}",
        )
    ]
    grid = _grid(lines)
    calls: list[list[str]] = []
    original = incremental_module.build_source_line_rows

    def tracked(source, *args, **kwargs):
        calls.append(list(source))
        return original(source, *args, **kwargs)

    monkeypatch.setattr(incremental_module, "build_source_line_rows", tracked)
    grid.show()
    grid.instructions.setFocus()
    _app().processEvents()
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    position = block.position() + block.text().rindex("B")
    cursor.setPosition(position)
    grid.instructions.setTextCursor(cursor)

    grid.instructions.insertPlainText("A")
    QTest.qWait(120)

    assert calls == [["label_0: LUI $v0, 0x8AB"]]
    assert grid.instructions.textCursor().position() == position + 1
    assert grid._pending_instruction_lines is None


def test_collapse_and_expand_do_not_assemble_source(monkeypatch):
    """Keep label folding as a strictly visual operation."""

    grid = _grid(["first:", "nop", "second:", "nop"])
    grid.set_label_folding_enabled(True)

    def unexpected(*_args, **_kwargs):
        raise AssertionError("folding must not invoke the assembler")

    monkeypatch.setattr(incremental_module, "build_source_line_rows", unexpected)
    grid.toggle_label_fold("first")
    grid.toggle_label_fold("first")

    assert "first" not in grid._collapsed_labels


def test_label_edit_propagates_to_dependent_branch_after_debounce():
    """Apply the edited row first, then update label dependants after 80 ms."""

    grid = _grid(["target: nop", "beq $zero, $zero, target"])
    grid.show()
    grid.instructions.setFocus()
    _app().processEvents()
    block = grid.instructions.document().firstBlock()
    cursor = QTextCursor(block)
    cursor.setPosition(block.position() + block.text().index(":"))
    grid.instructions.setTextCursor(cursor)

    grid.instructions.insertPlainText("2")

    assert "target" in grid.current_labels()
    QTest.qWait(160)
    assert grid.current_labels() == {"target2": "0x00000000"}
    assert grid.export_rows()[1].bytes_text == ""


def test_f1_refreshes_only_four_kilobytes_and_warns_after_leaving(monkeypatch):
    """Bound large F1 refreshes and request a new render after viewport travel."""

    lines = [f"label_{index}: nop" if index % 8 == 0 else "nop" for index in range(1100)]
    grid = _grid(lines)
    calls: list[int] = []
    original = refresh_module.build_source_line_rows

    def tracked(source, *args, **kwargs):
        calls.append(len(source))
        return original(source, *args, **kwargs)

    monkeypatch.setattr(refresh_module, "build_source_line_rows", tracked)
    warnings: list[str] = []
    grid.commandWarningRequested.connect(warnings.append)

    grid.recalculate_labels_and_branches()

    assert calls
    assert max(calls) <= 1024
    assert grid._last_assembly_refresh_window == (0, 4096)
    assert warnings == [BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_REBUILDING]

    grid.set_visible_offset(grid.scrollbar.maximum())
    _app().processEvents()
    grid.set_visible_offset(grid.scrollbar.maximum())

    if grid._last_assembly_refresh_window is not None:
        assert warnings[-1] == BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_REFRESH_REQUIRED
