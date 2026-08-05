from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QTextEdit

from src.core.binary_workbench.mips_r3000a import validate_mips_hazards
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.constants.raw_instruction_style import (
    RAW_INSTRUCTION_HAZARD_ERROR_BACKGROUND_RGBA,
    RAW_INSTRUCTION_HAZARD_WARNING_BACKGROUND_RGBA,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import address_from_row


class GridRawInstructionsMixin:
    def _render_raw_instructions(self) -> None:
        lines = self._raw_instruction_lines()
        self._set_editor_text(self.raw_instructions, lines)
        self.raw_instructions.set_hazard_extra_selections([])
        self._apply_instruction_hazards(validate_mips_hazards([row.instruction for row in self._rows]))
        if self._label_folding_enabled:
            self._apply_hidden_rows(self.raw_instructions, self._folded_hidden_rows())

    def _raw_instruction_lines(self) -> list[str]:
        lines: list[str] = []
        for row in self._rows:
            lines.append(self._display_raw_row(row))
        return lines

    def _raw_instruction_from_bytes(self, bytes_text: str, address: int) -> str:
        try:
            data = bytes.fromhex(bytes_text.replace(" ", ""))
        except ValueError:
            return ""
        if not data:
            return ""
        return self._codec.disassemble(data[:ROW_BYTES].ljust(ROW_BYTES, b"\x00"), address)

    def _apply_instruction_hazards(self, hazards) -> None:
        document = self.instructions.document()
        self.instructions.set_hazard_extra_selections(
            [
                self._instruction_hazard_selection(
                    document.findBlockByNumber(item.line_index),
                    item.severity,
                )
                for item in hazards
            ]
        )

    def _instruction_hazard_selection(self, block, severity: str) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.cursor = self.instructions.textCursor()
        set_cursor_position(selection.cursor, block.position())
        selection.cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        selection.format = QTextCharFormat()
        rgba = (
            RAW_INSTRUCTION_HAZARD_ERROR_BACKGROUND_RGBA
            if severity == "error"
            else RAW_INSTRUCTION_HAZARD_WARNING_BACKGROUND_RGBA
        )
        selection.format.setBackground(QColor(*rgba))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        return selection
